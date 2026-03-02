from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from control_room.collectors.github import (
    _build_event_title,
    get_project_items,
    get_repo_events_sync,
)


class TestGetProjectItems:
    @patch("control_room.collectors.github.subprocess.run")
    def test_parses_project_items(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "items": [
                        {
                            "title": "Fix login bug",
                            "status": "In Progress",
                            "type": "Issue",
                            "content": {
                                "url": "https://github.com/org/repo/issues/1",
                                "repository": "repo",
                            },
                            "labels": [{"name": "bug"}],
                            "assignees": [{"login": "user1"}],
                        }
                    ]
                }
            ),
            stderr="",
        )
        items = get_project_items()
        assert len(items) == 1
        assert items[0].title == "Fix login bug"
        assert items[0].status == "In Progress"

    @patch("control_room.collectors.github.subprocess.run")
    def test_handles_empty_response(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='{"items": []}', stderr="")
        items = get_project_items()
        assert items == []

    @patch("control_room.collectors.github.subprocess.run")
    def test_handles_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="auth required")
        items = get_project_items()
        assert items == []

    @patch("control_room.collectors.github.subprocess.run")
    def test_handles_timeout(self, mock_run):
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("gh", 30)
        items = get_project_items()
        assert items == []


class TestGetRepoEvents:
    @patch("control_room.collectors.github.subprocess.run")
    def test_parses_events(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "type": "PushEvent",
                        "created_at": "2026-03-01T10:00:00Z",
                        "actor": {"login": "user1"},
                        "payload": {"size": 3},
                    }
                ]
            ),
            stderr="",
        )
        events = get_repo_events_sync("owner", "repo")
        assert len(events) == 1
        assert events[0].event_type == "commit"
        assert events[0].color == "green"
        assert "3 commits" in events[0].title

    @patch("control_room.collectors.github.subprocess.run")
    def test_handles_api_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        events = get_repo_events_sync("owner", "repo")
        assert events == []


class TestBuildEventTitle:
    def test_push_event(self):
        assert "3 commits" in _build_event_title("PushEvent", {"size": 3})

    def test_issue_event(self):
        result = _build_event_title(
            "IssuesEvent",
            {"action": "opened", "issue": {"title": "Bug report"}},
        )
        assert "opened" in result
        assert "Bug report" in result

    def test_unknown_event(self):
        result = _build_event_title("SomeNewEvent", {})
        assert result == "SomeNewEvent"
