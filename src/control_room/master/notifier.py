"""macOS notifications via osascript."""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)


def notify(title: str, message: str, sound: str = "Glass") -> bool:
    """Send a macOS notification via osascript.

    Returns True if notification was sent successfully.
    """
    script = (
        f'display notification "{_escape(message)}" '
        f'with title "{_escape(title)}" '
        f'sound name "{sound}"'
    )

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            logger.warning("osascript notification failed: %s", result.stderr.strip())
            return False
        return True
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("Failed to send notification: %s", exc)
        return False


def notify_completion(session_id: str, task_title: str, repo: str) -> bool:
    """Notify that a session completed."""
    return notify(
        title=f"Task Complete: {repo}",
        message=f"{task_title} ({session_id})",
        sound="Glass",
    )


def notify_blocker(session_id: str, task_title: str, blocker: str) -> bool:
    """Notify that a session is blocked."""
    return notify(
        title=f"Blocker: {task_title}",
        message=f"{blocker} ({session_id})",
        sound="Basso",
    )


def notify_failure(session_id: str, task_title: str, reason: str) -> bool:
    """Notify that a session failed."""
    return notify(
        title=f"Session Failed: {task_title}",
        message=f"{reason} ({session_id})",
        sound="Sosumi",
    )


def notify_review_complete(repo: str, passed: bool) -> bool:
    """Notify that a code review completed."""
    status = "PASSED" if passed else "NEEDS ATTENTION"
    return notify(
        title=f"Review {status}: {repo}",
        message=f"Code review completed for {repo}",
        sound="Glass" if passed else "Basso",
    )


def _escape(text: str) -> str:
    """Escape text for AppleScript string literals."""
    return text.replace("\\", "\\\\").replace('"', '\\"')
