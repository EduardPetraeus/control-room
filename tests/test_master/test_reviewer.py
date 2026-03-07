"""Tests for master.reviewer — post-completion review pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from control_room.master.launcher import SessionInfo
from control_room.master.reviewer import should_review
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


class TestShouldReview:
    """Tests for should_review determination."""

    @patch("control_room.master.reviewer.subprocess.run")
    def test_review_needed_with_commits(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Review needed when branch has commits ahead of main."""
        mock_run.return_value = MagicMock(returncode=0, stdout="abc123 feat: add thing\n")

        session = SessionInfo(
            session_id="s1",
            pid=1,
            task_config=_make_task(branch="feat/test"),
            repo_path=tmp_path,
        )
        assert should_review(session) is True

    @patch("control_room.master.reviewer.subprocess.run")
    def test_no_review_no_commits(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """No review when branch has no commits ahead of main."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        session = SessionInfo(
            session_id="s1",
            pid=1,
            task_config=_make_task(branch="feat/empty"),
            repo_path=tmp_path,
        )
        assert should_review(session) is False

    def test_no_review_no_branch(self, tmp_path: Path) -> None:
        """No review when task has no branch specified."""
        session = SessionInfo(
            session_id="s1",
            pid=1,
            task_config=_make_task(branch=""),
            repo_path=tmp_path,
        )
        assert should_review(session) is False

    def test_no_review_nonexistent_path(self) -> None:
        """No review when repo path doesn't exist."""
        session = SessionInfo(
            session_id="s1",
            pid=1,
            task_config=_make_task(),
            repo_path=Path("/nonexistent/path"),
        )
        assert should_review(session) is False
