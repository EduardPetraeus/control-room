from __future__ import annotations

from pydantic import BaseModel

from control_room.models.governance import RepoGovernance


class StatusInfo(BaseModel):
    """Parsed status information extracted from STATUS.md, README.md, or DOGFOOD.md."""

    version: str | None = None
    test_count: int | None = None
    test_passing: int | None = None
    health_score: str | None = None
    current_branch: str | None = None
    status_text: str = "unknown"


class ProjectStatus(BaseModel):
    """Aggregated project status combining git, status files, and config data."""

    name: str
    description: str = ""
    path: str = ""
    branch: str = "unknown"
    version: str | None = None
    test_count: int | None = None
    test_passing: int | None = None
    health_score: str | None = None
    status_text: str = "unknown"
    status_color: str = "gray"  # green, amber, red, gray
    commits_30d: int = 0
    last_commit_date: str | None = None
    governance: RepoGovernance | None = None
