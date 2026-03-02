"""Tests for the ai-pm TaskEngine integration collector."""

from __future__ import annotations

from pathlib import Path

import pytest

from control_room.collectors.task_engine import (
    detect_cycles,
    get_all_critical_paths,
    get_critical_path,
    get_dependency_order,
    get_fleet_next_tasks,
    get_next_task,
)
from control_room.config import RepoConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo(tmp_path: Path, name: str = "test-repo", task_dir: str = "backlog") -> RepoConfig:
    """Create a RepoConfig pointing at tmp_path with the given task_dir."""
    return RepoConfig(name=name, path=str(tmp_path), task_dir=task_dir)


def _write_task(directory: Path, task_id: str, **overrides: object) -> Path:
    """Write a single ai-pm task YAML file (TASK-xxx.yaml format).

    The file name must start with ``TASK-`` for ai-pm's parser to pick it up.
    """
    defaults = {
        "id": task_id,
        "title": f"Task {task_id}",
        "status": "ready",
        "priority": "medium",
        "agent": "code",
        "review": "auto-merge",
        "created": "2026-03-02",
    }
    defaults.update(overrides)

    lines = []
    for key, value in defaults.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        elif value is None:
            lines.append(f"{key}:")
        else:
            lines.append(f"{key}: {_yaml_value(value)}")

    file_path = directory / f"{task_id}.yaml"
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return file_path


def _yaml_value(val: object) -> str:
    """Format a Python value for inline YAML."""
    if isinstance(val, str):
        return f'"{val}"'
    if isinstance(val, bool):
        return "true" if val else "false"
    return str(val)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_with_chain(tmp_path: Path) -> RepoConfig:
    """Create a repo with a 3-task dependency chain: TASK-001 -> TASK-002 -> TASK-003."""
    backlog = tmp_path / "backlog"
    backlog.mkdir()

    _write_task(backlog, "TASK-001", priority="high")
    _write_task(backlog, "TASK-002", depends_on=["TASK-001"], priority="medium")
    _write_task(backlog, "TASK-003", depends_on=["TASK-002"], priority="low")

    return _make_repo(tmp_path)


@pytest.fixture
def repo_empty(tmp_path: Path) -> RepoConfig:
    """Create a repo with an empty backlog directory."""
    backlog = tmp_path / "backlog"
    backlog.mkdir()
    return _make_repo(tmp_path)


@pytest.fixture
def repo_no_dir(tmp_path: Path) -> RepoConfig:
    """Create a repo pointing to a path with no task directory at all."""
    return _make_repo(tmp_path, task_dir="nonexistent")


# ---------------------------------------------------------------------------
# Tests: get_critical_path
# ---------------------------------------------------------------------------


class TestGetCriticalPath:
    def test_returns_chain(self, repo_with_chain: RepoConfig) -> None:
        """Critical path should be the full dependency chain."""
        cp = get_critical_path(repo_with_chain)
        assert cp == ["TASK-001", "TASK-002", "TASK-003"]

    def test_empty_backlog_returns_empty(self, repo_empty: RepoConfig) -> None:
        """An empty backlog should return an empty critical path."""
        cp = get_critical_path(repo_empty)
        assert cp == []

    def test_missing_dir_returns_empty(self, repo_no_dir: RepoConfig) -> None:
        """A missing task directory should return an empty list, not raise."""
        cp = get_critical_path(repo_no_dir)
        assert cp == []

    def test_done_tasks_excluded(self, tmp_path: Path) -> None:
        """Tasks with status=done should not appear in the critical path."""
        backlog = tmp_path / "backlog"
        backlog.mkdir()

        _write_task(backlog, "TASK-001", status="done")
        _write_task(backlog, "TASK-002", depends_on=["TASK-001"], status="ready")
        _write_task(backlog, "TASK-003", depends_on=["TASK-002"], status="ready")

        repo = _make_repo(tmp_path)
        cp = get_critical_path(repo)

        # TASK-001 is done, so the critical path only contains the active tasks
        assert "TASK-001" not in cp
        assert "TASK-002" in cp
        assert "TASK-003" in cp


# ---------------------------------------------------------------------------
# Tests: get_next_task
# ---------------------------------------------------------------------------


class TestGetNextTask:
    def test_picks_highest_priority(self, tmp_path: Path) -> None:
        """Should return the highest-priority ready task."""
        backlog = tmp_path / "backlog"
        backlog.mkdir()

        _write_task(backlog, "TASK-001", priority="low", status="ready")
        _write_task(backlog, "TASK-002", priority="critical", status="ready")
        _write_task(backlog, "TASK-003", priority="high", status="ready")

        repo = _make_repo(tmp_path)
        task = get_next_task(repo)

        assert task is not None
        assert task["id"] == "TASK-002"

    def test_skips_non_ready(self, tmp_path: Path) -> None:
        """Tasks not in 'ready' status should be skipped."""
        backlog = tmp_path / "backlog"
        backlog.mkdir()

        _write_task(backlog, "TASK-001", priority="critical", status="in_progress")
        _write_task(backlog, "TASK-002", priority="low", status="ready")

        repo = _make_repo(tmp_path)
        task = get_next_task(repo)

        assert task is not None
        assert task["id"] == "TASK-002"

    def test_filters_by_agent_type(self, tmp_path: Path) -> None:
        """When agent_type is specified, only matching tasks are returned."""
        backlog = tmp_path / "backlog"
        backlog.mkdir()

        _write_task(backlog, "TASK-001", priority="high", status="ready", agent="docs")
        _write_task(backlog, "TASK-002", priority="medium", status="ready", agent="code")

        repo = _make_repo(tmp_path)
        task = get_next_task(repo, agent_type="code")

        assert task is not None
        assert task["id"] == "TASK-002"

    def test_returns_none_when_empty(self, repo_empty: RepoConfig) -> None:
        """Should return None when there are no tasks."""
        assert get_next_task(repo_empty) is None

    def test_returns_none_when_no_dir(self, repo_no_dir: RepoConfig) -> None:
        """Should return None when the task directory does not exist."""
        assert get_next_task(repo_no_dir) is None

    def test_skips_assigned_tasks(self, tmp_path: Path) -> None:
        """Tasks with an assignee should be skipped by pick_next."""
        backlog = tmp_path / "backlog"
        backlog.mkdir()

        _write_task(backlog, "TASK-001", priority="critical", status="ready", assignee="alice")
        _write_task(backlog, "TASK-002", priority="low", status="ready")

        repo = _make_repo(tmp_path)
        task = get_next_task(repo)

        assert task is not None
        assert task["id"] == "TASK-002"

    def test_respects_dependency_readiness(self, tmp_path: Path) -> None:
        """A ready task with unfinished dependencies should not be picked."""
        backlog = tmp_path / "backlog"
        backlog.mkdir()

        _write_task(backlog, "TASK-001", priority="high", status="ready")
        _write_task(
            backlog,
            "TASK-002",
            priority="critical",
            status="ready",
            depends_on=["TASK-001"],
        )

        repo = _make_repo(tmp_path)
        task = get_next_task(repo)

        # TASK-002 is critical but blocked by undone TASK-001
        assert task is not None
        assert task["id"] == "TASK-001"


# ---------------------------------------------------------------------------
# Tests: detect_cycles
# ---------------------------------------------------------------------------


class TestDetectCycles:
    def test_no_cycles(self, repo_with_chain: RepoConfig) -> None:
        """A linear chain should have no cycles."""
        cycles = detect_cycles(repo_with_chain)
        assert cycles == []

    def test_empty_returns_empty(self, repo_empty: RepoConfig) -> None:
        """Empty backlog should return no cycles."""
        assert detect_cycles(repo_empty) == []

    def test_missing_dir_returns_empty(self, repo_no_dir: RepoConfig) -> None:
        """Missing dir should return empty list, not raise."""
        assert detect_cycles(repo_no_dir) == []


# ---------------------------------------------------------------------------
# Tests: get_dependency_order
# ---------------------------------------------------------------------------


class TestGetDependencyOrder:
    def test_topological_sort(self, repo_with_chain: RepoConfig) -> None:
        """Dependencies should come before dependents."""
        order = get_dependency_order(repo_with_chain)

        assert len(order) == 3
        # TASK-001 must come before TASK-002, TASK-002 before TASK-003
        assert order.index("TASK-001") < order.index("TASK-002")
        assert order.index("TASK-002") < order.index("TASK-003")

    def test_empty_returns_empty(self, repo_empty: RepoConfig) -> None:
        """Empty backlog should return empty list."""
        assert get_dependency_order(repo_empty) == []

    def test_missing_dir_returns_empty(self, repo_no_dir: RepoConfig) -> None:
        """Missing dir should return empty list."""
        assert get_dependency_order(repo_no_dir) == []


# ---------------------------------------------------------------------------
# Tests: get_all_critical_paths (fleet-wide)
# ---------------------------------------------------------------------------


class TestGetAllCriticalPaths:
    def test_aggregates_across_repos(self, tmp_path: Path) -> None:
        """Should return critical paths keyed by repo name."""
        # Repo A: has a chain
        repo_a_path = tmp_path / "repo-a"
        backlog_a = repo_a_path / "backlog"
        backlog_a.mkdir(parents=True)
        _write_task(backlog_a, "TASK-001", priority="high")
        _write_task(backlog_a, "TASK-002", depends_on=["TASK-001"])

        # Repo B: empty
        repo_b_path = tmp_path / "repo-b"
        (repo_b_path / "backlog").mkdir(parents=True)

        repos = [
            _make_repo(repo_a_path, name="repo-a"),
            _make_repo(repo_b_path, name="repo-b"),
        ]
        result = get_all_critical_paths(repos)

        assert "repo-a" in result
        assert "repo-b" not in result  # empty backlog => no critical path
        assert result["repo-a"] == ["TASK-001", "TASK-002"]

    def test_empty_list(self) -> None:
        """No repos should return empty dict."""
        assert get_all_critical_paths([]) == {}


# ---------------------------------------------------------------------------
# Tests: get_fleet_next_tasks (fleet-wide)
# ---------------------------------------------------------------------------


class TestGetFleetNextTasks:
    def test_collects_from_multiple_repos(self, tmp_path: Path) -> None:
        """Should return one next-task per repo that has ready tasks."""
        repo_a_path = tmp_path / "repo-a"
        backlog_a = repo_a_path / "backlog"
        backlog_a.mkdir(parents=True)
        _write_task(backlog_a, "TASK-001", priority="high", status="ready")

        repo_b_path = tmp_path / "repo-b"
        backlog_b = repo_b_path / "backlog"
        backlog_b.mkdir(parents=True)
        _write_task(backlog_b, "TASK-010", priority="critical", status="ready")

        repos = [
            _make_repo(repo_a_path, name="repo-a"),
            _make_repo(repo_b_path, name="repo-b"),
        ]
        tasks = get_fleet_next_tasks(repos)

        assert len(tasks) == 2
        repo_names = {t["_repo"] for t in tasks}
        assert repo_names == {"repo-a", "repo-b"}

    def test_skips_repos_without_tasks(self, tmp_path: Path) -> None:
        """Repos with no ready tasks should not contribute."""
        repo_a_path = tmp_path / "repo-a"
        backlog_a = repo_a_path / "backlog"
        backlog_a.mkdir(parents=True)
        _write_task(backlog_a, "TASK-001", priority="high", status="ready")

        repo_b_path = tmp_path / "repo-b"
        (repo_b_path / "backlog").mkdir(parents=True)

        repos = [
            _make_repo(repo_a_path, name="repo-a"),
            _make_repo(repo_b_path, name="repo-b"),
        ]
        tasks = get_fleet_next_tasks(repos)

        assert len(tasks) == 1
        assert tasks[0]["_repo"] == "repo-a"

    def test_empty_list(self) -> None:
        """No repos should return empty list."""
        assert get_fleet_next_tasks([]) == []

    def test_filters_by_agent_type(self, tmp_path: Path) -> None:
        """Agent type filter should propagate to each repo's pick_next."""
        backlog = tmp_path / "backlog"
        backlog.mkdir()
        _write_task(backlog, "TASK-001", priority="high", status="ready", agent="docs")
        _write_task(backlog, "TASK-002", priority="medium", status="ready", agent="code")

        repos = [_make_repo(tmp_path, name="my-repo")]
        tasks = get_fleet_next_tasks(repos, agent_type="code")

        assert len(tasks) == 1
        assert tasks[0]["id"] == "TASK-002"
        assert tasks[0]["_repo"] == "my-repo"


# ---------------------------------------------------------------------------
# Tests: task_dir fallback
# ---------------------------------------------------------------------------


class TestTaskDirFallback:
    def test_configured_dir_used_first(self, tmp_path: Path) -> None:
        """When task_dir exists, it should be used instead of backlog/."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _write_task(tasks_dir, "TASK-001", priority="high", status="ready")

        # Also create backlog with a different task to verify fallback is NOT used
        backlog = tmp_path / "backlog"
        backlog.mkdir()
        _write_task(backlog, "TASK-099", priority="low", status="ready")

        repo = RepoConfig(name="test", path=str(tmp_path), task_dir="tasks")
        task = get_next_task(repo)

        assert task is not None
        assert task["id"] == "TASK-001"

    def test_falls_back_to_backlog(self, tmp_path: Path) -> None:
        """When configured task_dir does not exist, fall back to backlog/."""
        backlog = tmp_path / "backlog"
        backlog.mkdir()
        _write_task(backlog, "TASK-001", priority="high", status="ready")

        repo = RepoConfig(name="test", path=str(tmp_path), task_dir="nonexistent")
        task = get_next_task(repo)

        assert task is not None
        assert task["id"] == "TASK-001"
