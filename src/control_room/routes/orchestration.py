from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Request

from control_room.models.orchestration import (
    Assignment,
    AssignRequest,
    AssignResponse,
    EscalateRequest,
    EscalateResponse,
    FleetAssessment,
    PlanRequest,
    PlanResponse,
    Subtask,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent/master", tags=["orchestration"])


@router.post("/plan", response_model=PlanResponse)
async def plan_tasks(request: Request, plan_req: PlanRequest):
    """Decompose a high-level goal into subtasks with dependencies.

    This is a structural decomposition — it breaks goals into logical steps
    based on common software development patterns. It does NOT use LLMs.
    """
    subtasks = _decompose_goal(plan_req.goal, plan_req.context, plan_req.max_subtasks)

    # Derive critical path from dependencies
    critical_path = [s.id for s in subtasks if not s.depends_on] + [
        s.id for s in subtasks if s.depends_on
    ]

    return PlanResponse(
        goal=plan_req.goal,
        subtasks=subtasks,
        critical_path=critical_path[: plan_req.max_subtasks],
        estimated_total_effort=_estimate_total(subtasks),
    )


@router.post("/assign", response_model=AssignResponse)
async def assign_tasks(request: Request, assign_req: AssignRequest):
    """Route tasks to available idle sessions."""
    aggregator = request.app.state.aggregator
    fleet = aggregator.get_fleet_status()

    # Get idle sessions
    idle_sessions = [s for s in fleet.sessions if s.status.value == "idle"]

    # Get tasks to assign
    if assign_req.task_ids:
        task_ids = assign_req.task_ids
    else:
        # Auto-discover from pick-next across all repos
        next_tasks = aggregator.get_next_tasks()
        task_ids = [t.get("id", "") for t in next_tasks]

    assignments = []
    unassigned = []

    for i, task_id in enumerate(task_ids):
        if i < len(idle_sessions):
            session = idle_sessions[i]
            assignments.append(
                Assignment(
                    task_id=task_id,
                    task_title=task_id,  # Would be enriched with real title in full impl
                    session_id=session.session_id,
                    repo=session.repo,
                )
            )
        else:
            unassigned.append(task_id)

    return AssignResponse(assignments=assignments, unassigned=unassigned)


@router.get("/status", response_model=FleetAssessment)
async def fleet_status(request: Request):
    """Fleet-level assessment aggregating all data sources."""
    aggregator = request.app.state.aggregator

    fleet = aggregator.get_fleet_status()
    queue = aggregator.get_blocker_queue()
    critical_paths = aggregator.get_critical_paths()
    next_tasks = aggregator.get_next_tasks()

    return FleetAssessment(
        total_sessions=len(fleet.sessions),
        active=fleet.total_active,
        blocked=fleet.total_blocked,
        idle=fleet.total_idle,
        completed=fleet.total_completed,
        failed=fleet.total_failed,
        fleet_progress=fleet.fleet_progress,
        fleet_cost_usd=fleet.fleet_cost_usd,
        blockers=[item.title for item in queue.items[:10]],
        critical_paths=critical_paths,
        next_tasks=next_tasks[:10],
    )


@router.post("/escalate", response_model=EscalateResponse)
async def escalate_blocker(request: Request, escalation: EscalateRequest):
    """Escalate a blocker — adds to queue for human resolution."""
    escalation_id = f"esc-{uuid.uuid4().hex[:8]}"

    # For now, all escalations are queued for human resolution
    # Future: pattern matching for auto-resolution
    logger.info(
        "Escalation %s: %s (severity=%s, repo=%s, session=%s)",
        escalation_id,
        escalation.description,
        escalation.severity,
        escalation.repo,
        escalation.session_id,
    )

    return EscalateResponse(
        escalation_id=escalation_id,
        action="queued",
        message=f"Blocker queued for human resolution: {escalation.description[:100]}",
    )


def _decompose_goal(goal: str, context: str, max_subtasks: int) -> list[Subtask]:
    """Rule-based goal decomposition into subtasks."""
    # Simple structural decomposition
    # In production, this would call an LLM
    subtasks = []
    base_id = f"sub-{uuid.uuid4().hex[:6]}"

    subtasks.append(
        Subtask(
            id=f"{base_id}-1",
            title=f"Research: {goal[:60]}",
            description=f"Investigate requirements and existing code for: {goal}",
            priority="high",
            agent_type="code",
            estimated_effort="s",
        )
    )

    subtasks.append(
        Subtask(
            id=f"{base_id}-2",
            title=f"Implement: {goal[:60]}",
            description=f"Build the core implementation for: {goal}. {context}",
            priority="high",
            depends_on=[f"{base_id}-1"],
            agent_type="code",
            estimated_effort="l",
        )
    )

    subtasks.append(
        Subtask(
            id=f"{base_id}-3",
            title=f"Test: {goal[:60]}",
            description=f"Write and run tests for: {goal}",
            priority="medium",
            depends_on=[f"{base_id}-2"],
            agent_type="test",
            estimated_effort="m",
        )
    )

    subtasks.append(
        Subtask(
            id=f"{base_id}-4",
            title=f"Document: {goal[:60]}",
            description=f"Update documentation for: {goal}",
            priority="low",
            depends_on=[f"{base_id}-3"],
            agent_type="docs",
            estimated_effort="s",
        )
    )

    return subtasks[:max_subtasks]


def _estimate_total(subtasks: list[Subtask]) -> str:
    """Estimate total effort from subtask estimates."""
    effort_map = {"xs": 1, "s": 2, "m": 4, "l": 8, "xl": 16}
    total = sum(effort_map.get(s.estimated_effort, 4) for s in subtasks)
    if total <= 4:
        return "s"
    elif total <= 12:
        return "m"
    elif total <= 24:
        return "l"
    return "xl"
