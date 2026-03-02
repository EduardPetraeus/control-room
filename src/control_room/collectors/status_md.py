from __future__ import annotations

import logging
import re
from pathlib import Path

from control_room.config import RepoConfig
from control_room.models.project import StatusInfo

logger = logging.getLogger(__name__)

# File names to try, in priority order.
_STATUS_FILES = ("STATUS.md", "README.md", "DOGFOOD.md")

# --- regex patterns ---
_VERSION_RE = re.compile(r"[vV]\d+(?:\.\d+)*")
_TEST_PASSING_RE = re.compile(r"(\d+)\s*/\s*(\d+)\s*(?:tests?\s*)?pass", re.IGNORECASE)
_TEST_COUNT_RE = re.compile(r"(\d+)\s*tests?", re.IGNORECASE)
_HEALTH_SCORE_RE = re.compile(r"(\d+)%")
_BRANCH_COLON_RE = re.compile(r"branch:\s*(\S+)", re.IGNORECASE)
_BRANCH_BACKTICK_RE = re.compile(r"on\s+`([^`]+)`", re.IGNORECASE)
_STATUS_HEADER_RE = re.compile(r"^##\s+Status\b", re.IGNORECASE | re.MULTILINE)
_STATUS_BOLD_RE = re.compile(r"\*\*Status:\*\*\s*(.+)", re.IGNORECASE)


def parse_status_md(content: str) -> StatusInfo:
    """Parse markdown content and extract project status information.

    Uses regex to extract version, test counts, health score, current branch,
    and status text from markdown files.
    """
    if not content or not content.strip():
        return StatusInfo()

    info: dict[str, object] = {}

    # Version: find patterns like v0.3.0, v2, V2
    version_match = _VERSION_RE.search(content)
    if version_match:
        info["version"] = version_match.group(0)

    # Test counts: "864/864 passing" takes priority over "864 tests"
    passing_match = _TEST_PASSING_RE.search(content)
    if passing_match:
        info["test_count"] = int(passing_match.group(2))
        info["test_passing"] = int(passing_match.group(1))
    else:
        count_match = _TEST_COUNT_RE.search(content)
        if count_match:
            info["test_count"] = int(count_match.group(1))

    # Health score: "55%"
    health_match = _HEALTH_SCORE_RE.search(content)
    if health_match:
        info["health_score"] = f"{health_match.group(1)}%"

    # Current branch: "branch: main" or "on `feature/v1`"
    branch_match = _BRANCH_COLON_RE.search(content)
    if branch_match:
        info["current_branch"] = branch_match.group(1)
    else:
        backtick_match = _BRANCH_BACKTICK_RE.search(content)
        if backtick_match:
            info["current_branch"] = backtick_match.group(1)

    # Status text: first line after "## Status" header or "**Status:** VALUE"
    bold_match = _STATUS_BOLD_RE.search(content)
    if bold_match:
        info["status_text"] = bold_match.group(1).strip()
    else:
        header_match = _STATUS_HEADER_RE.search(content)
        if header_match:
            # Grab the first non-empty line after the header
            rest = content[header_match.end() :]
            for line in rest.splitlines():
                stripped = line.strip()
                if stripped:
                    info["status_text"] = stripped
                    break

    return StatusInfo(**info)


def get_all_status_info(repos: list[RepoConfig]) -> dict[str, StatusInfo]:
    """Collect status information from all configured repositories.

    For each repo, tries to read STATUS.md, README.md, or DOGFOOD.md (in that
    order). Returns a dict keyed by repo name. Fault-tolerant: logs errors and
    returns a default StatusInfo for any repo that fails.
    """
    results: dict[str, StatusInfo] = {}

    for repo in repos:
        try:
            repo_path = Path(repo.path)
            content: str | None = None

            for filename in _STATUS_FILES:
                candidate = repo_path / filename
                if candidate.is_file():
                    content = candidate.read_text(encoding="utf-8")
                    break

            if content is not None:
                results[repo.name] = parse_status_md(content)
            else:
                logger.debug("No status file found for repo %s at %s", repo.name, repo.path)
                results[repo.name] = StatusInfo()

        except Exception:
            logger.exception("Failed to collect status for repo %s", repo.name)
            results[repo.name] = StatusInfo()

    return results
