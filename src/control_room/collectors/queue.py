from __future__ import annotations

import logging
from pathlib import Path

from control_room.collectors.governance import get_drift_report
from control_room.collectors.heartbeat import find_heartbeat_files, parse_heartbeat
from control_room.collectors.yaml_tasks import load_tasks_from_directory
from control_room.config import RepoConfig
from control_room.models.queue import (
    BlockerQueue,
    QueueItem,
    QueueItemPriority,
    QueueItemType,
)

logger = logging.getLogger(__name__)

GOVERNANCE_TEMPLATE = (
    Path.home() / "Github repos" / "ai-governance-framework" / "templates" / "CLAUDE.md"
)


def collect_heartbeat_blockers(repo_paths: list[Path]) -> list[QueueItem]:
    """Collect blockers from agent heartbeat files."""
    items: list[QueueItem] = []
    heartbeat_files = find_heartbeat_files(repo_paths)
    for hb_file in heartbeat_files:
        hb = parse_heartbeat(hb_file)
        if hb is not None and hb.blocker:
            items.append(
                QueueItem(
                    id=f"hb-{hb.session_id}",
                    item_type=QueueItemType.AGENT_BLOCKED,
                    priority=QueueItemPriority.CRITICAL,
                    title=f"Agent blocked in {hb.repo}",
                    description=hb.blocker,
                    source_repo=hb.repo,
                    session_id=hb.session_id,
                )
            )
    return items


def collect_blocked_tasks(repos: list[RepoConfig]) -> list[QueueItem]:
    """Collect blocked YAML tasks from all repos."""
    items: list[QueueItem] = []
    for repo in repos:
        try:
            repo_path = Path(repo.path)
            task_dir = repo_path / repo.task_dir
            if not task_dir.exists():
                # Try backlog/ as fallback
                task_dir = repo_path / "backlog"
            if not task_dir.exists():
                continue
            tasks = load_tasks_from_directory(str(task_dir), repo.name)
            for task in tasks:
                if task.status == "blocked" or task.blocked_by:
                    items.append(
                        QueueItem(
                            id=f"task-{repo.name}-{task.id}",
                            item_type=QueueItemType.TASK_BLOCKED,
                            priority=QueueItemPriority.MEDIUM,
                            title=f"Blocked: {task.title}",
                            description=(
                                f"Blocked by: {', '.join(task.blocked_by)}"
                                if task.blocked_by
                                else "Status: blocked"
                            ),
                            source_repo=repo.name,
                        )
                    )
        except Exception as e:
            logger.warning("Failed to collect blocked tasks from %s: %s", repo.name, e)
    return items


def collect_drift_alerts(repos: list[RepoConfig]) -> list[QueueItem]:
    """Collect governance drift alerts from all repos."""
    items: list[QueueItem] = []
    if not GOVERNANCE_TEMPLATE.exists():
        logger.warning("Governance template not found at %s", GOVERNANCE_TEMPLATE)
        return items

    for repo in repos:
        try:
            repo_path = Path(repo.path)
            report = get_drift_report(GOVERNANCE_TEMPLATE, repo_path)
            if not report.get("aligned", True):
                missing = report.get("missing_sections", [])
                drifted = report.get("drift_sections", [])
                desc_parts: list[str] = []
                if missing:
                    desc_parts.append(f"Missing sections: {', '.join(missing)}")
                if drifted:
                    drift_names = [
                        d.get("section", d) if isinstance(d, dict) else str(d) for d in drifted
                    ]
                    desc_parts.append(f"Drifted sections: {', '.join(drift_names)}")
                items.append(
                    QueueItem(
                        id=f"drift-{repo.name}",
                        item_type=QueueItemType.GOVERNANCE_DRIFT,
                        priority=QueueItemPriority.LOW,
                        title=f"Governance drift in {repo.name}",
                        description=(
                            "; ".join(desc_parts)
                            if desc_parts
                            else "CLAUDE.md not aligned with template"
                        ),
                        source_repo=repo.name,
                    )
                )
        except Exception as e:
            logger.warning("Drift check failed for %s: %s", repo.name, e)
    return items


def collect_blocker_queue(repos: list[RepoConfig]) -> BlockerQueue:
    """Aggregate all blocker sources into a prioritized queue."""
    repo_paths = [Path(r.path) for r in repos]

    all_items: list[QueueItem] = []
    all_items.extend(collect_heartbeat_blockers(repo_paths))
    all_items.extend(collect_blocked_tasks(repos))
    all_items.extend(collect_drift_alerts(repos))

    # Sort by priority (critical first)
    priority_order = {
        QueueItemPriority.CRITICAL: 0,
        QueueItemPriority.HIGH: 1,
        QueueItemPriority.MEDIUM: 2,
        QueueItemPriority.LOW: 3,
    }
    all_items.sort(key=lambda x: priority_order.get(x.priority, 99))

    return BlockerQueue(
        items=all_items,
        total_critical=sum(1 for i in all_items if i.priority == QueueItemPriority.CRITICAL),
        total_high=sum(1 for i in all_items if i.priority == QueueItemPriority.HIGH),
        total_medium=sum(1 for i in all_items if i.priority == QueueItemPriority.MEDIUM),
        total_low=sum(1 for i in all_items if i.priority == QueueItemPriority.LOW),
    )
