from __future__ import annotations

from pydantic import BaseModel, Field


class SessionCost(BaseModel):
    """Cost data for a single session or repo."""

    name: str  # session ID or repo name
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


class CostSummary(BaseModel):
    """Aggregated cost data for the fleet."""

    total_cost_usd: float = 0.0
    total_tokens: int = 0
    sessions: list[SessionCost] = Field(default_factory=list)
    budget_limit_usd: float = 0.0  # from config
    budget_used_pct: float = 0.0
    budget_alert: bool = False  # true when approaching/exceeding limit
    cost_by_model: dict[str, float] = Field(default_factory=dict)  # model_name -> total_cost
