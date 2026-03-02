from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Path to governance-framework automation scripts
GOVERNANCE_AUTOMATION_PATH = Path.home() / "Github repos" / "ai-governance-framework" / "automation"


def _ensure_governance_path() -> None:
    """Add governance automation scripts to sys.path if not already there."""
    path_str = str(GOVERNANCE_AUTOMATION_PATH)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def get_health_score(repo_path: Path) -> dict[str, Any]:
    """Calculate governance health score for a repo.

    Returns a dict with score, level, level_label, and checks.
    On failure, returns safe defaults and logs a warning.
    """
    try:
        _ensure_governance_path()
        from health_score_calculator import calculate_score

        return calculate_score(repo_path)
    except Exception as e:
        logger.warning("Health score calculation failed for %s: %s", repo_path, e)
        return {"score": 0, "level": 0, "level_label": "Unknown", "checks": []}


def get_drift_report(
    template_path: Path, target_path: Path, threshold: float = 0.5
) -> dict[str, Any]:
    """Detect governance drift from template.

    Returns a dict with aligned, missing_sections, drift_sections, recommendations.
    On failure, returns safe defaults and logs a warning.
    """
    try:
        _ensure_governance_path()
        from drift_detector import detect_drift

        return detect_drift(template_path, target_path, threshold)
    except Exception as e:
        logger.warning("Drift detection failed for %s: %s", target_path, e)
        return {
            "aligned": True,
            "missing_sections": [],
            "drift_sections": [],
            "recommendations": [],
        }


def get_cost_data(repo_path: Path) -> list[dict[str, Any]]:
    """Parse cost log from a repo.

    Returns a list of cost entry dicts.
    On failure, returns an empty list and logs a warning.
    """
    try:
        _ensure_governance_path()
        from governance_dashboard import parse_cost_log

        return parse_cost_log(repo_path)
    except Exception as e:
        logger.warning("Cost log parsing failed for %s: %s", repo_path, e)
        return []


def get_changelog_data(repo_path: Path) -> list[dict[str, Any]]:
    """Parse changelog data from a repo.

    Returns a list of changelog entry dicts.
    On failure, returns an empty list and logs a warning.
    """
    try:
        _ensure_governance_path()
        from governance_dashboard import parse_changelog

        return parse_changelog(repo_path)
    except Exception as e:
        logger.warning("Changelog parsing failed for %s: %s", repo_path, e)
        return []


def get_content_quality(repo_path: Path) -> dict[str, Any]:
    """Run content quality check on a repo.

    Returns a dict with files and summary.
    On failure, returns safe defaults and logs a warning.
    """
    try:
        _ensure_governance_path()
        from content_quality_checker import run_quality_check

        return run_quality_check(repo_path)
    except Exception as e:
        logger.warning("Content quality check failed for %s: %s", repo_path, e)
        return {
            "files": [],
            "summary": {"grade_a": 0, "grade_b": 0, "grade_c": 0, "grade_f": 0},
        }
