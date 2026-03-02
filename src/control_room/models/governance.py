from __future__ import annotations

from pydantic import BaseModel, Field


class HealthCheck(BaseModel):
    """Single health check item."""

    name: str
    passed: bool
    points: int = 0


class GovernanceHealth(BaseModel):
    """Governance health score for a repo."""

    score: int = 0
    level: int = 0
    level_label: str = "Unknown"
    checks: list[HealthCheck] = Field(default_factory=list)


class DriftAlert(BaseModel):
    """Single drift detection finding."""

    section: str
    direction: str = ""  # "shorter" or "longer"
    ratio: float = 0.0


class DriftReport(BaseModel):
    """Drift detection result for a repo."""

    aligned: bool = True
    missing_sections: list[str] = Field(default_factory=list)
    drift_sections: list[DriftAlert] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class CostEntry(BaseModel):
    """Single cost log entry."""

    session: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class RepoGovernance(BaseModel):
    """Full governance data for a single repo."""

    repo_name: str
    health: GovernanceHealth = Field(default_factory=GovernanceHealth)
    drift: DriftReport = Field(default_factory=DriftReport)
    cost_entries: list[CostEntry] = Field(default_factory=list)
    content_quality: dict = Field(default_factory=dict)
