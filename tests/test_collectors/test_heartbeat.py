from __future__ import annotations

import json
from pathlib import Path

from control_room.collectors.heartbeat import (
    collect_fleet_status,
    find_heartbeat_files,
    parse_heartbeat,
)
from control_room.models.heartbeat import SessionStatus


class TestFindHeartbeatFiles:
    """Tests for find_heartbeat_files scanning logic."""

    def test_finds_existing_heartbeat(self, tmp_path: Path) -> None:
        """Verify heartbeat files are found in repos that contain them."""
        repo_a = tmp_path / "repo-a"
        repo_a.mkdir()
        hb_file = repo_a / "session-heartbeat.json"
        hb_file.write_text("{}")

        result = find_heartbeat_files([repo_a])
        assert len(result) == 1
        assert result[0] == hb_file

    def test_skips_repos_without_heartbeat(self, tmp_path: Path) -> None:
        """Verify repos without heartbeat files are skipped."""
        repo_a = tmp_path / "repo-a"
        repo_a.mkdir()
        repo_b = tmp_path / "repo-b"
        repo_b.mkdir()
        (repo_a / "session-heartbeat.json").write_text("{}")

        result = find_heartbeat_files([repo_a, repo_b])
        assert len(result) == 1

    def test_empty_repos_list(self) -> None:
        """Verify empty list returns empty result."""
        result = find_heartbeat_files([])
        assert result == []

    def test_nonexistent_repo_path(self, tmp_path: Path) -> None:
        """Verify nonexistent paths are silently skipped."""
        fake_path = tmp_path / "nonexistent"
        result = find_heartbeat_files([fake_path])
        assert result == []

    def test_multiple_repos_with_heartbeats(self, tmp_path: Path) -> None:
        """Verify multiple repos with heartbeats are all found."""
        repos = []
        for name in ["repo-a", "repo-b", "repo-c"]:
            repo = tmp_path / name
            repo.mkdir()
            (repo / "session-heartbeat.json").write_text("{}")
            repos.append(repo)

        result = find_heartbeat_files(repos)
        assert len(result) == 3


class TestParseHeartbeat:
    """Tests for parse_heartbeat JSON parsing."""

    def test_valid_heartbeat(self, tmp_path: Path) -> None:
        """Verify valid JSON is parsed into a SessionHeartbeat."""
        hb_file = tmp_path / "session-heartbeat.json"
        data = {
            "session_id": "sess-001",
            "repo": "control-room",
            "branch": "main",
            "task": "Build fleet dashboard",
            "progress": 0.75,
            "status": "active",
            "cost_usd": 1.23,
            "tokens_used": 5000,
            "model": "claude-opus-4-6",
        }
        hb_file.write_text(json.dumps(data))

        result = parse_heartbeat(hb_file)
        assert result is not None
        assert result.session_id == "sess-001"
        assert result.repo == "control-room"
        assert result.branch == "main"
        assert result.progress == 0.75
        assert result.status == SessionStatus.ACTIVE
        assert result.cost_usd == 1.23
        assert result.tokens_used == 5000
        assert result.model == "claude-opus-4-6"

    def test_minimal_heartbeat(self, tmp_path: Path) -> None:
        """Verify minimal valid heartbeat with only required fields."""
        hb_file = tmp_path / "session-heartbeat.json"
        data = {"session_id": "sess-002", "repo": "test-repo"}
        hb_file.write_text(json.dumps(data))

        result = parse_heartbeat(hb_file)
        assert result is not None
        assert result.session_id == "sess-002"
        assert result.status == SessionStatus.IDLE
        assert result.progress == 0.0

    def test_invalid_json(self, tmp_path: Path) -> None:
        """Verify invalid JSON returns None instead of raising."""
        hb_file = tmp_path / "session-heartbeat.json"
        hb_file.write_text("not valid json {{{")

        result = parse_heartbeat(hb_file)
        assert result is None

    def test_missing_required_fields(self, tmp_path: Path) -> None:
        """Verify missing required fields returns None."""
        hb_file = tmp_path / "session-heartbeat.json"
        hb_file.write_text(json.dumps({"status": "active"}))

        result = parse_heartbeat(hb_file)
        assert result is None

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        """Verify nonexistent file returns None."""
        hb_file = tmp_path / "does-not-exist.json"
        result = parse_heartbeat(hb_file)
        assert result is None


class TestCollectFleetStatus:
    """Tests for collect_fleet_status aggregation."""

    def _write_heartbeat(
        self,
        repo_path: Path,
        session_id: str,
        status: str = "active",
        progress: float = 0.5,
        cost_usd: float = 1.0,
        tokens_used: int = 1000,
    ) -> None:
        """Helper to write a heartbeat file to a repo directory."""
        repo_path.mkdir(exist_ok=True)
        data = {
            "session_id": session_id,
            "repo": repo_path.name,
            "status": status,
            "progress": progress,
            "cost_usd": cost_usd,
            "tokens_used": tokens_used,
        }
        (repo_path / "session-heartbeat.json").write_text(json.dumps(data))

    def test_mixed_statuses(self, tmp_path: Path) -> None:
        """Verify aggregates are correct with mixed session statuses."""
        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        repo_c = tmp_path / "repo-c"
        repo_d = tmp_path / "repo-d"

        self._write_heartbeat(
            repo_a,
            "s1",
            status="active",
            progress=0.8,
            cost_usd=2.0,
            tokens_used=3000,
        )
        self._write_heartbeat(
            repo_b,
            "s2",
            status="blocked",
            progress=0.3,
            cost_usd=1.0,
            tokens_used=2000,
        )
        self._write_heartbeat(
            repo_c,
            "s3",
            status="completed",
            progress=1.0,
            cost_usd=5.0,
            tokens_used=10000,
        )
        self._write_heartbeat(
            repo_d,
            "s4",
            status="active",
            progress=0.6,
            cost_usd=1.5,
            tokens_used=4000,
        )

        fleet = collect_fleet_status([repo_a, repo_b, repo_c, repo_d])

        assert fleet.total_active == 2
        assert fleet.total_blocked == 1
        assert fleet.total_completed == 1
        assert fleet.total_idle == 0
        assert fleet.total_failed == 0
        assert len(fleet.sessions) == 4

        # Fleet progress = average of active sessions (0.8 + 0.6) / 2 = 0.7
        assert abs(fleet.fleet_progress - 0.7) < 0.001

        # Total cost = 2.0 + 1.0 + 5.0 + 1.5 = 9.5
        assert abs(fleet.fleet_cost_usd - 9.5) < 0.001

        # Total tokens = 3000 + 2000 + 10000 + 4000 = 19000
        assert fleet.fleet_tokens == 19000

    def test_empty_repos_list(self) -> None:
        """Verify empty repos returns empty fleet status."""
        fleet = collect_fleet_status([])

        assert fleet.sessions == []
        assert fleet.total_active == 0
        assert fleet.total_blocked == 0
        assert fleet.total_idle == 0
        assert fleet.total_completed == 0
        assert fleet.total_failed == 0
        assert fleet.fleet_progress == 0.0
        assert fleet.fleet_cost_usd == 0.0
        assert fleet.fleet_tokens == 0

    def test_repos_without_heartbeats(self, tmp_path: Path) -> None:
        """Verify repos without heartbeat files produce empty fleet."""
        repo_a = tmp_path / "repo-a"
        repo_a.mkdir()

        fleet = collect_fleet_status([repo_a])
        assert fleet.sessions == []
        assert fleet.total_active == 0

    def test_all_idle_sessions(self, tmp_path: Path) -> None:
        """Verify fleet progress is 0 when all sessions are idle."""
        repo_a = tmp_path / "repo-a"
        self._write_heartbeat(repo_a, "s1", status="idle", progress=0.0)

        fleet = collect_fleet_status([repo_a])
        assert fleet.total_idle == 1
        assert fleet.fleet_progress == 0.0

    def test_invalid_heartbeat_skipped(self, tmp_path: Path) -> None:
        """Verify invalid heartbeat files are skipped gracefully."""
        repo_a = tmp_path / "repo-a"
        repo_a.mkdir()
        (repo_a / "session-heartbeat.json").write_text("bad json")

        repo_b = tmp_path / "repo-b"
        self._write_heartbeat(repo_b, "s2", status="active")

        fleet = collect_fleet_status([repo_a, repo_b])
        assert len(fleet.sessions) == 1
        assert fleet.total_active == 1

    def test_single_failed_session(self, tmp_path: Path) -> None:
        """Verify a single failed session is counted correctly."""
        repo = tmp_path / "repo"
        self._write_heartbeat(repo, "s1", status="failed", progress=0.4, cost_usd=3.0)

        fleet = collect_fleet_status([repo])
        assert fleet.total_failed == 1
        assert fleet.total_active == 0
        assert fleet.fleet_progress == 0.0
        assert abs(fleet.fleet_cost_usd - 3.0) < 0.001
