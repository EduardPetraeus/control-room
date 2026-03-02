from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from control_room.app import create_app
from control_room.models.heartbeat import FleetStatus, SessionHeartbeat, SessionStatus
from control_room.models.queue import BlockerQueue, QueueItem, QueueItemPriority, QueueItemType


def _mock_aggregator(
    fleet: FleetStatus | None = None,
    queue: BlockerQueue | None = None,
    critical_paths: dict | None = None,
    next_tasks: list | None = None,
) -> MagicMock:
    """Build a mock aggregator with the given return values."""
    aggregator = MagicMock()
    aggregator.get_fleet_status.return_value = fleet or FleetStatus()
    aggregator.get_blocker_queue.return_value = queue or BlockerQueue()
    aggregator.get_critical_paths.return_value = critical_paths or {}
    aggregator.get_next_tasks.return_value = next_tasks or []
    return aggregator


# --- /agent/master/plan ---


def test_plan_returns_subtasks() -> None:
    """Plan endpoint decomposes a goal into 4 default subtasks."""
    app = create_app()
    with TestClient(app) as client:
        response = client.post("/agent/master/plan", json={"goal": "Add user auth"})
        assert response.status_code == 200
        data = response.json()
        assert data["goal"] == "Add user auth"
        assert len(data["subtasks"]) == 4
        assert data["subtasks"][0]["title"].startswith("Research:")
        assert data["subtasks"][1]["title"].startswith("Implement:")
        assert data["subtasks"][2]["title"].startswith("Test:")
        assert data["subtasks"][3]["title"].startswith("Document:")
        assert data["critical_path"]
        assert data["estimated_total_effort"]


def test_plan_respects_max_subtasks() -> None:
    """Plan endpoint respects the max_subtasks parameter."""
    app = create_app()
    with TestClient(app) as client:
        response = client.post("/agent/master/plan", json={"goal": "Fix bug", "max_subtasks": 2})
        assert response.status_code == 200
        data = response.json()
        assert len(data["subtasks"]) <= 2


def test_plan_includes_dependencies() -> None:
    """Plan subtasks should have dependency chains."""
    app = create_app()
    with TestClient(app) as client:
        response = client.post("/agent/master/plan", json={"goal": "Build feature X"})
        data = response.json()
        subtasks = data["subtasks"]
        # First subtask has no dependencies
        assert subtasks[0]["depends_on"] == []
        # Second depends on first
        assert subtasks[1]["depends_on"] == [subtasks[0]["id"]]


def test_plan_with_context() -> None:
    """Plan endpoint uses context in subtask descriptions."""
    app = create_app()
    with TestClient(app) as client:
        response = client.post(
            "/agent/master/plan",
            json={"goal": "Add caching", "context": "Use Redis for session store"},
        )
        data = response.json()
        # Context appears in the implement subtask description
        impl_subtask = data["subtasks"][1]
        assert "Redis" in impl_subtask["description"]


def test_plan_effort_estimation() -> None:
    """Plan should estimate total effort based on subtask sizes."""
    app = create_app()
    with TestClient(app) as client:
        response = client.post("/agent/master/plan", json={"goal": "Small task"})
        data = response.json()
        # Default 4 subtasks: s(2) + l(8) + m(4) + s(2) = 16 -> "l"
        assert data["estimated_total_effort"] == "l"


# --- /agent/master/assign ---


def test_assign_with_idle_sessions() -> None:
    """Assign endpoint matches tasks to idle sessions."""
    fleet = FleetStatus(
        sessions=[
            SessionHeartbeat(session_id="sess-1", repo="repo-a", status=SessionStatus.IDLE),
            SessionHeartbeat(session_id="sess-2", repo="repo-b", status=SessionStatus.IDLE),
        ],
        total_idle=2,
    )
    app = create_app()
    with TestClient(app) as client:
        app.state.aggregator = _mock_aggregator(fleet=fleet)
        response = client.post("/agent/master/assign", json={"task_ids": ["task-1", "task-2"]})
        assert response.status_code == 200
        data = response.json()
        assert len(data["assignments"]) == 2
        assert data["unassigned"] == []
        assert data["assignments"][0]["task_id"] == "task-1"
        assert data["assignments"][0]["session_id"] == "sess-1"


def test_assign_more_tasks_than_sessions() -> None:
    """Assign returns unassigned tasks when sessions are insufficient."""
    fleet = FleetStatus(
        sessions=[
            SessionHeartbeat(session_id="sess-1", repo="repo-a", status=SessionStatus.IDLE),
        ],
        total_idle=1,
    )
    app = create_app()
    with TestClient(app) as client:
        app.state.aggregator = _mock_aggregator(fleet=fleet)
        response = client.post(
            "/agent/master/assign", json={"task_ids": ["task-1", "task-2", "task-3"]}
        )
        data = response.json()
        assert len(data["assignments"]) == 1
        assert len(data["unassigned"]) == 2


def test_assign_auto_discovers_tasks() -> None:
    """Assign with empty task_ids auto-discovers from pick-next."""
    fleet = FleetStatus(
        sessions=[
            SessionHeartbeat(session_id="sess-1", repo="repo-a", status=SessionStatus.IDLE),
        ],
        total_idle=1,
    )
    next_tasks = [{"id": "auto-task-1", "_repo": "repo-a"}]
    app = create_app()
    with TestClient(app) as client:
        app.state.aggregator = _mock_aggregator(fleet=fleet, next_tasks=next_tasks)
        response = client.post("/agent/master/assign", json={})
        assert response.status_code == 200
        data = response.json()
        assert len(data["assignments"]) == 1
        assert data["assignments"][0]["task_id"] == "auto-task-1"


def test_assign_skips_active_sessions() -> None:
    """Assign only considers idle sessions, not active or blocked."""
    fleet = FleetStatus(
        sessions=[
            SessionHeartbeat(session_id="sess-active", repo="repo-a", status=SessionStatus.ACTIVE),
            SessionHeartbeat(
                session_id="sess-blocked", repo="repo-b", status=SessionStatus.BLOCKED
            ),
        ],
        total_active=1,
        total_blocked=1,
    )
    app = create_app()
    with TestClient(app) as client:
        app.state.aggregator = _mock_aggregator(fleet=fleet)
        response = client.post("/agent/master/assign", json={"task_ids": ["task-1"]})
        data = response.json()
        assert len(data["assignments"]) == 0
        assert data["unassigned"] == ["task-1"]


# --- /agent/master/status ---


def test_status_returns_fleet_assessment() -> None:
    """Status endpoint returns all fleet assessment fields."""
    fleet = FleetStatus(
        sessions=[
            SessionHeartbeat(session_id="sess-1", repo="repo-a", status=SessionStatus.ACTIVE),
        ],
        total_active=1,
        fleet_progress=0.5,
        fleet_cost_usd=1.23,
    )
    queue = BlockerQueue(
        items=[
            QueueItem(
                id="q-1",
                item_type=QueueItemType.AGENT_BLOCKED,
                priority=QueueItemPriority.CRITICAL,
                title="Agent stuck on tests",
            ),
        ],
        total_critical=1,
    )
    critical_paths = {"repo-a": ["task-1", "task-2"]}
    next_tasks = [{"id": "next-1", "_repo": "repo-a"}]

    app = create_app()
    with TestClient(app) as client:
        app.state.aggregator = _mock_aggregator(
            fleet=fleet, queue=queue, critical_paths=critical_paths, next_tasks=next_tasks
        )
        response = client.get("/agent/master/status")
        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions"] == 1
        assert data["active"] == 1
        assert data["fleet_progress"] == 0.5
        assert data["fleet_cost_usd"] == 1.23
        assert "Agent stuck on tests" in data["blockers"]
        assert data["critical_paths"] == {"repo-a": ["task-1", "task-2"]}
        assert len(data["next_tasks"]) == 1


def test_status_empty_fleet() -> None:
    """Status endpoint handles empty fleet gracefully."""
    app = create_app()
    with TestClient(app) as client:
        app.state.aggregator = _mock_aggregator()
        response = client.get("/agent/master/status")
        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions"] == 0
        assert data["active"] == 0
        assert data["blockers"] == []
        assert data["critical_paths"] == {}
        assert data["next_tasks"] == []


# --- /agent/master/escalate ---


def test_escalate_queues_blocker() -> None:
    """Escalate endpoint returns queued status with escalation ID."""
    app = create_app()
    with TestClient(app) as client:
        response = client.post(
            "/agent/master/escalate",
            json={
                "description": "Can't access database",
                "severity": "high",
                "repo": "control-room",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "queued"
        assert data["escalation_id"].startswith("esc-")
        assert "Can't access database" in data["message"]


def test_escalate_truncates_long_description() -> None:
    """Escalate message should truncate very long descriptions."""
    app = create_app()
    with TestClient(app) as client:
        long_desc = "x" * 500
        response = client.post(
            "/agent/master/escalate",
            json={"description": long_desc},
        )
        data = response.json()
        # Message should contain truncated version (first 100 chars)
        assert len(data["message"]) < 500


def test_escalate_with_session_info() -> None:
    """Escalate accepts optional session_id and repo."""
    app = create_app()
    with TestClient(app) as client:
        response = client.post(
            "/agent/master/escalate",
            json={
                "description": "Build failed",
                "session_id": "sess-42",
                "repo": "my-repo",
                "severity": "critical",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "queued"
