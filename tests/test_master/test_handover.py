"""Tests for master.handover — context limit detection and continuation prompts."""

from __future__ import annotations

import json
from pathlib import Path

from control_room.master.handover import (
    build_continuation_prompt,
    detect_context_limit,
    needs_handover,
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


def _make_session(tmp_path: Path, **kwargs) -> SessionInfo:
    return SessionInfo(
        session_id=kwargs.get("session_id", "s1"),
        pid=kwargs.get("pid", 1),
        task_config=_make_task(
            **{k: v for k, v in kwargs.items() if k not in ("session_id", "pid")}
        ),
        repo_path=tmp_path,
    )


class TestNeedsHandover:
    """Tests for needs_handover detection."""

    def test_incomplete_active_needs_handover(self, tmp_path: Path) -> None:
        """Active session with low progress needs handover."""
        hb = {"status": "active", "progress": 0.3}
        (tmp_path / "session-heartbeat.json").write_text(json.dumps(hb))

        session = _make_session(tmp_path)
        assert needs_handover(session) is True

    def test_completed_high_progress_no_handover(self, tmp_path: Path) -> None:
        """Completed session with high progress does not need handover."""
        hb = {"status": "completed", "progress": 0.95}
        (tmp_path / "session-heartbeat.json").write_text(json.dumps(hb))

        session = _make_session(tmp_path)
        assert needs_handover(session) is False

    def test_failed_no_handover(self, tmp_path: Path) -> None:
        """Failed sessions should not auto-handover."""
        hb = {"status": "failed", "progress": 0.2}
        (tmp_path / "session-heartbeat.json").write_text(json.dumps(hb))

        session = _make_session(tmp_path)
        assert needs_handover(session) is False

    def test_blocked_no_handover(self, tmp_path: Path) -> None:
        """Blocked sessions should not auto-handover."""
        hb = {"status": "blocked", "progress": 0.5}
        (tmp_path / "session-heartbeat.json").write_text(json.dumps(hb))

        session = _make_session(tmp_path)
        assert needs_handover(session) is False

    def test_no_heartbeat_no_handover(self, tmp_path: Path) -> None:
        """No heartbeat file means no handover."""
        session = _make_session(tmp_path)
        assert needs_handover(session) is False

    def test_completed_low_progress_needs_handover(self, tmp_path: Path) -> None:
        """Completed session with low progress needs handover."""
        hb = {"status": "completed", "progress": 0.4}
        (tmp_path / "session-heartbeat.json").write_text(json.dumps(hb))

        session = _make_session(tmp_path)
        assert needs_handover(session) is True


class TestDetectContextLimit:
    """Tests for context limit detection in session output."""

    def test_detects_context_window(self) -> None:
        output = "Error: exceeded context window limit, truncating..."
        assert detect_context_limit(output) is True

    def test_detects_token_limit(self) -> None:
        output = "Warning: approaching token limit"
        assert detect_context_limit(output) is True

    def test_no_context_limit(self) -> None:
        output = "Task completed successfully. All tests pass."
        assert detect_context_limit(output) is False

    def test_case_insensitive(self) -> None:
        output = "CONTEXT WINDOW exceeded"
        assert detect_context_limit(output) is True


class TestBuildContinuationPrompt:
    """Tests for continuation prompt generation."""

    def test_includes_previous_session(self) -> None:
        task = _make_task(title="PRISMA export")
        prompt = build_continuation_prompt(task, "sess-001")
        assert "sess-001" in prompt
        assert "PRISMA export" in prompt

    def test_includes_branch(self) -> None:
        task = _make_task(branch="feat/iteration-8")
        prompt = build_continuation_prompt(task, "sess-001")
        assert "feat/iteration-8" in prompt

    def test_includes_progress_summary(self) -> None:
        task = _make_task()
        prompt = build_continuation_prompt(task, "sess-001", progress_summary="3 commits done")
        assert "3 commits done" in prompt

    def test_includes_acceptance_criteria(self) -> None:
        task = _make_task(acceptance_criteria=["Tests pass", "Clean code"])
        prompt = build_continuation_prompt(task, "sess-001")
        assert "Tests pass" in prompt

    def test_includes_handover_rules(self) -> None:
        task = _make_task()
        prompt = build_continuation_prompt(task, "sess-001")
        assert "Do NOT redo work" in prompt
        assert "Conventional Commits" in prompt
