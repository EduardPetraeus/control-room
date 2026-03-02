from __future__ import annotations

import json
import logging
import subprocess

from control_room.models.activity import ActivityEvent, GitHubProjectItem

logger = logging.getLogger(__name__)


def get_project_items(
    project_number: int = 1, owner: str = "EduardPetraeus"
) -> list[GitHubProjectItem]:
    """Fetch items from a GitHub Projects board via gh CLI.

    Uses: gh project item-list {number} --owner {owner} --format json --limit 100
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
                "100",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.warning("gh project item-list failed: %s", result.stderr.strip())
            return []

        data = json.loads(result.stdout)
        items: list[GitHubProjectItem] = []

        for item in data.get("items", []):
            status = ""
            # Status is in the "status" field from project items
            if "status" in item:
                status = item["status"] or ""

            labels = []
            if "labels" in item:
                labels = [
                    lbl.get("name", "") for lbl in item.get("labels", []) if isinstance(lbl, dict)
                ]
            elif isinstance(item.get("labels"), list):
                labels = [str(lbl) for lbl in item["labels"]]

            items.append(
                GitHubProjectItem(
                    title=item.get("title", ""),
                    status=status,
                    item_type=item.get("type", ""),
                    url=(
                        item.get("content", {}).get("url", "")
                        if isinstance(item.get("content"), dict)
                        else item.get("url", "")
                    ),
                    repo=(
                        item.get("content", {}).get("repository", "")
                        if isinstance(item.get("content"), dict)
                        else item.get("repository", "")
                    ),
                    labels=labels,
                    assignee=(
                        item.get("assignees", [{}])[0].get("login", "")
                        if item.get("assignees")
                        else ""
                    ),
                )
            )

        return items
    except (
        subprocess.TimeoutExpired,
        FileNotFoundError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        logger.warning("Failed to get GitHub project items: %s", exc)
        return []


def get_repo_events_sync(owner: str, repo: str, limit: int = 10) -> list[ActivityEvent]:
    """Fetch recent events for a repo via gh api."""
    try:
        result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{owner}/{repo}/events",
                "--jq",
                f"[.[:{limit}][] | {{type: .type, created_at: .created_at,"
                f" actor: .actor.login, payload: .payload}}]",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            logger.warning(
                "gh api events failed for %s/%s: %s",
                owner,
                repo,
                result.stderr.strip(),
            )
            return []

        events_data = json.loads(result.stdout)
        events: list[ActivityEvent] = []

        event_config = {
            "PushEvent": ("commit", "green"),
            "IssuesEvent": ("issue", "amber"),
            "PullRequestEvent": ("pr", "blue"),
            "ReleaseEvent": ("release", "green"),
            "CreateEvent": ("create", "green"),
            "DeleteEvent": ("delete", "red"),
            "IssueCommentEvent": ("comment", "gray"),
        }

        for event in events_data:
            event_type_raw = event.get("type", "")
            config = event_config.get(event_type_raw, ("other", "gray"))

            # Build a readable title
            payload = event.get("payload", {})
            title = _build_event_title(event_type_raw, payload)

            events.append(
                ActivityEvent(
                    event_type=config[0],
                    title=title,
                    repo_name=repo,
                    date=event.get("created_at", ""),
                    color=config[1],
                )
            )

        return events
    except (
        subprocess.TimeoutExpired,
        FileNotFoundError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        logger.warning("Failed to get events for %s/%s: %s", owner, repo, exc)
        return []


def _build_event_title(event_type: str, payload: dict) -> str:
    """Build a human-readable title for an event."""
    if event_type == "PushEvent":
        count = payload.get("size", 0)
        return f"Pushed {count} commit{'s' if count != 1 else ''}"
    if event_type == "IssuesEvent":
        action = payload.get("action", "")
        title = payload.get("issue", {}).get("title", "")
        return f"Issue {action}: {title}"
    if event_type == "PullRequestEvent":
        action = payload.get("action", "")
        title = payload.get("pull_request", {}).get("title", "")
        return f"PR {action}: {title}"
    if event_type == "ReleaseEvent":
        tag = payload.get("release", {}).get("tag_name", "")
        return f"Released {tag}"
    if event_type == "CreateEvent":
        ref_type = payload.get("ref_type", "")
        ref = payload.get("ref", "")
        return f"Created {ref_type} {ref}"
    return event_type
