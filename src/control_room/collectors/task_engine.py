"""Collector wrapping ai-pm's TaskEngine for fleet-wide task intelligence.

Provides critical-path analysis, pick-next assignment, dependency resolution,
and cycle detection across all configured repositories. This does NOT replace
yaml_tasks.py — it adds higher-level capabilities on top of ai-pm.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from control_room.config import RepoConfig

logger = logging.getLogger(__name__)


def _load_engine(repo_path: Path, task_dir: str = "tasks"):
    """Load a TaskEngine for a single repo. Returns None on failure."""
    try:
        from ai_pm.engine import TaskEngine
        from ai_pm.parser import load_all_tasks

        # Try configured task_dir first, then backlog/
        td = repo_path / task_dir
        if not td.exists():
            td = repo_path / "backlog"
        if not td.exists():
            return None

        tasks = load_all_tasks(td)
        if not tasks:
            return None

        return TaskEngine(tasks)
    except Exception as e:
        logger.warning("Failed to load TaskEngine for %s: %s", repo_path, e)
        return None


def get_critical_path(repo: RepoConfig) -> list[str]:
    """Get critical path (longest dependency chain) for a repo."""
    engine = _load_engine(Path(repo.path), repo.task_dir)
    if engine is None:
        return []
    try:
        return engine.critical_path()
    except Exception as e:
        logger.warning("Critical path failed for %s: %s", repo.name, e)
        return []


def get_next_task(repo: RepoConfig, agent_type: str | None = None) -> dict[str, Any] | None:
    """Get the highest-priority ready task for a repo."""
    engine = _load_engine(Path(repo.path), repo.task_dir)
    if engine is None:
        return None
    try:
        return engine.pick_next(agent_type=agent_type)
    except Exception as e:
        logger.warning("Pick-next failed for %s: %s", repo.name, e)
        return None


def get_dependency_order(repo: RepoConfig) -> list[str]:
    """Get topological sort of tasks for a repo."""
    engine = _load_engine(Path(repo.path), repo.task_dir)
    if engine is None:
        return []
    try:
        return engine.resolve_dependencies()
    except Exception as e:
        logger.warning("Dependency resolution failed for %s: %s", repo.name, e)
        return []


def detect_cycles(repo: RepoConfig) -> list[list[str]]:
    """Detect circular dependencies in a repo's tasks."""
    engine = _load_engine(Path(repo.path), repo.task_dir)
    if engine is None:
        return []
    try:
        return engine.detect_circular_dependencies()
    except Exception as e:
        logger.warning("Cycle detection failed for %s: %s", repo.name, e)
        return []


def get_all_critical_paths(repos: list[RepoConfig]) -> dict[str, list[str]]:
    """Get critical paths for all repos. Returns dict of repo_name -> critical_path."""
    result = {}
    for repo in repos:
        cp = get_critical_path(repo)
        if cp:
            result[repo.name] = cp
    return result


def get_fleet_next_tasks(
    repos: list[RepoConfig], agent_type: str | None = None
) -> list[dict[str, Any]]:
    """Get next available task across all repos."""
    tasks = []
    for repo in repos:
        task = get_next_task(repo, agent_type)
        if task is not None:
            task["_repo"] = repo.name
            tasks.append(task)
    return tasks
