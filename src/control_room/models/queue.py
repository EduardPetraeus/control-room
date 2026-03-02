from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class QueueItemType(str, Enum):
    """Types of items in the blocker queue."""

    AGENT_BLOCKED = "agent_blocked"
    CI_FAILED = "ci_failed"
    GOVERNANCE_DRIFT = "governance_drift"
    TASK_BLOCKED = "task_blocked"


class QueueItemPriority(str, Enum):
    """Priority ordering for queue items."""

    CRITICAL = "critical"  # cost-blocking, agent completely stuck
    HIGH = "high"  # CI-blocking, failing tests
    MEDIUM = "medium"  # questions, decisions needed
    LOW = "low"  # drift alerts, style issues


class QueueItem(BaseModel):
    """Single item in the blocker queue."""

    id: str
    item_type: QueueItemType
    priority: QueueItemPriority = QueueItemPriority.MEDIUM
    title: str
    description: str = ""
    source_repo: str = ""
    source_url: str = ""  # GitHub issue URL, CI run URL, etc.
    created_at: datetime = Field(default_factory=datetime.now)
    session_id: str = ""  # Which agent session is blocked


class BlockerQueue(BaseModel):
    """Aggregated blocker queue."""

    items: list[QueueItem] = Field(default_factory=list)
    total_critical: int = 0
    total_high: int = 0
    total_medium: int = 0
    total_low: int = 0
