"""Master Agent Daemon — tick-loop that polls tasks, manages sessions, triggers reviews.

Rule-based decision engine. No LLM calls — pure Python if/else logic.
Runs as a persistent service via launchd.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from control_room.master.handover import needs_handover, prepare_handover
from control_room.master.launcher import (
    SessionInfo,
    is_session_alive,
    is_session_timed_out,
    launch_session,
    stop_session,
    write_heartbeat,
)
from control_room.master.notifier import (
    notify_completion,
    notify_failure,
    notify_review_complete,
)
from control_room.master.reviewer import run_review_pipeline, should_review
from control_room.master.task_parser import TaskConfig, fetch_ready_tasks

logger = logging.getLogger(__name__)

DEFAULT_TICK_INTERVAL = 60  # seconds
DEFAULT_MAX_CONCURRENT = 2
DEFAULT_SESSION_TIMEOUT = 1800  # 30 minutes
STATE_FILE = Path.home() / ".claude" / "master-agent-state.json"
PID_FILE = Path.home() / ".claude" / "master-agent.pid"
LOG_DIR = Path.home() / "build-logs" / "master-agent"


@dataclass
class DaemonConfig:
    """Configuration for the master agent daemon."""

    tick_interval: int = DEFAULT_TICK_INTERVAL
    max_concurrent: int = DEFAULT_MAX_CONCURRENT
    session_timeout: int = DEFAULT_SESSION_TIMEOUT
    repos_base: Path = field(default_factory=lambda: Path.home() / "Github repos")
    project_number: int = 1
    project_owner: str = "EduardPetraeus"
    review_on_completion: bool = True
    notify_on_completion: bool = True
    auto_handover: bool = True


@dataclass
class DaemonState:
    """Runtime state of the daemon."""

    active_sessions: dict[str, SessionInfo] = field(default_factory=dict)
    completed_sessions: list[str] = field(default_factory=list)
    failed_sessions: list[str] = field(default_factory=list)
    tick_count: int = 0
    started_at: float = field(default_factory=time.time)
    running: bool = True


class MasterDaemon:
    """The master agent daemon — polls tasks, launches sessions, manages lifecycle."""

    def __init__(self, config: DaemonConfig | None = None) -> None:
        self.config = config or DaemonConfig()
        self.state = DaemonState()
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum: int, frame: object) -> None:
        """Handle shutdown signal."""
        logger.info("Received signal %d — shutting down gracefully", signum)
        self.state.running = False

    def run(self) -> None:
        """Main daemon loop."""
        logger.info(
            "Master Agent Daemon starting (tick=%ds, max_concurrent=%d)",
            self.config.tick_interval,
            self.config.max_concurrent,
        )

        self._write_pid()
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        try:
            while self.state.running:
                self._tick()
                self.state.tick_count += 1

                if self.state.running:
                    time.sleep(self.config.tick_interval)
        finally:
            self._shutdown()

    def _tick(self) -> None:
        """Single tick of the daemon loop.

        Decision tree (rule-based, no LLM):
        1. Check active sessions — handle completions, timeouts, failures
        2. Check fleet capacity — how many slots available?
        3. Poll for ready tasks — fetch from GitHub Projects
        4. Launch sessions — fill available slots with ready tasks
        """
        logger.debug("Tick %d — checking fleet state", self.state.tick_count)

        # Step 1: Check active sessions
        self._check_sessions()

        # Step 2: Calculate available capacity
        active_count = len(self.state.active_sessions)
        available_slots = self.config.max_concurrent - active_count

        if available_slots <= 0:
            logger.debug(
                "No available slots (%d/%d active)", active_count, self.config.max_concurrent
            )
            return

        # Step 3: Poll for ready tasks
        ready_tasks = fetch_ready_tasks(
            project_number=self.config.project_number,
            owner=self.config.project_owner,
        )

        if not ready_tasks:
            logger.debug("No ready tasks found")
            return

        # Step 4: Launch sessions for ready tasks
        launched = 0
        for task in ready_tasks:
            if launched >= available_slots:
                break

            # Skip tasks that are already running
            if self._is_task_running(task):
                continue

            session = launch_session(
                task_config=task,
                repos_base=self.config.repos_base,
                timeout_seconds=self.config.session_timeout,
            )

            if session is not None:
                self.state.active_sessions[session.session_id] = session
                launched += 1
                logger.info(
                    "Launched session %s for '%s' (%d/%d slots used)",
                    session.session_id,
                    task.title,
                    active_count + launched,
                    self.config.max_concurrent,
                )
                self._update_issue_status(task, "In Progress")

        self._save_state()

    def _check_sessions(self) -> None:
        """Check all active sessions for completion, timeout, or failure."""
        finished_ids: list[str] = []

        for session_id, session in self.state.active_sessions.items():
            if not is_session_alive(session):
                # Session process ended
                self._handle_session_completed(session)
                finished_ids.append(session_id)
            elif is_session_timed_out(session):
                # Session exceeded timeout
                self._handle_session_timeout(session)
                finished_ids.append(session_id)

        for session_id in finished_ids:
            del self.state.active_sessions[session_id]

    def _handle_session_completed(self, session: SessionInfo) -> None:
        """Handle a session that completed (process exited)."""
        logger.info("Session %s completed", session.session_id)
        self.state.completed_sessions.append(session.session_id)

        # Check if handover is needed
        if self.config.auto_handover and needs_handover(session):
            result = prepare_handover(session)
            if result is not None:
                new_task, _ = result
                logger.info(
                    "Preparing handover for session %s → new task",
                    session.session_id,
                )
                # Launch continuation session immediately if capacity allows
                if len(self.state.active_sessions) < self.config.max_concurrent:
                    new_session = launch_session(
                        task_config=new_task,
                        repos_base=self.config.repos_base,
                        timeout_seconds=self.config.session_timeout,
                    )
                    if new_session:
                        self.state.active_sessions[new_session.session_id] = new_session
                        return  # Skip review until continuation completes

        # Trigger review if applicable
        if self.config.review_on_completion and should_review(session):
            logger.info("Running review pipeline for %s", session.session_id)
            review_results = run_review_pipeline(session)
            all_passed = all(review_results.values())

            if self.config.notify_on_completion:
                notify_review_complete(session.task_config.repo, all_passed)

            self._update_issue_status(session.task_config, "Review")
        else:
            self._update_issue_status(session.task_config, "Review")

        if self.config.notify_on_completion:
            notify_completion(
                session.session_id,
                session.task_config.title,
                session.task_config.repo,
            )

    def _handle_session_timeout(self, session: SessionInfo) -> None:
        """Handle a session that exceeded its timeout."""
        logger.warning("Session %s timed out — stopping", session.session_id)
        stop_session(session)

        write_heartbeat(
            session.repo_path,
            session.session_id,
            session.task_config,
            status="failed",
        )

        self.state.failed_sessions.append(session.session_id)

        if self.config.notify_on_completion:
            notify_failure(
                session.session_id,
                session.task_config.title,
                "Session timed out",
            )

    def _is_task_running(self, task: TaskConfig) -> bool:
        """Check if a task is already being worked on by an active session."""
        for session in self.state.active_sessions.values():
            if (
                session.task_config.issue_number == task.issue_number
                and session.task_config.repo == task.repo
            ):
                return True
        return False

    def _update_issue_status(self, task: TaskConfig, new_status: str) -> None:
        """Update the GitHub Issue status on the project board."""
        if not task.issue_url:
            return

        try:
            # Use gh to update the project item status
            # First, find the item ID for this issue
            result = subprocess.run(
                [
                    "gh",
                    "project",
                    "item-list",
                    str(self.config.project_number),
                    "--owner",
                    self.config.project_owner,
                    "--format",
                    "json",
                    "--limit",
                    "100",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode != 0:
                logger.warning("Failed to list project items for status update")
                return

            data = json.loads(result.stdout)
            for item in data.get("items", []):
                content = item.get("content", {})
                if isinstance(content, dict) and content.get("url") == task.issue_url:
                    item_id = item.get("id", "")
                    if item_id:
                        self._set_project_item_status(item_id, new_status)
                    break

        except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to update issue status: %s", exc)

    def _set_project_item_status(self, item_id: str, status: str) -> None:
        """Set the status field on a project item."""

        try:
            # Get the status field ID
            result = subprocess.run(
                [
                    "gh",
                    "project",
                    "field-list",
                    str(self.config.project_number),
                    "--owner",
                    self.config.project_owner,
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode != 0:
                return

            fields = json.loads(result.stdout)
            status_field_id = ""
            status_option_id = ""

            for f in fields.get("fields", []):
                if f.get("name", "").lower() == "status":
                    status_field_id = f.get("id", "")
                    for opt in f.get("options", []):
                        if opt.get("name", "").lower() == status.lower():
                            status_option_id = opt.get("id", "")
                            break
                    break

            if not status_field_id or not status_option_id:
                logger.debug("Could not find status field/option for '%s'", status)
                return

            # Get project ID
            proj_result = subprocess.run(
                [
                    "gh",
                    "project",
                    "list",
                    "--owner",
                    self.config.project_owner,
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if proj_result.returncode != 0:
                return

            projects = json.loads(proj_result.stdout)
            project_id = ""
            for p in projects.get("projects", []):
                if p.get("number") == self.config.project_number:
                    project_id = p.get("id", "")
                    break

            if not project_id:
                return

            subprocess.run(
                [
                    "gh",
                    "project",
                    "item-edit",
                    "--project-id",
                    project_id,
                    "--id",
                    item_id,
                    "--field-id",
                    status_field_id,
                    "--single-select-option-id",
                    status_option_id,
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

        except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to set project item status: %s", exc)

    def _save_state(self) -> None:
        """Persist daemon state to disk."""
        state_data = {
            "tick_count": self.state.tick_count,
            "started_at": self.state.started_at,
            "active_sessions": {
                sid: {
                    "session_id": s.session_id,
                    "pid": s.pid,
                    "repo": s.task_config.repo,
                    "title": s.task_config.title,
                    "issue_number": s.task_config.issue_number,
                    "started_at": s.started_at,
                }
                for sid, s in self.state.active_sessions.items()
            },
            "completed_sessions": self.state.completed_sessions[-50:],
            "failed_sessions": self.state.failed_sessions[-50:],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATE_FILE.write_text(json.dumps(state_data, indent=2))
        except OSError as exc:
            logger.warning("Failed to save state: %s", exc)

    def _write_pid(self) -> None:
        """Write daemon PID to file."""
        try:
            PID_FILE.parent.mkdir(parents=True, exist_ok=True)
            PID_FILE.write_text(str(os.getpid()))
        except OSError as exc:
            logger.warning("Failed to write PID file: %s", exc)

    def _shutdown(self) -> None:
        """Graceful shutdown — stop all active sessions."""
        logger.info("Shutting down — stopping %d active sessions", len(self.state.active_sessions))

        for session_id, session in self.state.active_sessions.items():
            logger.info("Stopping session %s", session_id)
            stop_session(session)
            write_heartbeat(
                session.repo_path,
                session.session_id,
                session.task_config,
                status="idle",
            )

        self._save_state()

        # Clean up PID file
        try:
            PID_FILE.unlink(missing_ok=True)
        except OSError:
            pass

        logger.info("Master Agent Daemon stopped (ran %d ticks)", self.state.tick_count)

    def get_status(self) -> dict:
        """Get current daemon status as a dict."""
        uptime = time.time() - self.state.started_at
        return {
            "running": self.state.running,
            "uptime_seconds": int(uptime),
            "tick_count": self.state.tick_count,
            "active_sessions": len(self.state.active_sessions),
            "completed_sessions": len(self.state.completed_sessions),
            "failed_sessions": len(self.state.failed_sessions),
            "max_concurrent": self.config.max_concurrent,
            "sessions": {
                sid: {
                    "repo": s.task_config.repo,
                    "title": s.task_config.title,
                    "pid": s.pid,
                    "elapsed": int(time.time() - s.started_at),
                }
                for sid, s in self.state.active_sessions.items()
            },
        }


def load_daemon_config(config_path: Path | None = None) -> DaemonConfig:
    """Load daemon configuration from the control-room config.yaml."""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"

    if not config_path.exists():
        return DaemonConfig()

    try:
        import yaml

        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}

        master_config = raw.get("master_agent", {})
        if not master_config:
            return DaemonConfig()

        return DaemonConfig(
            tick_interval=master_config.get("tick_interval", DEFAULT_TICK_INTERVAL),
            max_concurrent=master_config.get("max_concurrent", DEFAULT_MAX_CONCURRENT),
            session_timeout=master_config.get("session_timeout", DEFAULT_SESSION_TIMEOUT),
            repos_base=Path(os.path.expanduser(master_config.get("repos_base", "~/Github repos"))),
            project_number=master_config.get("project_number", 1),
            project_owner=master_config.get("project_owner", "EduardPetraeus"),
            review_on_completion=master_config.get("review_on_completion", True),
            notify_on_completion=master_config.get("notify_on_completion", True),
            auto_handover=master_config.get("auto_handover", True),
        )

    except (OSError, ImportError) as exc:
        logger.warning("Failed to load daemon config: %s", exc)
        return DaemonConfig()
