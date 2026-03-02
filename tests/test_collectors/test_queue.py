from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import yaml

from control_room.collectors.queue import (
    collect_blocked_tasks,
    collect_blocker_queue,
    collect_drift_alerts,
    collect_heartbeat_blockers,
)
from control_room.config import RepoConfig
from control_room.models.queue import QueueItemPriority, QueueItemType


class TestCollectHeartbeatBlockers:
    """Tests for heartbeat-based blocker collection."""

    def _write_heartbeat(
        self,
        repo_path: Path,
        session_id: str,
        status: str = "active",
        blocker: str | None = None,
    ) -> None:
        """Helper to write a heartbeat file."""
        repo_path.mkdir(exist_ok=True)
        data = {
            "session_id": session_id,
            "repo": repo_path.name,
            "status": status,
            "blocker": blocker,
        }
        (repo_path / "session-heartbeat.json").write_text(json.dumps(data))

    def test_finds_blocked_sessions(self, tmp_path: Path) -> None:
        """Blocked sessions with a blocker field produce queue items."""
        repo = tmp_path / "my-repo"
        self._write_heartbeat(repo, "sess-001", status="blocked", blocker="Need API key")

        items = collect_heartbeat_blockers([repo])
        assert len(items) == 1
        assert items[0].item_type == QueueItemType.AGENT_BLOCKED
        assert items[0].priority == QueueItemPriority.CRITICAL
        assert "Need API key" in items[0].description
        assert items[0].session_id == "sess-001"

    def test_ignores_active_sessions(self, tmp_path: Path) -> None:
        """Active sessions without blockers are not collected."""
        repo = tmp_path / "my-repo"
        self._write_heartbeat(repo, "sess-002", status="active")

        items = collect_heartbeat_blockers([repo])
        assert len(items) == 0

    def test_ignores_sessions_without_blocker_text(self, tmp_path: Path) -> None:
        """Sessions with status blocked but no blocker text are skipped."""
        repo = tmp_path / "my-repo"
        self._write_heartbeat(repo, "sess-003", status="blocked", blocker=None)

        items = collect_heartbeat_blockers([repo])
        assert len(items) == 0

    def test_empty_repos_list(self) -> None:
        """Empty repo list returns empty items."""
        items = collect_heartbeat_blockers([])
        assert items == []

    def test_nonexistent_repo_path(self, tmp_path: Path) -> None:
        """Nonexistent repo path is handled gracefully."""
        fake = tmp_path / "nonexistent"
        items = collect_heartbeat_blockers([fake])
        assert items == []

    def test_multiple_blocked_sessions(self, tmp_path: Path) -> None:
        """Multiple blocked sessions across repos are all collected."""
        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        self._write_heartbeat(repo_a, "sess-a", status="blocked", blocker="Missing config")
        self._write_heartbeat(repo_b, "sess-b", status="blocked", blocker="Waiting for review")

        items = collect_heartbeat_blockers([repo_a, repo_b])
        assert len(items) == 2


class TestCollectBlockedTasks:
    """Tests for YAML task-based blocker collection."""

    def _make_repo_with_tasks(
        self, tmp_path: Path, repo_name: str, tasks: list[dict]
    ) -> RepoConfig:
        """Helper to create a repo dir with a tasks YAML file."""
        repo_dir = tmp_path / repo_name
        task_dir = repo_dir / "tasks"
        task_dir.mkdir(parents=True)
        yaml_content = yaml.dump({"tasks": tasks})
        (task_dir / "tasks.yaml").write_text(yaml_content)
        return RepoConfig(name=repo_name, path=str(repo_dir), task_dir="tasks")

    def test_finds_blocked_tasks(self, tmp_path: Path) -> None:
        """Tasks with status 'blocked' are collected."""
        repo = self._make_repo_with_tasks(
            tmp_path,
            "my-repo",
            [
                {"id": "T-001", "title": "Deploy API", "status": "blocked"},
                {"id": "T-002", "title": "Write docs", "status": "todo"},
            ],
        )

        items = collect_blocked_tasks([repo])
        assert len(items) == 1
        assert items[0].item_type == QueueItemType.TASK_BLOCKED
        assert "Deploy API" in items[0].title

    def test_finds_tasks_with_blocked_by(self, tmp_path: Path) -> None:
        """Tasks with non-empty blocked_by are collected."""
        repo = self._make_repo_with_tasks(
            tmp_path,
            "my-repo",
            [
                {
                    "id": "T-003",
                    "title": "Run integration tests",
                    "status": "todo",
                    "blocked_by": ["T-001"],
                },
            ],
        )

        items = collect_blocked_tasks([repo])
        assert len(items) == 1
        assert "T-001" in items[0].description

    def test_empty_task_dir(self, tmp_path: Path) -> None:
        """Repos with no task directory produce no items."""
        repo_dir = tmp_path / "empty-repo"
        repo_dir.mkdir()
        repo = RepoConfig(name="empty-repo", path=str(repo_dir), task_dir="tasks")

        items = collect_blocked_tasks([repo])
        assert items == []

    def test_fallback_to_backlog_dir(self, tmp_path: Path) -> None:
        """Falls back to backlog/ when tasks/ does not exist."""
        repo_dir = tmp_path / "backlog-repo"
        backlog_dir = repo_dir / "backlog"
        backlog_dir.mkdir(parents=True)
        tasks = [{"id": "B-001", "title": "Blocked thing", "status": "blocked"}]
        (backlog_dir / "tasks.yaml").write_text(yaml.dump({"tasks": tasks}))
        repo = RepoConfig(name="backlog-repo", path=str(repo_dir), task_dir="tasks")

        items = collect_blocked_tasks([repo])
        assert len(items) == 1

    def test_graceful_on_invalid_yaml(self, tmp_path: Path) -> None:
        """Invalid YAML files are handled gracefully."""
        repo_dir = tmp_path / "bad-repo"
        task_dir = repo_dir / "tasks"
        task_dir.mkdir(parents=True)
        (task_dir / "bad.yaml").write_text("{{not valid yaml")
        repo = RepoConfig(name="bad-repo", path=str(repo_dir), task_dir="tasks")

        items = collect_blocked_tasks([repo])
        assert items == []


class TestCollectDriftAlerts:
    """Tests for governance drift blocker collection."""

    def test_returns_items_when_drift_detected(self, tmp_path: Path) -> None:
        """Drift report with aligned=False produces a queue item."""
        repo = RepoConfig(name="drifty-repo", path=str(tmp_path))
        drift_report = {
            "aligned": False,
            "missing_sections": ["## Boundaries"],
            "drift_sections": [],
            "recommendations": [],
        }

        with (
            patch(
                "control_room.collectors.queue.get_drift_report",
                return_value=drift_report,
            ),
            patch(
                "control_room.collectors.queue.GOVERNANCE_TEMPLATE",
                tmp_path / "template.md",
            ),
        ):
            (tmp_path / "template.md").write_text("# Template")
            items = collect_drift_alerts([repo])

        assert len(items) == 1
        assert items[0].item_type == QueueItemType.GOVERNANCE_DRIFT
        assert items[0].priority == QueueItemPriority.LOW
        assert "Boundaries" in items[0].description

    def test_no_items_when_aligned(self, tmp_path: Path) -> None:
        """Aligned drift report produces no items."""
        repo = RepoConfig(name="good-repo", path=str(tmp_path))
        drift_report = {
            "aligned": True,
            "missing_sections": [],
            "drift_sections": [],
            "recommendations": [],
        }

        with (
            patch(
                "control_room.collectors.queue.get_drift_report",
                return_value=drift_report,
            ),
            patch(
                "control_room.collectors.queue.GOVERNANCE_TEMPLATE",
                tmp_path / "template.md",
            ),
        ):
            (tmp_path / "template.md").write_text("# Template")
            items = collect_drift_alerts([repo])

        assert items == []

    def test_no_items_when_template_missing(self, tmp_path: Path) -> None:
        """Missing governance template returns empty list."""
        repo = RepoConfig(name="repo", path=str(tmp_path))

        with patch(
            "control_room.collectors.queue.GOVERNANCE_TEMPLATE",
            tmp_path / "nonexistent.md",
        ):
            items = collect_drift_alerts([repo])

        assert items == []

    def test_graceful_on_exception(self, tmp_path: Path) -> None:
        """Exceptions during drift check are handled gracefully."""
        repo = RepoConfig(name="error-repo", path=str(tmp_path))

        with (
            patch(
                "control_room.collectors.queue.get_drift_report",
                side_effect=RuntimeError("boom"),
            ),
            patch(
                "control_room.collectors.queue.GOVERNANCE_TEMPLATE",
                tmp_path / "template.md",
            ),
        ):
            (tmp_path / "template.md").write_text("# Template")
            items = collect_drift_alerts([repo])

        assert items == []


class TestCollectBlockerQueue:
    """Tests for the aggregate blocker queue."""

    def test_sorts_by_priority(self, tmp_path: Path) -> None:
        """Queue items are sorted critical-first."""
        # Create one blocked heartbeat (critical) and one blocked task (medium)
        repo_dir = tmp_path / "sort-repo"
        repo_dir.mkdir()

        # Heartbeat: blocked agent
        hb_data = {
            "session_id": "sess-sort",
            "repo": "sort-repo",
            "status": "blocked",
            "blocker": "Need decision",
        }
        (repo_dir / "session-heartbeat.json").write_text(json.dumps(hb_data))

        # Tasks: one blocked task
        task_dir = repo_dir / "tasks"
        task_dir.mkdir()
        tasks = [{"id": "T-SORT", "title": "Blocked task", "status": "blocked"}]
        (task_dir / "tasks.yaml").write_text(yaml.dump({"tasks": tasks}))

        repo = RepoConfig(name="sort-repo", path=str(repo_dir), task_dir="tasks")

        with patch(
            "control_room.collectors.queue.GOVERNANCE_TEMPLATE",
            tmp_path / "nonexistent.md",
        ):
            queue = collect_blocker_queue([repo])

        assert len(queue.items) >= 2
        # First item should be critical (heartbeat blocker)
        assert queue.items[0].priority == QueueItemPriority.CRITICAL
        # Later items should be medium or lower
        assert queue.items[-1].priority.value in ("medium", "low")

    def test_empty_repos_return_empty_queue(self) -> None:
        """No repos produce an empty queue."""
        with patch(
            "control_room.collectors.queue.GOVERNANCE_TEMPLATE",
            Path("/nonexistent/template.md"),
        ):
            queue = collect_blocker_queue([])

        assert queue.items == []
        assert queue.total_critical == 0
        assert queue.total_high == 0
        assert queue.total_medium == 0
        assert queue.total_low == 0

    def test_counts_match_items(self, tmp_path: Path) -> None:
        """Priority counts match the actual items in the queue."""
        repo_dir = tmp_path / "count-repo"
        repo_dir.mkdir()

        hb_data = {
            "session_id": "sess-count",
            "repo": "count-repo",
            "status": "blocked",
            "blocker": "Stuck",
        }
        (repo_dir / "session-heartbeat.json").write_text(json.dumps(hb_data))

        repo = RepoConfig(name="count-repo", path=str(repo_dir), task_dir="tasks")

        with patch(
            "control_room.collectors.queue.GOVERNANCE_TEMPLATE",
            tmp_path / "nonexistent.md",
        ):
            queue = collect_blocker_queue([repo])

        critical_items = [i for i in queue.items if i.priority == QueueItemPriority.CRITICAL]
        assert queue.total_critical == len(critical_items)

    def test_nonexistent_directories_handled(self, tmp_path: Path) -> None:
        """Repos pointing to nonexistent dirs produce no errors."""
        repo = RepoConfig(name="ghost-repo", path=str(tmp_path / "ghost"), task_dir="tasks")

        with patch(
            "control_room.collectors.queue.GOVERNANCE_TEMPLATE",
            tmp_path / "nonexistent.md",
        ):
            queue = collect_blocker_queue([repo])

        assert queue.items == []
