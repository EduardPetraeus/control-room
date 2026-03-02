from __future__ import annotations

import logging
import subprocess

from control_room.models.activity import CommitInfo, CommitStats

logger = logging.getLogger(__name__)


def get_recent_commits(repo_path: str, limit: int = 20) -> list[CommitInfo]:
    """Return the most recent commits from a git repository.

    Runs ``git log`` with a pipe-delimited format and parses each line
    into a :class:`CommitInfo` object.  On any error the function logs a
    warning and returns an empty list.
    """
    try:
        result = subprocess.run(
            ["git", "log", "--format=%H|%an|%ai|%s", "-n", str(limit)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=repo_path,
        )
        if result.returncode != 0:
            logger.warning("git log failed in %s: %s", repo_path, result.stderr.strip())
            return []

        commits: list[CommitInfo] = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append(
                    CommitInfo(
                        hash=parts[0],
                        author=parts[1],
                        date=parts[2],
                        message=parts[3],
                    )
                )
        return commits

    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
        OSError,
    ) as exc:
        logger.warning("Failed to get recent commits from %s: %s", repo_path, exc)
        return []


def get_commit_stats(repo_path: str, days: int = 30) -> CommitStats:
    """Return aggregated commit statistics for the last *days* days.

    On any error the function returns a zeroed-out :class:`CommitStats`.
    """
    empty = CommitStats(total_commits=0, first_commit_date=None, last_commit_date=None, authors=[])
    try:
        result = subprocess.run(
            ["git", "log", f"--since={days} days ago", "--format=%H|%an|%ai|%s"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=repo_path,
        )
        if result.returncode != 0:
            logger.warning("git log failed in %s: %s", repo_path, result.stderr.strip())
            return empty

        lines = [ln for ln in result.stdout.strip().splitlines() if ln]
        if not lines:
            return empty

        dates: list[str] = []
        authors: set[str] = set()
        for line in lines:
            parts = line.split("|", 3)
            if len(parts) == 4:
                authors.add(parts[1])
                dates.append(parts[2])

        return CommitStats(
            total_commits=len(lines),
            first_commit_date=dates[-1] if dates else None,
            last_commit_date=dates[0] if dates else None,
            authors=sorted(authors),
        )

    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
        OSError,
    ) as exc:
        logger.warning("Failed to get commit stats from %s: %s", repo_path, exc)
        return empty


def get_current_branch(repo_path: str) -> str:
    """Return the current branch name, or ``"unknown"`` on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=repo_path,
        )
        if result.returncode != 0:
            logger.warning("git rev-parse failed in %s: %s", repo_path, result.stderr.strip())
            return "unknown"
        return result.stdout.strip()

    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
        OSError,
    ) as exc:
        logger.warning("Failed to get current branch from %s: %s", repo_path, exc)
        return "unknown"


def get_last_commit_date(repo_path: str) -> str | None:
    """Return the ISO date string of the most recent commit, or ``None``."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ai"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=repo_path,
        )
        if result.returncode != 0:
            logger.warning("git log failed in %s: %s", repo_path, result.stderr.strip())
            return None
        output = result.stdout.strip()
        return output if output else None

    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
        OSError,
    ) as exc:
        logger.warning("Failed to get last commit date from %s: %s", repo_path, exc)
        return None
