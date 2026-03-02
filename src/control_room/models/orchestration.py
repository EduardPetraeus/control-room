from __future__ import annotations

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    """Request to decompose a high-level goal into subtasks."""

    goal: str
    context: str = ""
    max_subtasks: int = 10


class Subtask(BaseModel):
    """A decomposed subtask."""

    id: str
    title: str
    description: str = ""
    priority: str = "medium"
    depends_on: list[str] = Field(default_factory=list)
    agent_type: str = "code"
    estimated_effort: str = "m"  # xs/s/m/l/xl


class PlanResponse(BaseModel):
    """Response from task decomposition."""

    goal: str
    subtasks: list[Subtask] = Field(default_factory=list)
    critical_path: list[str] = Field(default_factory=list)
    estimated_total_effort: str = ""


class AssignRequest(BaseModel):
    """Request to assign tasks to available sessions."""

    task_ids: list[str] = Field(default_factory=list)
    # If empty, auto-discover from pick-next


class Assignment(BaseModel):
    """A task assigned to a session."""

    task_id: str
    task_title: str
    session_id: str
    repo: str


class AssignResponse(BaseModel):
    """Response from task assignment."""

    assignments: list[Assignment] = Field(default_factory=list)
    unassigned: list[str] = Field(default_factory=list)  # task IDs with no available session


class FleetAssessment(BaseModel):
    """Fleet-level status assessment."""

    total_sessions: int = 0
    active: int = 0
    blocked: int = 0
    idle: int = 0
    completed: int = 0
    failed: int = 0
    fleet_progress: float = 0.0
    fleet_cost_usd: float = 0.0
    blockers: list[str] = Field(default_factory=list)
    critical_paths: dict[str, list[str]] = Field(default_factory=dict)
    next_tasks: list[dict] = Field(default_factory=list)


class EscalateRequest(BaseModel):
    """Request to escalate a blocker."""

    description: str
    session_id: str = ""
    repo: str = ""
    severity: str = "medium"  # low/medium/high/critical


class EscalateResponse(BaseModel):
    """Response from escalation."""

    escalation_id: str
    action: str  # "queued" or "auto_resolved"
    message: str = ""
