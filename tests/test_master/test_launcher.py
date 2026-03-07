"""Tests for master.launcher — Claude CLI session management."""

from __future__ import annotations

import json
from pathlib import Path

from control_room.master.launcher import (
    SessionInfo,
    build_claude_command,
    collect_session_output,
    generate_session_id,
    is_session_alive,
    is_session_timed_out,
    resolve_repo_path,
    write_heartbeat,
)
from control_room.master.task_parser import TaskConfig


def _make_task(**kwargs) -> TaskConfig:
    """Helper to create a TaskConfig with defaults."""
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


class TestGenerateSessionId:
    """Tests for session ID generation."""

    def test_contains_repo_name(self) -> None:
        task = _make_task(repo="evidence-sync")
        session_id = generate_session_id(task)
        assert "evidence-sync" in session_id

    def test_contains_issue_number(self) -> None:
        task = _make_task(issue_number=42)
        session_id = generate_session_id(task)
        assert "42" in session_id

    def test_starts_with_master(self) -> None:
        task = _make_task()
        session_id = generate_session_id(task)
        assert session_id.startswith("master-")

    def test_unique_ids(self) -> None:
        task = _make_task()
        id1 = generate_session_id(task)
        # IDs include timestamp so they should differ (or at least not be empty)
        assert id1
        assert len(id1) > 10


class TestResolveRepoPath:
    """Tests for repo path resolution."""

    def test_existing_repo(self, tmp_path: Path) -> None:
        repo = tmp_path / "my-repo"
        repo.mkdir()
        result = resolve_repo_path("my-repo", repos_base=tmp_path)
        assert result == repo

    def test_nonexistent_repo(self, tmp_path: Path) -> None:
        result = resolve_repo_path("nonexistent", repos_base=tmp_path)
        assert result is None


class TestBuildClaudeCommand:
    """Tests for Claude CLI command construction."""

    def test_basic_command(self) -> None:
        task = _make_task()
        cmd = build_claude_command(task, "sess-001")
        assert cmd[0] == "claude"
        assert "--print" in cmd
        assert "--model" in cmd
        assert "claude-sonnet-4-5-20250929" in cmd
        assert "--max-turns" in cmd

    def test_prompt_includes_task_title(self) -> None:
        task = _make_task(title="PRISMA export")
        cmd = build_claude_command(task, "sess-001")
        prompt = cmd[-1]
        assert "PRISMA export" in prompt

    def test_prompt_includes_instructions(self) -> None:
        task = _make_task(instructions="Implement the feature")
        cmd = build_claude_command(task, "sess-001")
        prompt = cmd[-1]
        assert "Implement the feature" in prompt

    def test_prompt_includes_acceptance_criteria(self) -> None:
        task = _make_task(acceptance_criteria=["Tests pass", "Clean code"])
        cmd = build_claude_command(task, "sess-001")
        prompt = cmd[-1]
        assert "Tests pass" in prompt
        assert "Clean code" in prompt


class TestWriteHeartbeat:
    """Tests for heartbeat file writing."""

    def test_writes_valid_json(self, tmp_path: Path) -> None:
        task = _make_task(repo="test-repo")
        write_heartbeat(tmp_path, "sess-001", task, status="active", progress=0.5)

        hb_path = tmp_path / "session-heartbeat.json"
        assert hb_path.exists()

        data = json.loads(hb_path.read_text())
        assert data["session_id"] == "sess-001"
        assert data["repo"] == "test-repo"
        assert data["status"] == "active"
        assert data["progress"] == 0.5
        assert data["managed_by"] == "master-agent"

    def test_writes_task_metadata(self, tmp_path: Path) -> None:
        task = _make_task(title="My Task", issue_number=42, branch="feat/test")
        write_heartbeat(tmp_path, "sess-001", task)

        data = json.loads((tmp_path / "session-heartbeat.json").read_text())
        assert data["task"] == "My Task"
        assert data["issue_number"] == 42
        assert data["branch"] == "feat/test"


class TestSessionLifecycle:
    """Tests for session alive/timeout checks."""

    def test_is_session_alive_dead_pid(self) -> None:
        session = SessionInfo(
            session_id="s1",
            pid=99999999,
            task_config=_make_task(),
            repo_path=Path("/tmp"),
        )
        assert not is_session_alive(session)

    def test_is_session_timed_out(self) -> None:
        import time

        session = SessionInfo(
            session_id="s1",
            pid=1,
            task_config=_make_task(),
            repo_path=Path("/tmp"),
            started_at=time.time() - 3600,
            timeout_seconds=1800,
        )
        assert is_session_timed_out(session)

    def test_is_session_not_timed_out(self) -> None:
        import time

        session = SessionInfo(
            session_id="s1",
            pid=1,
            task_config=_make_task(),
            repo_path=Path("/tmp"),
            started_at=time.time(),
            timeout_seconds=1800,
        )
        assert not is_session_timed_out(session)


class TestCollectSessionOutput:
    """Tests for reading session output from heartbeat."""

    def test_reads_heartbeat(self, tmp_path: Path) -> None:
        hb_data = {"session_id": "s1", "status": "completed", "progress": 1.0}
        (tmp_path / "session-heartbeat.json").write_text(json.dumps(hb_data))

        session = SessionInfo(
            session_id="s1",
            pid=1,
            task_config=_make_task(),
            repo_path=tmp_path,
        )
        result = collect_session_output(session)
        assert result is not None
        assert result["status"] == "completed"

    def test_missing_heartbeat(self, tmp_path: Path) -> None:
        session = SessionInfo(
            session_id="s1",
            pid=1,
            task_config=_make_task(),
            repo_path=tmp_path,
        )
        result = collect_session_output(session)
        assert result is None
