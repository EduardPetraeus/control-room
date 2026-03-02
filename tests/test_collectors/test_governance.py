from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from control_room.collectors.governance import (
    get_changelog_data,
    get_content_quality,
    get_cost_data,
    get_drift_report,
    get_health_score,
)


class TestGetHealthScore:
    """Tests for get_health_score governance collector."""

    @patch("control_room.collectors.governance._ensure_governance_path")
    def test_returns_structured_data(self, mock_ensure: MagicMock) -> None:
        """Verify health score returns dict with expected keys when import succeeds."""
        fake_result = {
            "score": 85,
            "level": 3,
            "level_label": "Gold",
            "checks": [
                {"name": "CLAUDE.md exists", "passed": True, "points": 10},
                {"name": "README.md exists", "passed": True, "points": 10},
            ],
        }
        mock_module = MagicMock()
        mock_module.calculate_score.return_value = fake_result

        with patch.dict("sys.modules", {"health_score_calculator": mock_module}):
            result = get_health_score(Path("/tmp/test-repo"))

        assert result["score"] == 85
        assert result["level"] == 3
        assert result["level_label"] == "Gold"
        assert len(result["checks"]) == 2

    def test_graceful_fallback_on_import_error(self) -> None:
        """Verify safe defaults when governance module import fails."""
        # Use a path that ensures the import fails (no real module available)
        with patch(
            "control_room.collectors.governance._ensure_governance_path",
            side_effect=ImportError("No module"),
        ):
            result = get_health_score(Path("/tmp/nonexistent"))

        assert result["score"] == 0
        assert result["level"] == 0
        assert result["level_label"] == "Unknown"
        assert result["checks"] == []

    def test_graceful_fallback_on_runtime_error(self) -> None:
        """Verify safe defaults when calculation raises RuntimeError."""
        mock_module = MagicMock()
        mock_module.calculate_score.side_effect = RuntimeError("broken")

        with (
            patch("control_room.collectors.governance._ensure_governance_path"),
            patch.dict("sys.modules", {"health_score_calculator": mock_module}),
        ):
            result = get_health_score(Path("/tmp/test-repo"))

        assert result["score"] == 0
        assert result["checks"] == []


class TestGetDriftReport:
    """Tests for get_drift_report governance collector."""

    @patch("control_room.collectors.governance._ensure_governance_path")
    def test_returns_structured_data(self, mock_ensure: MagicMock) -> None:
        """Verify drift report returns dict with expected keys."""
        fake_result = {
            "aligned": False,
            "missing_sections": ["security_protocol"],
            "drift_sections": [{"section": "conventions", "direction": "shorter", "ratio": 0.3}],
            "recommendations": ["Add security_protocol section"],
        }
        mock_module = MagicMock()
        mock_module.detect_drift.return_value = fake_result

        with patch.dict("sys.modules", {"drift_detector": mock_module}):
            result = get_drift_report(Path("/tmp/template"), Path("/tmp/target"), threshold=0.5)

        assert result["aligned"] is False
        assert "security_protocol" in result["missing_sections"]
        assert len(result["drift_sections"]) == 1
        assert len(result["recommendations"]) == 1

    def test_graceful_fallback_on_error(self) -> None:
        """Verify safe defaults when drift detection fails."""
        with patch(
            "control_room.collectors.governance._ensure_governance_path",
            side_effect=ImportError("No module"),
        ):
            result = get_drift_report(Path("/tmp/a"), Path("/tmp/b"))

        assert result["aligned"] is True
        assert result["missing_sections"] == []
        assert result["drift_sections"] == []
        assert result["recommendations"] == []


class TestGetCostData:
    """Tests for get_cost_data governance collector."""

    @patch("control_room.collectors.governance._ensure_governance_path")
    def test_returns_list(self, mock_ensure: MagicMock) -> None:
        """Verify cost data returns a list of cost entries."""
        fake_result = [
            {
                "session": "2026-03-01",
                "model": "claude-opus-4",
                "input_tokens": 1000,
                "output_tokens": 500,
                "cost_usd": 0.05,
            }
        ]
        mock_module = MagicMock()
        mock_module.parse_cost_log.return_value = fake_result

        with patch.dict("sys.modules", {"governance_dashboard": mock_module}):
            result = get_cost_data(Path("/tmp/test-repo"))

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["model"] == "claude-opus-4"

    def test_graceful_fallback_on_error(self) -> None:
        """Verify empty list when cost parsing fails."""
        with patch(
            "control_room.collectors.governance._ensure_governance_path",
            side_effect=ImportError("No module"),
        ):
            result = get_cost_data(Path("/tmp/nonexistent"))

        assert result == []


class TestGetChangelogData:
    """Tests for get_changelog_data governance collector."""

    @patch("control_room.collectors.governance._ensure_governance_path")
    def test_returns_list(self, mock_ensure: MagicMock) -> None:
        """Verify changelog data returns a list of entries."""
        fake_result = [{"version": "v0.3.0", "date": "2026-03-01", "changes": ["fix"]}]
        mock_module = MagicMock()
        mock_module.parse_changelog.return_value = fake_result

        with patch.dict("sys.modules", {"governance_dashboard": mock_module}):
            result = get_changelog_data(Path("/tmp/test-repo"))

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["version"] == "v0.3.0"

    def test_graceful_fallback_on_error(self) -> None:
        """Verify empty list when changelog parsing fails."""
        with patch(
            "control_room.collectors.governance._ensure_governance_path",
            side_effect=ImportError("No module"),
        ):
            result = get_changelog_data(Path("/tmp/nonexistent"))

        assert result == []


class TestGetContentQuality:
    """Tests for get_content_quality governance collector."""

    @patch("control_room.collectors.governance._ensure_governance_path")
    def test_returns_structured_data(self, mock_ensure: MagicMock) -> None:
        """Verify content quality returns dict with files and summary."""
        fake_result = {
            "files": [{"path": "README.md", "grade": "A", "issues": []}],
            "summary": {"grade_a": 1, "grade_b": 0, "grade_c": 0, "grade_f": 0},
        }
        mock_module = MagicMock()
        mock_module.run_quality_check.return_value = fake_result

        with patch.dict("sys.modules", {"content_quality_checker": mock_module}):
            result = get_content_quality(Path("/tmp/test-repo"))

        assert len(result["files"]) == 1
        assert result["summary"]["grade_a"] == 1

    def test_graceful_fallback_on_error(self) -> None:
        """Verify safe defaults when content quality check fails."""
        with patch(
            "control_room.collectors.governance._ensure_governance_path",
            side_effect=ImportError("No module"),
        ):
            result = get_content_quality(Path("/tmp/nonexistent"))

        assert result["files"] == []
        assert result["summary"]["grade_a"] == 0
        assert result["summary"]["grade_f"] == 0
