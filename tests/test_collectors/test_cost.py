from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from control_room.collectors.cost import (
    build_cost_summary,
    collect_repo_costs,
    collect_session_costs,
)
from control_room.config import RepoConfig


def _write_heartbeat(
    repo_path: Path,
    session_id: str,
    cost_usd: float = 1.0,
    tokens_used: int = 1000,
    model: str = "claude-opus-4-6",
    status: str = "active",
) -> None:
    """Helper to write a heartbeat file to a repo directory."""
    repo_path.mkdir(exist_ok=True)
    data = {
        "session_id": session_id,
        "repo": repo_path.name,
        "status": status,
        "cost_usd": cost_usd,
        "tokens_used": tokens_used,
        "model": model,
    }
    (repo_path / "session-heartbeat.json").write_text(json.dumps(data))


class TestCollectSessionCosts:
    """Tests for collecting cost data from heartbeat files."""

    def test_collects_costs_from_heartbeats(self, tmp_path: Path) -> None:
        """Verify cost data is extracted from heartbeat files."""
        repo_a = tmp_path / "repo-a"
        _write_heartbeat(repo_a, "sess-001", cost_usd=2.50, tokens_used=5000)

        costs = collect_session_costs([repo_a])
        assert len(costs) == 1
        assert costs[0].name == "sess-001"
        assert costs[0].cost_usd == 2.50
        assert costs[0].total_tokens == 5000
        assert costs[0].model == "claude-opus-4-6"

    def test_skips_zero_cost_sessions(self, tmp_path: Path) -> None:
        """Verify sessions with zero cost and zero tokens are skipped."""
        repo_a = tmp_path / "repo-a"
        _write_heartbeat(repo_a, "sess-001", cost_usd=0.0, tokens_used=0)

        costs = collect_session_costs([repo_a])
        assert len(costs) == 0

    def test_includes_zero_cost_with_tokens(self, tmp_path: Path) -> None:
        """Verify sessions with tokens but zero cost are included."""
        repo_a = tmp_path / "repo-a"
        _write_heartbeat(repo_a, "sess-001", cost_usd=0.0, tokens_used=1000)

        costs = collect_session_costs([repo_a])
        assert len(costs) == 1

    def test_multiple_repos(self, tmp_path: Path) -> None:
        """Verify costs from multiple repos are collected."""
        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        _write_heartbeat(repo_a, "sess-001", cost_usd=1.0, tokens_used=1000)
        _write_heartbeat(repo_b, "sess-002", cost_usd=2.0, tokens_used=2000)

        costs = collect_session_costs([repo_a, repo_b])
        assert len(costs) == 2

    def test_empty_repos_list(self) -> None:
        """Verify empty repos list returns empty costs."""
        costs = collect_session_costs([])
        assert costs == []

    def test_invalid_heartbeat_skipped(self, tmp_path: Path) -> None:
        """Verify invalid heartbeat files are skipped gracefully."""
        repo_a = tmp_path / "repo-a"
        repo_a.mkdir()
        (repo_a / "session-heartbeat.json").write_text("bad json")

        costs = collect_session_costs([repo_a])
        assert costs == []


class TestCollectRepoCosts:
    """Tests for collecting cost data from repo COST_LOG.md files."""

    def test_collects_from_governance_cost_data(self, tmp_path: Path) -> None:
        """Verify cost entries from governance collector are collected."""
        repo = RepoConfig(name="test-repo", path=str(tmp_path / "test-repo"))
        mock_entries = [
            {
                "session": "sess-100",
                "model": "claude-sonnet-4-20250514",
                "input_tokens": 1000,
                "output_tokens": 500,
                "cost": 0.75,
            },
        ]

        with patch("control_room.collectors.cost.get_cost_data", return_value=mock_entries):
            costs = collect_repo_costs([repo])

        assert len(costs) == 1
        assert costs[0].name == "sess-100"
        assert costs[0].model == "claude-sonnet-4-20250514"
        assert costs[0].input_tokens == 1000
        assert costs[0].output_tokens == 500
        assert costs[0].total_tokens == 1500
        assert costs[0].cost_usd == 0.75

    def test_uses_repo_name_as_fallback(self, tmp_path: Path) -> None:
        """Verify repo name is used when session field is missing."""
        repo = RepoConfig(name="my-repo", path=str(tmp_path / "my-repo"))
        mock_entries = [{"cost": 1.0}]

        with patch("control_room.collectors.cost.get_cost_data", return_value=mock_entries):
            costs = collect_repo_costs([repo])

        assert len(costs) == 1
        assert costs[0].name == "my-repo"

    def test_handles_cost_usd_field(self, tmp_path: Path) -> None:
        """Verify cost_usd field is used when cost field is missing."""
        repo = RepoConfig(name="test-repo", path=str(tmp_path / "test-repo"))
        mock_entries = [{"cost_usd": 3.50}]

        with patch("control_room.collectors.cost.get_cost_data", return_value=mock_entries):
            costs = collect_repo_costs([repo])

        assert len(costs) == 1
        assert costs[0].cost_usd == 3.50

    def test_handles_governance_failure(self, tmp_path: Path) -> None:
        """Verify governance collector failures are handled gracefully."""
        repo = RepoConfig(name="test-repo", path=str(tmp_path / "test-repo"))

        with patch(
            "control_room.collectors.cost.get_cost_data",
            side_effect=RuntimeError("boom"),
        ):
            costs = collect_repo_costs([repo])

        assert costs == []

    def test_empty_repos_list(self) -> None:
        """Verify empty repos list returns empty costs."""
        costs = collect_repo_costs([])
        assert costs == []


class TestBuildCostSummary:
    """Tests for building aggregated cost summary."""

    def test_aggregates_session_and_repo_costs(self, tmp_path: Path) -> None:
        """Verify costs from heartbeats and repos are aggregated."""
        repo_a = tmp_path / "repo-a"
        _write_heartbeat(repo_a, "sess-001", cost_usd=2.0, tokens_used=3000)

        repo = RepoConfig(name="repo-a", path=str(repo_a))
        mock_entries = [
            {
                "session": "log-001",
                "model": "opus",
                "input_tokens": 500,
                "output_tokens": 200,
                "cost": 1.0,
            },
        ]

        with patch("control_room.collectors.cost.get_cost_data", return_value=mock_entries):
            summary = build_cost_summary([repo], budget_limit_usd=50.0)

        assert summary.total_cost_usd == 3.0
        assert summary.total_tokens == 3700  # 3000 + 500 + 200
        assert len(summary.sessions) == 2

    def test_budget_alert_at_80_percent(self, tmp_path: Path) -> None:
        """Verify budget alert triggers at 80% usage."""
        repo_a = tmp_path / "repo-a"
        _write_heartbeat(repo_a, "sess-001", cost_usd=42.0, tokens_used=1000)

        repo = RepoConfig(name="repo-a", path=str(repo_a))

        with patch("control_room.collectors.cost.get_cost_data", return_value=[]):
            summary = build_cost_summary([repo], budget_limit_usd=50.0)

        assert summary.budget_alert is True
        assert summary.budget_used_pct >= 80.0

    def test_no_budget_alert_below_80_percent(self, tmp_path: Path) -> None:
        """Verify no budget alert below 80% usage."""
        repo_a = tmp_path / "repo-a"
        _write_heartbeat(repo_a, "sess-001", cost_usd=10.0, tokens_used=1000)

        repo = RepoConfig(name="repo-a", path=str(repo_a))

        with patch("control_room.collectors.cost.get_cost_data", return_value=[]):
            summary = build_cost_summary([repo], budget_limit_usd=50.0)

        assert summary.budget_alert is False
        assert summary.budget_used_pct < 80.0

    def test_empty_repos_return_zero_summary(self) -> None:
        """Verify empty repos return a zero-value summary."""
        summary = build_cost_summary([], budget_limit_usd=50.0)

        assert summary.total_cost_usd == 0.0
        assert summary.total_tokens == 0
        assert summary.sessions == []
        assert summary.budget_used_pct == 0.0
        assert summary.budget_alert is False
        assert summary.cost_by_model == {}

    def test_cost_by_model_groups_correctly(self, tmp_path: Path) -> None:
        """Verify costs are grouped by model name."""
        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        _write_heartbeat(
            repo_a, "sess-001", cost_usd=2.0, tokens_used=1000, model="claude-opus-4-6"
        )
        _write_heartbeat(
            repo_b, "sess-002", cost_usd=3.0, tokens_used=2000, model="claude-sonnet-4-20250514"
        )

        repos = [
            RepoConfig(name="repo-a", path=str(repo_a)),
            RepoConfig(name="repo-b", path=str(repo_b)),
        ]

        with patch("control_room.collectors.cost.get_cost_data", return_value=[]):
            summary = build_cost_summary(repos, budget_limit_usd=50.0)

        assert "claude-opus-4-6" in summary.cost_by_model
        assert "claude-sonnet-4-20250514" in summary.cost_by_model
        assert summary.cost_by_model["claude-opus-4-6"] == 2.0
        assert summary.cost_by_model["claude-sonnet-4-20250514"] == 3.0

    def test_unknown_model_grouped_as_unknown(self, tmp_path: Path) -> None:
        """Verify sessions without a model name are grouped as 'unknown'."""
        repo_a = tmp_path / "repo-a"
        _write_heartbeat(repo_a, "sess-001", cost_usd=1.0, tokens_used=500, model="")

        repo = RepoConfig(name="repo-a", path=str(repo_a))

        with patch("control_room.collectors.cost.get_cost_data", return_value=[]):
            summary = build_cost_summary([repo], budget_limit_usd=50.0)

        assert "unknown" in summary.cost_by_model
        assert summary.cost_by_model["unknown"] == 1.0

    def test_zero_budget_no_division_error(self) -> None:
        """Verify zero budget limit does not cause division by zero."""
        summary = build_cost_summary([], budget_limit_usd=0.0)

        assert summary.budget_used_pct == 0.0
        assert summary.budget_alert is False
