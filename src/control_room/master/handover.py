"""Detect context limits and build continuation prompts for session handover."""

from __future__ import annotations

import json
import logging

from control_room.master.launcher import (
    HEARTBEAT_FILENAME,
    SessionInfo,
)
from control_room.master.task_parser import TaskConfig

logger = logging.getLogger(__name__)

# Indicators that a session hit context limits
CONTEXT_LIMIT_INDICATORS = [
    "context window",
    "context limit",
    "token limit",
    "maximum context",
    "conversation too long",
    "compress",
]


def needs_handover(session: SessionInfo) -> bool:
    """Check if a completed session needs a handover to continue work.

    Reads the session output/heartbeat to determine if the task is incomplete.
    """
    hb_path = session.repo_path / HEARTBEAT_FILENAME
    if not hb_path.exists():
        return False

    try:
        data = json.loads(hb_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    status = data.get("status", "")
    progress = data.get("progress", 0.0)

    # Session completed normally — no handover needed
    if status == "completed" and progress >= 0.9:
        return False

    # Session failed or was blocked — no auto-handover
    if status in ("failed", "blocked"):
        return False

    # Session ended with incomplete progress — needs handover
    if progress < 0.9 and status in ("active", "idle", "completed"):
        return True

    return False


def detect_context_limit(session_output: str) -> bool:
    """Check if session output indicates a context window limit was hit."""
    output_lower = session_output.lower()
    return any(indicator in output_lower for indicator in CONTEXT_LIMIT_INDICATORS)


def build_continuation_prompt(
    original_task: TaskConfig,
    previous_session_id: str,
    progress_summary: str = "",
) -> str:
    """Build a continuation prompt for a handover session.

    Includes context about what the previous session accomplished.
    """
    parts = [
        f"## Continuation from session {previous_session_id}",
        f"Original task: {original_task.title}",
        f"Issue: #{original_task.issue_number} ({original_task.issue_url})",
    ]

    if original_task.branch:
        parts.append(f"Branch: {original_task.branch}")
        parts.append(
            "Git: the branch should already exist with partial work. "
            "Check git log to see what was done."
        )

    if progress_summary:
        parts.append(f"\n## Previous Progress\n{progress_summary}")

    if original_task.instructions:
        parts.append(f"\n## Original Instructions\n{original_task.instructions}")

    if original_task.acceptance_criteria:
        criteria = "\n".join(f"- [ ] {c}" for c in original_task.acceptance_criteria)
        parts.append(f"\n## Acceptance Criteria (check what's already done)\n{criteria}")

    parts.append(
        "\n## Handover Rules\n"
        "- Check git log and current state before making changes\n"
        "- Do NOT redo work that was already completed\n"
        "- Continue from where the previous session left off\n"
        "- Run tests to verify existing work still passes\n"
        "- Commit with Conventional Commits format"
    )

    return "\n".join(parts)


def get_progress_summary(session: SessionInfo) -> str:
    """Extract a progress summary from the session's repo state.

    Checks git log for recent commits on the task branch.
    """
    import subprocess

    branch = session.task_config.branch or "HEAD"

    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-10", branch],
            cwd=str(session.repo_path),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return f"Recent commits on {branch}:\n{result.stdout.strip()}"
    except (OSError, subprocess.TimeoutExpired):
        pass

    return ""


def prepare_handover(session: SessionInfo) -> tuple[TaskConfig, str] | None:
    """Prepare a handover for a session that needs continuation.

    Returns a tuple of (new_task_config, continuation_prompt), or None if
    no handover is needed.
    """
    if not needs_handover(session):
        return None

    progress_summary = get_progress_summary(session)
    continuation_prompt = build_continuation_prompt(
        session.task_config,
        session.session_id,
        progress_summary,
    )

    # Create a new task config for the continuation
    new_task = TaskConfig(
        issue_number=session.task_config.issue_number,
        issue_url=session.task_config.issue_url,
        title=f"[Continuation] {session.task_config.title}",
        repo=session.task_config.repo,
        branch=session.task_config.branch,
        model=session.task_config.model,
        budget=session.task_config.budget,
        max_turns=session.task_config.max_turns,
        instructions=continuation_prompt,
        acceptance_criteria=session.task_config.acceptance_criteria,
        status="Ready",
    )

    return new_task, continuation_prompt
