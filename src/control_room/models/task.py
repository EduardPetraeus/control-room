from __future__ import annotations

from pydantic import BaseModel, Field


class YamlTask(BaseModel):
    """Represents a single task loaded from a YAML task file."""

    id: str
    title: str
    status: str = "backlog"
    priority: str = "medium"
    project: str = ""
    blocked_by: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    description: str = ""


PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class UnifiedTask(BaseModel):
    """Normalized task from YAML or GitHub."""

    id: str
    title: str
    status: str = "backlog"  # backlog, todo, in_progress, review, done
    priority: str = "medium"
    priority_order: int = 2
    project: str = ""
    source: str = "yaml"  # yaml or github
    is_blocked: bool = False
    blocked_by: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    url: str = ""
