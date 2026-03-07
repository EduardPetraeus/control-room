"""Launch and manage Claude CLI sessions as subprocesses."""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from control_room.master.task_parser import TaskConfig

logger = logging.getLogger(__name__)

REPOS_BASE = Path.home() / "Github repos"
HEARTBEAT_FILENAME = "session-heartbeat.json"


@dataclass
class SessionInfo:
    """Tracking information for a running Claude CLI session."""

    session_id: str
    pid: int
    task_config: TaskConfig
    repo_path: Path
    started_at: float = field(default_factory=time.time)
    timeout_seconds: int = 1800  # 30 minutes default


def generate_session_id(task_config: TaskConfig) -> str:
    """Generate a unique session ID from task config."""
    timestamp = int(time.time())
    repo = task_config.repo or "unknown"
    issue = task_config.issue_number or 0
    return f"master-{repo}-{issue}-{timestamp}"


def resolve_repo_path(repo_name: str, repos_base: Path | None = None) -> Path | None:
    """Resolve a repo name to an absolute path."""
    base = repos_base or REPOS_BASE
    repo_path = base / repo_name
    if repo_path.is_dir():
        return repo_path
    return None


def build_claude_command(
    task_config: TaskConfig,
    session_id: str,
) -> list[str]:
    """Build the claude CLI command for a task."""
    prompt = _build_prompt(task_config, session_id)

    cmd = [
        "claude",
        "--print",
        "--model",
        task_config.model,
        "--max-turns",
        str(task_config.max_turns),
        "--output-format",
        "json",
        prompt,
    ]

    return cmd


def _build_prompt(task_config: TaskConfig, session_id: str) -> str:
    """Build the prompt for a Claude CLI session."""
    parts = [
        f"Session ID: {session_id}",
        f"Task: {task_config.title}",
        f"Issue: #{task_config.issue_number} ({task_config.issue_url})",
    ]

    if task_config.branch:
        parts.append(f"Branch: {task_config.branch}")
        parts.append(f"Git: checkout or create branch '{task_config.branch}' before starting.")

    if task_config.instructions:
        parts.append(f"\n## Instructions\n{task_config.instructions}")

    if task_config.acceptance_criteria:
        criteria = "\n".join(f"- [ ] {c}" for c in task_config.acceptance_criteria)
        parts.append(f"\n## Acceptance Criteria\n{criteria}")

    parts.append(
        "\n## Rules\n"
        "- Work on a feature branch, never commit to main\n"
        "- Run tests after changes\n"
        "- Commit with Conventional Commits format\n"
        "- Co-Authored-By: Claude <noreply@anthropic.com>"
    )

    return "\n".join(parts)


def write_heartbeat(
    repo_path: Path,
    session_id: str,
    task_config: TaskConfig,
    status: str = "active",
    progress: float = 0.0,
) -> None:
    """Write a heartbeat JSON file to the repo directory."""
    heartbeat = {
        "session_id": session_id,
        "repo": task_config.repo,
        "branch": task_config.branch or "unknown",
        "task": task_config.title,
        "progress": progress,
        "status": status,
        "cost_usd": 0.0,
        "tokens_used": 0,
        "model": task_config.model,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "managed_by": "master-agent",
        "issue_number": task_config.issue_number,
    }

    hb_path = repo_path / HEARTBEAT_FILENAME
    try:
        hb_path.write_text(json.dumps(heartbeat, indent=2))
    except OSError as exc:
        logger.warning("Failed to write heartbeat to %s: %s", hb_path, exc)


def launch_session(
    task_config: TaskConfig,
    repos_base: Path | None = None,
    timeout_seconds: int = 1800,
) -> SessionInfo | None:
    """Launch a Claude CLI session for a task.

    Returns SessionInfo if successfully launched, None otherwise.
    """
    repo_path = resolve_repo_path(task_config.repo, repos_base)
    if repo_path is None:
        logger.error("Repo not found: %s", task_config.repo)
        return None

    session_id = generate_session_id(task_config)
    cmd = build_claude_command(task_config, session_id)

    logger.info(
        "Launching session %s for %s (#%d) in %s",
        session_id,
        task_config.title,
        task_config.issue_number,
        repo_path,
    )

    # Write initial heartbeat
    write_heartbeat(repo_path, session_id, task_config, status="active")

    try:
        env = os.environ.copy()
        env["MASTER_SESSION_ID"] = session_id

        process = subprocess.Popen(
            cmd,
            cwd=str(repo_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            start_new_session=True,
        )

        return SessionInfo(
            session_id=session_id,
            pid=process.pid,
            task_config=task_config,
            repo_path=repo_path,
            timeout_seconds=timeout_seconds,
        )

    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("Failed to launch session %s: %s", session_id, exc)
        write_heartbeat(repo_path, session_id, task_config, status="failed")
        return None


def is_session_alive(session: SessionInfo) -> bool:
    """Check if a session's process is still running."""
    try:
        os.kill(session.pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def is_session_timed_out(session: SessionInfo) -> bool:
    """Check if a session has exceeded its timeout."""
    elapsed = time.time() - session.started_at
    return elapsed > session.timeout_seconds


def stop_session(session: SessionInfo) -> bool:
    """Stop a running session gracefully."""
    try:
        os.kill(session.pid, signal.SIGTERM)
        # Give it 10 seconds to clean up
        deadline = time.time() + 10
        while time.time() < deadline:
            if not is_session_alive(session):
                return True
            time.sleep(0.5)
        # Force kill
        os.kill(session.pid, signal.SIGKILL)
        return True
    except (OSError, ProcessLookupError):
        return True  # Already dead


def collect_session_output(session: SessionInfo) -> dict | None:
    """Try to read session output after completion.

    Reads the heartbeat file in the repo directory for final status.
    """
    hb_path = session.repo_path / HEARTBEAT_FILENAME
    if not hb_path.exists():
        return None
    try:
        data = json.loads(hb_path.read_text(encoding="utf-8"))
        return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read session output for %s: %s", session.session_id, exc)
        return None
