"""Tests for master.daemon — the main tick-loop and decision engine."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from control_room.master.daemon import (
    DaemonConfig,
    DaemonState,
    MasterDaemon,
    load_daemon_config,
)
from control_room.master.launcher import SessionInfo
from control_room.master.task_parser import TaskConfig


def _make_task(**kwargs) -> TaskConfig:
    defaults = {
        "issue_number": 1,
        "issue_url": "https://github.com/test/repo/issues/1",
        "title": "Test task",
        "repo": "test-repo",
        "branch": "feat/test",
        "model": "claude-sonnet-4-5-20250929",
        "budget": 5.0,
        "max_turns": 30,
        "instructions": "Do the thing",
        "acceptance_criteria": ["It works"],
        "status": "Ready",
    }
    defaults.update(kwargs)
    return TaskConfig(**defaults)


class TestDaemonConfig:
    """Tests for daemon configuration."""

    def test_default_config(self) -> None:
        config = DaemonConfig()
        assert config.tick_interval == 60
        assert config.max_concurrent == 2
        assert config.session_timeout == 1800
        assert config.review_on_completion is True
        assert config.notify_on_completion is True
        assert config.auto_handover is True

    def test_custom_config(self) -> None:
        config = DaemonConfig(
            tick_interval=30,
            max_concurrent=4,
            session_timeout=3600,
        )
        assert config.tick_interval == 30
        assert config.max_concurrent == 4
        assert config.session_timeout == 3600


class TestLoadDaemonConfig:
    """Tests for loading config from YAML."""

    def test_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        config = load_daemon_config(tmp_path / "nonexistent.yaml")
        assert config.tick_interval == 60
        assert config.max_concurrent == 2

    def test_empty_file_returns_defaults(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")
        config = load_daemon_config(config_file)
        assert config.tick_interval == 60

    def test_loads_master_agent_section(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "master_agent:\n"
            "  tick_interval: 30\n"
            "  max_concurrent: 4\n"
            "  session_timeout: 3600\n"
            "  review_on_completion: false\n"
        )
        config = load_daemon_config(config_file)
        assert config.tick_interval == 30
        assert config.max_concurrent == 4
        assert config.session_timeout == 3600
        assert config.review_on_completion is False

    def test_no_master_agent_section(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("server:\n  host: localhost\n")
        config = load_daemon_config(config_file)
        assert config.tick_interval == 60


class TestDaemonState:
    """Tests for daemon runtime state."""

    def test_initial_state(self) -> None:
        state = DaemonState()
        assert state.active_sessions == {}
        assert state.completed_sessions == []
        assert state.failed_sessions == []
        assert state.tick_count == 0
        assert state.running is True


class TestMasterDaemon:
    """Tests for the MasterDaemon class."""

    def test_get_status_empty(self) -> None:
        daemon = MasterDaemon(DaemonConfig())
        status = daemon.get_status()
        assert status["running"] is True
        assert status["active_sessions"] == 0
        assert status["completed_sessions"] == 0
        assert status["failed_sessions"] == 0
        assert status["max_concurrent"] == 2

    def test_is_task_running_false(self) -> None:
        daemon = MasterDaemon(DaemonConfig())
        task = _make_task(issue_number=42, repo="my-repo")
        assert daemon._is_task_running(task) is False

    def test_is_task_running_true(self) -> None:
        daemon = MasterDaemon(DaemonConfig())
        task = _make_task(issue_number=42, repo="my-repo")
        session = SessionInfo(
            session_id="s1",
            pid=1,
            task_config=task,
            repo_path=Path("/tmp"),
        )
        daemon.state.active_sessions["s1"] = session
        assert daemon._is_task_running(task) is True

    @patch("control_room.master.daemon.fetch_ready_tasks")
    def test_tick_no_tasks(self, mock_fetch: MagicMock) -> None:
        """Tick with no ready tasks does nothing."""
        mock_fetch.return_value = []
        daemon = MasterDaemon(DaemonConfig())
        daemon._tick()
        assert len(daemon.state.active_sessions) == 0

    @patch("control_room.master.daemon.launch_session")
    @patch("control_room.master.daemon.fetch_ready_tasks")
    def test_tick_launches_session(self, mock_fetch: MagicMock, mock_launch: MagicMock) -> None:
        """Tick with ready task launches a session."""
        task = _make_task(title="Build feature")
        mock_fetch.return_value = [task]

        session = SessionInfo(
            session_id="s1",
            pid=12345,
            task_config=task,
            repo_path=Path("/tmp"),
        )
        mock_launch.return_value = session

        daemon = MasterDaemon(DaemonConfig())
        with patch.object(daemon, "_update_issue_status"):
            with patch.object(daemon, "_save_state"):
                daemon._tick()

        assert len(daemon.state.active_sessions) == 1
        assert "s1" in daemon.state.active_sessions

    @patch("control_room.master.daemon.launch_session")
    @patch("control_room.master.daemon.fetch_ready_tasks")
    @patch("control_room.master.daemon.is_session_alive", return_value=True)
    @patch("control_room.master.daemon.is_session_timed_out", return_value=False)
    def test_tick_respects_max_concurrent(
        self,
        mock_timeout: MagicMock,
        mock_alive: MagicMock,
        mock_fetch: MagicMock,
        mock_launch: MagicMock,
    ) -> None:
        """Tick does not exceed max_concurrent sessions."""
        config = DaemonConfig(max_concurrent=1)
        daemon = MasterDaemon(config)

        # Already at capacity
        existing_task = _make_task(issue_number=1)
        daemon.state.active_sessions["s0"] = SessionInfo(
            session_id="s0",
            pid=1,
            task_config=existing_task,
            repo_path=Path("/tmp"),
        )

        daemon._tick()
        mock_fetch.assert_not_called()
        assert len(daemon.state.active_sessions) == 1

    @patch("control_room.master.daemon.is_session_alive")
    def test_check_sessions_detects_completion(self, mock_alive: MagicMock) -> None:
        """Completed sessions are detected and removed."""
        mock_alive.return_value = False
        daemon = MasterDaemon(DaemonConfig(review_on_completion=False, notify_on_completion=False))

        task = _make_task()
        daemon.state.active_sessions["s1"] = SessionInfo(
            session_id="s1",
            pid=1,
            task_config=task,
            repo_path=Path("/tmp"),
        )

        with patch("control_room.master.daemon.needs_handover", return_value=False):
            with patch.object(daemon, "_update_issue_status"):
                daemon._check_sessions()

        assert len(daemon.state.active_sessions) == 0
        assert "s1" in daemon.state.completed_sessions

    def test_save_state(self, tmp_path: Path) -> None:
        """State is persisted to JSON file."""
        daemon = MasterDaemon(DaemonConfig())
        daemon.state.tick_count = 10

        # Override the state file path for testing
        state_file = tmp_path / "state.json"
        with patch("control_room.master.daemon.STATE_FILE", state_file):
            daemon._save_state()

        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["tick_count"] == 10

    @patch("control_room.master.daemon.is_session_timed_out")
    @patch("control_room.master.daemon.is_session_alive")
    @patch("control_room.master.daemon.stop_session")
    def test_timeout_handling(
        self, mock_stop: MagicMock, mock_alive: MagicMock, mock_timeout: MagicMock, tmp_path: Path
    ) -> None:
        """Timed-out sessions are stopped and marked failed."""
        mock_alive.return_value = True
        mock_timeout.return_value = True
        mock_stop.return_value = True

        daemon = MasterDaemon(DaemonConfig(notify_on_completion=False))
        task = _make_task()
        daemon.state.active_sessions["s1"] = SessionInfo(
            session_id="s1",
            pid=1,
            task_config=task,
            repo_path=tmp_path,
        )

        with patch.object(daemon, "_update_issue_status"):
            daemon._check_sessions()

        assert "s1" in daemon.state.failed_sessions
        assert len(daemon.state.active_sessions) == 0
        mock_stop.assert_called_once()
