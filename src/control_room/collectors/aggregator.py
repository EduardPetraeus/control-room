from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from control_room.collectors.cost import build_cost_summary
from control_room.collectors.git_log import (
    get_commit_stats,
    get_current_branch,
    get_last_commit_date,
)
from control_room.collectors.governance import get_drift_report, get_health_score
from control_room.collectors.heartbeat import collect_fleet_status
from control_room.collectors.status_md import get_all_status_info
from control_room.collectors.task_engine import get_all_critical_paths, get_fleet_next_tasks
from control_room.config import AppConfig
from control_room.models.cost import CostSummary
from control_room.models.governance import (
    DriftAlert,
    DriftReport,
    GovernanceHealth,
    HealthCheck,
    RepoGovernance,
)
from control_room.models.heartbeat import FleetStatus
from control_room.models.project import ProjectStatus, StatusInfo
from control_room.models.queue import BlockerQueue

if TYPE_CHECKING:
    from control_room.models.activity import ActivityEvent, GitHubProjectItem
    from control_room.models.task import UnifiedTask, YamlTask

logger = logging.getLogger(__name__)


class DataCache:
    """Simple in-memory cache with TTL."""

    def __init__(self, ttl_seconds: int = 30) -> None:
        self._ttl = ttl_seconds
        self._cache: dict[str, tuple[float, object]] = {}

    def get(self, key: str) -> object | None:
        """Return cached value if within TTL, otherwise None."""
        if key in self._cache:
            timestamp, value = self._cache[key]
            if time.time() - timestamp < self._ttl:
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value: object) -> None:
        """Store a value with the current timestamp."""
        self._cache[key] = (time.time(), value)

    def clear(self) -> None:
        """Remove all cached entries."""
        self._cache.clear()


class DataAggregator:
    """Collect and cache project status data from all configured repositories."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.cache = DataCache(ttl_seconds=config.server.cache_ttl_seconds)

    def get_fleet_status(self) -> FleetStatus:
        """Get fleet status from heartbeat files."""
        cached = self.cache.get("fleet_status")
        if cached is not None:
            return cached  # type: ignore[return-value]

        repo_paths = [Path(r.path) for r in self.config.repos]
        fleet = collect_fleet_status(repo_paths)
        self.cache.set("fleet_status", fleet)
        return fleet

    def get_blocker_queue(self) -> BlockerQueue:
        """Get prioritized blocker queue."""
        from control_room.collectors.queue import collect_blocker_queue

        cached = self.cache.get("blocker_queue")
        if cached is not None:
            return cached  # type: ignore[return-value]
        queue = collect_blocker_queue(self.config.repos)
        self.cache.set("blocker_queue", queue)
        return queue

    def _collect_governance(self, repo_path: str, repo_name: str) -> RepoGovernance:
        """Collect governance health score and drift data for a repo.

        All calls are fault-tolerant: failures result in safe defaults.
        """
        path = Path(repo_path)
        health_raw = get_health_score(path)

        # Convert raw health dict to structured model
        checks = [
            HealthCheck(
                name=c.get("name", ""),
                passed=c.get("passed", False),
                points=c.get("points", 0),
            )
            for c in health_raw.get("checks", [])
        ]
        health = GovernanceHealth(
            score=health_raw.get("score", 0),
            level=health_raw.get("level", 0),
            level_label=health_raw.get("level_label", "Unknown"),
            checks=checks,
        )

        # Drift detection: compare repo's CLAUDE.md against governance template
        template_path = (
            Path.home() / "Github repos" / "ai-governance-framework" / "templates" / "CLAUDE.md"
        )
        drift_raw = get_drift_report(template_path, path)

        drift_sections = [
            DriftAlert(
                section=d.get("section", ""),
                direction=d.get("direction", ""),
                ratio=d.get("ratio", 0.0),
            )
            for d in drift_raw.get("drift_sections", [])
        ]
        drift = DriftReport(
            aligned=drift_raw.get("aligned", True),
            missing_sections=drift_raw.get("missing_sections", []),
            drift_sections=drift_sections,
            recommendations=drift_raw.get("recommendations", []),
        )

        return RepoGovernance(
            repo_name=repo_name,
            health=health,
            drift=drift,
        )

    def _determine_status_color(self, project: ProjectStatus) -> str:
        """Determine status color based on test results and activity.

        - green: tests passing + recent commits (last 30 days)
        - amber: stale (no recent commits) or no test info
        - red: failing tests or low health score
        - gray: no data at all
        """
        has_tests = project.test_count is not None
        has_commits = project.commits_30d > 0

        # Red: failing tests or health < 60%
        if has_tests and project.test_passing is not None:
            if project.test_count and project.test_passing < project.test_count:
                return "red"
        if project.health_score:
            try:
                score = int(project.health_score.replace("%", ""))
                if score < 60:
                    return "red"
            except ValueError:
                pass

        # Green: tests + recent activity
        if has_tests and has_commits:
            return "green"

        # Amber: stale or no tests
        if has_tests or has_commits:
            return "amber"

        # Gray: no data
        return "gray"

    def get_all_projects(self) -> list[ProjectStatus]:
        """Get status for all configured projects."""
        cached = self.cache.get("all_projects")
        if cached is not None:
            return cached  # type: ignore[return-value]

        status_info = get_all_status_info(self.config.repos)
        projects: list[ProjectStatus] = []

        for repo in self.config.repos:
            info = status_info.get(repo.name, StatusInfo())
            branch = get_current_branch(repo.path)
            stats = get_commit_stats(repo.path, days=30)
            last_date = get_last_commit_date(repo.path)

            project = ProjectStatus(
                name=repo.name,
                description=repo.description,
                path=repo.path,
                branch=branch,
                version=info.version,
                test_count=info.test_count,
                test_passing=info.test_passing,
                health_score=info.health_score,
                status_text=info.status_text,
                commits_30d=stats.total_commits,
                last_commit_date=last_date,
            )

            # Collect governance data (health score + drift)
            project.governance = self._collect_governance(repo.path, repo.name)

            project.status_color = self._determine_status_color(project)
            projects.append(project)

        self.cache.set("all_projects", projects)
        return projects

    def _yaml_to_unified(self, task: YamlTask) -> UnifiedTask:
        """Convert a YamlTask to a UnifiedTask."""
        from control_room.models.task import PRIORITY_ORDER, UnifiedTask

        # Map status: blocked tasks go to backlog with is_blocked flag
        status = task.status.lower()
        is_blocked = len(task.blocked_by) > 0 or status == "blocked"

        # Normalize status
        status_map = {
            "backlog": "backlog",
            "blocked": "backlog",
            "todo": "todo",
            "pending": "todo",
            "open": "todo",
            "active": "in_progress",
            "wip": "in_progress",
            "in-progress": "in_progress",
            "in_progress": "in_progress",
            "review": "review",
            "complete": "done",
            "completed": "done",
            "closed": "done",
            "done": "done",
        }
        normalized_status = status_map.get(status, "backlog")

        return UnifiedTask(
            id=task.id,
            title=task.title,
            status=normalized_status,
            priority=task.priority,
            priority_order=PRIORITY_ORDER.get(task.priority.lower(), 2),
            project=task.project,
            source="yaml",
            is_blocked=is_blocked,
            blocked_by=task.blocked_by,
            tags=task.tags,
            description=task.description,
        )

    def _github_item_to_unified(self, item: GitHubProjectItem) -> UnifiedTask:
        """Convert a GitHub project item to a UnifiedTask."""
        from control_room.models.task import PRIORITY_ORDER, UnifiedTask

        # Map GitHub project status to kanban columns
        status_map = {
            "todo": "todo",
            "in progress": "in_progress",
            "done": "done",
            "": "backlog",
        }
        status = status_map.get(item.status.lower(), "backlog")

        # Determine priority from labels
        priority = "medium"
        for label in item.labels:
            label_lower = label.lower()
            if "critical" in label_lower or "urgent" in label_lower:
                priority = "critical"
                break
            if "high" in label_lower:
                priority = "high"
                break
            if "low" in label_lower:
                priority = "low"
                break

        return UnifiedTask(
            id=f"gh-{hash(item.title) % 10000}",
            title=item.title,
            status=status,
            priority=priority,
            priority_order=PRIORITY_ORDER.get(priority, 2),
            project=item.repo or "github",
            source="github",
            url=item.url,
        )

    def get_all_tasks(self) -> list[UnifiedTask]:
        """Get all tasks from YAML files and GitHub, normalized and sorted."""
        from control_room.collectors.github import get_project_items
        from control_room.collectors.yaml_tasks import get_all_project_tasks

        cached = self.cache.get("all_tasks")
        if cached is not None:
            return cached  # type: ignore[return-value]

        # YAML tasks
        yaml_tasks = get_all_project_tasks(self.config.repos)
        unified: list[UnifiedTask] = [self._yaml_to_unified(t) for t in yaml_tasks]

        # GitHub project items
        try:
            gh_items = get_project_items(
                project_number=1,
                owner=self.config.github.username or "EduardPetraeus",
            )
            # Deduplicate by title (YAML takes precedence)
            existing_titles = {t.title.lower() for t in unified}
            for item in gh_items:
                if item.title.lower() not in existing_titles:
                    unified.append(self._github_item_to_unified(item))
                    existing_titles.add(item.title.lower())
        except Exception:
            logger.exception("Failed to fetch GitHub project items")

        # Sort by priority order (critical first)
        unified.sort(key=lambda t: t.priority_order)

        self.cache.set("all_tasks", unified)
        return unified

    def get_activity_feed(self, limit: int = 30) -> list[ActivityEvent]:
        """Get a cross-repo activity feed from git commits and GitHub events."""
        from control_room.collectors.git_log import get_recent_commits
        from control_room.collectors.github import get_repo_events_sync
        from control_room.models.activity import ActivityEvent

        cached = self.cache.get("activity_feed")
        if cached is not None:
            return cached  # type: ignore[return-value]

        events: list[ActivityEvent] = []

        # Git commits from all repos
        for repo in self.config.repos:
            try:
                commits = get_recent_commits(repo.path, limit=5)
                for commit in commits:
                    events.append(
                        ActivityEvent(
                            event_type="commit",
                            title=commit.message,
                            repo_name=repo.name,
                            date=commit.date,
                            color="green",
                        )
                    )
            except Exception:
                logger.warning("Failed to get commits for %s", repo.name)

        # GitHub events
        if self.config.github.username:
            for repo in self.config.repos:
                try:
                    gh_events = get_repo_events_sync(
                        self.config.github.username, repo.name, limit=5
                    )
                    events.extend(gh_events)
                except Exception:
                    logger.warning("Failed to get GitHub events for %s", repo.name)

        # Sort by date descending, take limit
        events.sort(key=lambda e: e.date, reverse=True)
        events = events[:limit]

        self.cache.set("activity_feed", events)
        return events

    def get_cost_summary(self) -> CostSummary:
        """Get aggregated cost data."""
        cached = self.cache.get("cost_summary")
        if cached is not None:
            return cached  # type: ignore[return-value]
        budget = getattr(self.config, "budget_limit_usd", 50.0)
        summary = build_cost_summary(self.config.repos, budget)
        self.cache.set("cost_summary", summary)
        return summary

    def get_critical_paths(self) -> dict[str, list[str]]:
        """Get critical paths for all repos."""
        cached = self.cache.get("critical_paths")
        if cached is not None:
            return cached  # type: ignore[return-value]
        paths = get_all_critical_paths(self.config.repos)
        self.cache.set("critical_paths", paths)
        return paths

    def get_next_tasks(self, agent_type: str | None = None) -> list[dict]:
        """Get next available tasks across all repos."""
        # Don't cache this — it should always be fresh for agent assignment
        return get_fleet_next_tasks(self.config.repos, agent_type)

    def get_tasks_by_column(self) -> dict[str, list[UnifiedTask]]:
        """Group tasks into kanban columns."""

        columns: dict[str, list[UnifiedTask]] = {
            "backlog": [],
            "todo": [],
            "in_progress": [],
            "review": [],
            "done": [],
        }
        for task in self.get_all_tasks():
            col = columns.get(task.status, columns["backlog"])
            col.append(task)
        return columns
