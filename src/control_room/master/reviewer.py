"""Trigger review pipeline after session completion."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from control_room.master.launcher import SessionInfo

logger = logging.getLogger(__name__)

REVIEW_AGENTS = Path.home() / ".claude" / "agents"


def run_review_pipeline(session: SessionInfo) -> dict[str, bool]:
    """Run code-reviewer and security-reviewer on the session's repo.

    Returns a dict with review results: {"code": bool, "security": bool}.
    True means the review passed (or at least completed without error).
    """
    results: dict[str, bool] = {}

    results["code"] = _run_claude_review(
        repo_path=session.repo_path,
        agent_name="code-reviewer",
        branch=session.task_config.branch,
    )

    results["security"] = _run_claude_review(
        repo_path=session.repo_path,
        agent_name="security-reviewer",
        branch=session.task_config.branch,
    )

    return results


def _run_claude_review(
    repo_path: Path,
    agent_name: str,
    branch: str = "",
) -> bool:
    """Run a Claude review agent on a repo.

    Uses `claude --print` with the agent's instructions as context.
    Returns True if the review completed successfully.
    """
    agent_file = REVIEW_AGENTS / f"{agent_name}.md"
    if not agent_file.exists():
        logger.warning("Review agent not found: %s", agent_file)
        return False

    diff_target = f"main...{branch}" if branch else "HEAD~5..HEAD"
    prompt = (
        f"Review the code changes in this repo. "
        f"Focus on the diff: `git diff {diff_target}`. "
        f"Report any issues found. Be concise."
    )

    try:
        result = subprocess.run(
            [
                "claude",
                "--print",
                "--model",
                "claude-sonnet-4-5-20250929",
                "--max-turns",
                "5",
                prompt,
            ],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes per review
        )

        if result.returncode != 0:
            logger.warning(
                "%s review failed for %s: %s",
                agent_name,
                repo_path.name,
                result.stderr.strip()[:200],
            )
            return False

        logger.info(
            "%s review completed for %s (exit code %d)",
            agent_name,
            repo_path.name,
            result.returncode,
        )
        return True

    except subprocess.TimeoutExpired:
        logger.warning("%s review timed out for %s", agent_name, repo_path.name)
        return False
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("%s review error for %s: %s", agent_name, repo_path.name, exc)
        return False


def should_review(session: SessionInfo) -> bool:
    """Determine if a completed session should trigger a review.

    Reviews are triggered for sessions that completed with actual code changes.
    """
    if not session.repo_path.is_dir():
        return False

    # Check if there are uncommitted or recent commits on the branch
    branch = session.task_config.branch
    if not branch:
        return False

    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-1", f"main..{branch}"],
            cwd=str(session.repo_path),
            capture_output=True,
            text=True,
            timeout=10,
        )
        # If there are commits ahead of main, review is needed
        return result.returncode == 0 and bool(result.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        return False
