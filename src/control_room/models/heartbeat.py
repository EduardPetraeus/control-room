from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Status of a Claude Code session."""

    ACTIVE = "active"
    BLOCKED = "blocked"
    IDLE = "idle"
    COMPLETED = "completed"
    FAILED = "failed"


class SessionHeartbeat(BaseModel):
    """Heartbeat from a single Claude Code session."""

    session_id: str
    repo: str
    branch: str = "unknown"
    task: str = ""
    progress: float = 0.0  # 0.0 to 1.0
    status: SessionStatus = SessionStatus.IDLE
    blocker: str | None = None
    cost_usd: float = 0.0
    tokens_used: int = 0
    model: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)


class FleetStatus(BaseModel):
    """Aggregated fleet status across all sessions."""

    sessions: list[SessionHeartbeat] = Field(default_factory=list)
    total_active: int = 0
    total_blocked: int = 0
    total_idle: int = 0
    total_completed: int = 0
    total_failed: int = 0
    fleet_progress: float = 0.0  # average progress across active sessions
    fleet_cost_usd: float = 0.0
    fleet_tokens: int = 0
