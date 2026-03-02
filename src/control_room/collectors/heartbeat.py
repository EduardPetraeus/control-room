from __future__ import annotations

import json
import logging
from pathlib import Path

from control_room.models.heartbeat import FleetStatus, SessionHeartbeat, SessionStatus

logger = logging.getLogger(__name__)

HEARTBEAT_FILENAME = "session-heartbeat.json"


def find_heartbeat_files(repo_paths: list[Path]) -> list[Path]:
    """Scan repo directories for heartbeat files."""
    found = []
    for repo_path in repo_paths:
        hb_path = repo_path / HEARTBEAT_FILENAME
        if hb_path.exists():
            found.append(hb_path)
    return found


def parse_heartbeat(file_path: Path) -> SessionHeartbeat | None:
    """Parse a single heartbeat JSON file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        data = json.loads(content)
        return SessionHeartbeat(**data)
    except Exception as e:
        logger.warning("Failed to parse heartbeat %s: %s", file_path, e)
        return None


def collect_fleet_status(repo_paths: list[Path]) -> FleetStatus:
    """Collect heartbeats from all repos and build fleet status."""
    heartbeat_files = find_heartbeat_files(repo_paths)
    sessions = []

    for hb_file in heartbeat_files:
        heartbeat = parse_heartbeat(hb_file)
        if heartbeat is not None:
            sessions.append(heartbeat)

    # Calculate aggregates
    active = sum(1 for s in sessions if s.status == SessionStatus.ACTIVE)
    blocked = sum(1 for s in sessions if s.status == SessionStatus.BLOCKED)
    idle = sum(1 for s in sessions if s.status == SessionStatus.IDLE)
    completed = sum(1 for s in sessions if s.status == SessionStatus.COMPLETED)
    failed = sum(1 for s in sessions if s.status == SessionStatus.FAILED)

    active_sessions = [s for s in sessions if s.status == SessionStatus.ACTIVE]
    fleet_progress = (
        sum(s.progress for s in active_sessions) / len(active_sessions) if active_sessions else 0.0
    )
    fleet_cost = sum(s.cost_usd for s in sessions)
    fleet_tokens = sum(s.tokens_used for s in sessions)

    return FleetStatus(
        sessions=sessions,
        total_active=active,
        total_blocked=blocked,
        total_idle=idle,
        total_completed=completed,
        total_failed=failed,
        fleet_progress=fleet_progress,
        fleet_cost_usd=fleet_cost,
        fleet_tokens=fleet_tokens,
    )
