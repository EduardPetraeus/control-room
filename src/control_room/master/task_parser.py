"""Parse GitHub Issue body into task configuration for the master agent daemon."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_BUDGET = 10.0
DEFAULT_MAX_TURNS = 60


@dataclass
class TaskConfig:
    """Parsed task configuration from a GitHub Issue body."""

    issue_number: int = 0
    issue_url: str = ""
    title: str = ""
    repo: str = ""
    branch: str = ""
    model: str = DEFAULT_MODEL
    budget: float = DEFAULT_BUDGET
    max_turns: int = DEFAULT_MAX_TURNS
    instructions: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    status: str = ""


def parse_issue_body(body: str) -> dict[str, str | float | int | list[str]]:
    """Extract structured fields from a GitHub Issue body.

    Expected format (markdown):
        ## Agent Task
        **Repo:** evidence-sync
        **Branch:** feat/iteration-8
        **Model:** claude-sonnet-4-5-20250929
        **Budget:** $5
        **Max turns:** 60

        ## Instructions
        Implement the PRISMA flow diagram...

        ## Acceptance Criteria
        - [ ] SVG export generates valid output
        - [ ] Unit tests for all new functions
    """
    result: dict[str, str | float | int | list[str]] = {}

    # Extract key-value fields from **Key:** Value pattern
    field_patterns = {
        "repo": r"\*\*Repo:\*\*\s*(.+)",
        "branch": r"\*\*Branch:\*\*\s*(.+)",
        "model": r"\*\*Model:\*\*\s*(.+)",
        "budget": r"\*\*Budget:\*\*\s*\$?([\d.]+)",
        "max_turns": r"\*\*Max turns:\*\*\s*(\d+)",
    }

    for key, pattern in field_patterns.items():
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if key == "budget":
                result[key] = float(value)
            elif key == "max_turns":
                result[key] = int(value)
            else:
                result[key] = value

    # Extract instructions section
    instructions_match = re.search(
        r"## Instructions\s*\n(.*?)(?=\n## |\Z)",
        body,
        re.DOTALL | re.IGNORECASE,
    )
    if instructions_match:
        result["instructions"] = instructions_match.group(1).strip()

    # Extract acceptance criteria as list
    criteria_match = re.search(
        r"## Acceptance Criteria\s*\n(.*?)(?=\n## |\Z)",
        body,
        re.DOTALL | re.IGNORECASE,
    )
    if criteria_match:
        criteria_text = criteria_match.group(1).strip()
        criteria = []
        for line in criteria_text.split("\n"):
            line = line.strip()
            # Match both checked and unchecked checkboxes, or plain bullets
            cleaned = re.sub(r"^-\s*\[[ x]\]\s*", "", line)
            cleaned = re.sub(r"^[-*]\s*", "", cleaned)
            if cleaned:
                criteria.append(cleaned)
        result["acceptance_criteria"] = criteria

    return result


def build_task_config(
    issue_number: int,
    issue_url: str,
    title: str,
    body: str,
    status: str = "",
) -> TaskConfig:
    """Build a TaskConfig from a GitHub Issue."""
    parsed = parse_issue_body(body)

    raw_budget = parsed.get("budget", DEFAULT_BUDGET)
    raw_max_turns = parsed.get("max_turns", DEFAULT_MAX_TURNS)
    raw_criteria = parsed.get("acceptance_criteria", [])

    return TaskConfig(
        issue_number=issue_number,
        issue_url=issue_url,
        title=title,
        repo=str(parsed.get("repo", "")),
        branch=str(parsed.get("branch", "")),
        model=str(parsed.get("model", DEFAULT_MODEL)),
        budget=float(raw_budget) if not isinstance(raw_budget, list) else DEFAULT_BUDGET,
        max_turns=int(raw_max_turns) if not isinstance(raw_max_turns, list) else DEFAULT_MAX_TURNS,
        instructions=str(parsed.get("instructions", "")),
        acceptance_criteria=raw_criteria if isinstance(raw_criteria, list) else [],
        status=status,
    )


def fetch_ready_tasks(
    project_number: int = 1,
    owner: str = "EduardPetraeus",
) -> list[TaskConfig]:
    """Fetch tasks with status 'Ready' from GitHub Projects board.

    Fetches the project board items, finds issues with 'Ready' status,
    then fetches each issue body and parses it into a TaskConfig.
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "project",
                "item-list",
                str(project_number),
                "--owner",
                owner,
                "--format",
                "json",
                "--limit",
                "500",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.warning("gh project item-list failed: %s", result.stderr.strip())
            return []

        data = json.loads(result.stdout)
        tasks: list[TaskConfig] = []

        for item in data.get("items", []):
            status = item.get("status", "") or ""
            if status.lower() != "ready":
                continue

            content = item.get("content", {})
            if not isinstance(content, dict):
                continue

            # type is inside content, not top-level
            item_type = content.get("type", "")
            if item_type not in ("Issue", "ISSUE"):
                continue

            issue_url = content.get("url", "")
            title = item.get("title", "")
            issue_number = content.get("number", 0)
            repo_full = content.get("repository", "")

            # Body is included in content from gh project item-list
            body = content.get("body", "")
            if not body:
                # Fallback: fetch via gh API if body not in content
                body = _fetch_issue_body(issue_url)
            if not body:
                logger.warning("Could not fetch body for issue: %s", issue_url)
                continue

            task = build_task_config(
                issue_number=issue_number,
                issue_url=issue_url,
                title=title,
                body=body,
                status=status,
            )

            # If repo not specified in body, infer from project item
            if not task.repo and repo_full:
                # repo_full might be "EduardPetraeus/evidence-sync"
                task.repo = repo_full.split("/")[-1] if "/" in repo_full else repo_full

            tasks.append(task)

        return tasks

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to fetch ready tasks: %s", exc)
        return []


def _fetch_issue_body(issue_url: str) -> str:
    """Fetch issue body from GitHub API using gh CLI."""
    if not issue_url:
        return ""

    try:
        # Extract owner/repo/number from URL like https://github.com/owner/repo/issues/42
        match = re.search(r"github\.com/([^/]+)/([^/]+)/issues/(\d+)", issue_url)
        if not match:
            return ""

        owner, repo, number = match.groups()
        result = subprocess.run(
            ["gh", "issue", "view", number, "--repo", f"{owner}/{repo}", "--json", "body"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return ""

        data = json.loads(result.stdout)
        return data.get("body", "")

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to fetch issue body from %s: %s", issue_url, exc)
        return ""
