"""Tests for master.task_parser — GitHub Issue body parsing."""

from __future__ import annotations

from control_room.master.task_parser import (
    DEFAULT_BUDGET,
    DEFAULT_MAX_TURNS,
    DEFAULT_MODEL,
    build_task_config,
    parse_issue_body,
)

SAMPLE_BODY = """## Agent Task

**Repo:** evidence-sync
**Branch:** feat/iteration-8
**Model:** claude-sonnet-4-5-20250929
**Budget:** $5
**Max turns:** 60

## Instructions

Implement the PRISMA flow diagram export as SVG.
Use the existing diagram module as a base.

## Acceptance Criteria

- [ ] SVG export generates valid output
- [ ] Unit tests for all new functions
- [ ] ruff clean
"""

MINIMAL_BODY = """## Agent Task

**Repo:** my-repo

## Instructions

Fix the bug.
"""


class TestParseIssueBody:
    """Tests for parse_issue_body field extraction."""

    def test_full_body(self) -> None:
        """Parse a fully populated issue body."""
        result = parse_issue_body(SAMPLE_BODY)
        assert result["repo"] == "evidence-sync"
        assert result["branch"] == "feat/iteration-8"
        assert result["model"] == "claude-sonnet-4-5-20250929"
        assert result["budget"] == 5.0
        assert result["max_turns"] == 60

    def test_instructions_extracted(self) -> None:
        """Verify instructions section is captured."""
        result = parse_issue_body(SAMPLE_BODY)
        instructions = result["instructions"]
        assert isinstance(instructions, str)
        assert "PRISMA flow diagram" in instructions
        assert "existing diagram module" in instructions

    def test_acceptance_criteria_extracted(self) -> None:
        """Verify acceptance criteria are parsed as a list."""
        result = parse_issue_body(SAMPLE_BODY)
        criteria = result["acceptance_criteria"]
        assert isinstance(criteria, list)
        assert len(criteria) == 3
        assert "SVG export generates valid output" in criteria
        assert "ruff clean" in criteria

    def test_minimal_body(self) -> None:
        """Parse a body with only repo and instructions."""
        result = parse_issue_body(MINIMAL_BODY)
        assert result["repo"] == "my-repo"
        assert "branch" not in result
        assert "model" not in result
        assert "Fix the bug" in str(result.get("instructions", ""))

    def test_empty_body(self) -> None:
        """Empty body returns empty dict."""
        result = parse_issue_body("")
        assert isinstance(result, dict)
        assert "repo" not in result

    def test_budget_without_dollar_sign(self) -> None:
        """Budget field works without $ prefix."""
        body = "**Budget:** 10.50"
        result = parse_issue_body(body)
        assert result["budget"] == 10.50

    def test_case_insensitive_fields(self) -> None:
        """Fields are matched case-insensitively."""
        body = "**repo:** my-repo\n**BRANCH:** main"
        result = parse_issue_body(body)
        assert result["repo"] == "my-repo"
        assert result["branch"] == "main"

    def test_criteria_with_checked_boxes(self) -> None:
        """Checked checkboxes are still parsed."""
        body = """## Acceptance Criteria

- [x] Already done
- [ ] Not yet
"""
        result = parse_issue_body(body)
        criteria = result["acceptance_criteria"]
        assert isinstance(criteria, list)
        assert len(criteria) == 2
        assert "Already done" in criteria

    def test_criteria_with_plain_bullets(self) -> None:
        """Plain bullet points without checkboxes are parsed."""
        body = """## Acceptance Criteria

- First item
- Second item
"""
        result = parse_issue_body(body)
        criteria = result["acceptance_criteria"]
        assert isinstance(criteria, list)
        assert len(criteria) == 2


class TestBuildTaskConfig:
    """Tests for build_task_config from issue data."""

    def test_full_config(self) -> None:
        """Build config from full issue body."""
        config = build_task_config(
            issue_number=42,
            issue_url="https://github.com/EduardPetraeus/evidence-sync/issues/42",
            title="PRISMA SVG Export",
            body=SAMPLE_BODY,
            status="Ready",
        )
        assert config.issue_number == 42
        assert config.repo == "evidence-sync"
        assert config.branch == "feat/iteration-8"
        assert config.model == "claude-sonnet-4-5-20250929"
        assert config.budget == 5.0
        assert config.max_turns == 60
        assert config.status == "Ready"
        assert len(config.acceptance_criteria) == 3

    def test_defaults_applied(self) -> None:
        """Missing fields get defaults."""
        config = build_task_config(
            issue_number=1,
            issue_url="",
            title="Simple task",
            body=MINIMAL_BODY,
        )
        assert config.model == DEFAULT_MODEL
        assert config.budget == DEFAULT_BUDGET
        assert config.max_turns == DEFAULT_MAX_TURNS
        assert config.branch == ""

    def test_empty_body(self) -> None:
        """Empty body produces config with defaults."""
        config = build_task_config(
            issue_number=1,
            issue_url="",
            title="Empty",
            body="",
        )
        assert config.repo == ""
        assert config.instructions == ""
        assert config.acceptance_criteria == []
