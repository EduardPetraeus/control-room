from __future__ import annotations

from pydantic import BaseModel


class VelocityMetrics(BaseModel):
    """Aggregated velocity and productivity metrics."""

    total_commits_30d: int = 0
    daily_avg_commits: float = 0.0
    weekly_avg_commits: float = 0.0
    total_tests: int = 0
    total_tests_passing: int = 0
    tasks_total: int = 0
    tasks_done: int = 0
    tasks_in_progress: int = 0
    tasks_backlog: int = 0
    completion_rate: float = 0.0
    active_repos: int = 0
    total_repos: int = 0
