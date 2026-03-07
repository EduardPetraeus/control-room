"""CLI entry point for the master agent daemon.

Usage:
    python -m control_room.master start     # Start the daemon in foreground
    python -m control_room.master stop      # Stop a running daemon
    python -m control_room.master status    # Show daemon status
    python -m control_room.master logs      # Tail daemon logs
"""

from __future__ import annotations

import json
import os
import signal
import sys

import click

from control_room.master.daemon import LOG_DIR, PID_FILE, STATE_FILE


@click.group()
def cli() -> None:
    """Master Agent Daemon — autonomous task execution for Claude Code."""


@cli.command()
@click.option("--tick", default=60, help="Tick interval in seconds")
@click.option("--max-concurrent", default=2, help="Max concurrent sessions")
@click.option("--timeout", default=1800, help="Session timeout in seconds")
@click.option("--no-review", is_flag=True, help="Skip review pipeline after completion")
@click.option("--no-notify", is_flag=True, help="Disable macOS notifications")
@click.option("--no-handover", is_flag=True, help="Disable auto-handover")
def start(
    tick: int,
    max_concurrent: int,
    timeout: int,
    no_review: bool,
    no_notify: bool,
    no_handover: bool,
) -> None:
    """Start the master agent daemon."""
    import logging

    from control_room.master.daemon import MasterDaemon, load_daemon_config

    # Load config from file, then override with CLI args
    config = load_daemon_config()
    config.tick_interval = tick
    config.max_concurrent = max_concurrent
    config.session_timeout = timeout
    if no_review:
        config.review_on_completion = False
    if no_notify:
        config.notify_on_completion = False
    if no_handover:
        config.auto_handover = False

    # Setup logging
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_DIR / "daemon.log"),
        ],
    )

    # Check if already running
    if _is_daemon_running():
        click.echo("Master agent daemon is already running. Use 'stop' first.")
        sys.exit(1)

    click.echo(f"Starting Master Agent Daemon (tick={tick}s, max={max_concurrent})")
    daemon = MasterDaemon(config)
    daemon.run()


@cli.command()
def stop() -> None:
    """Stop the running master agent daemon."""
    if not PID_FILE.exists():
        click.echo("No PID file found — daemon may not be running.")
        return

    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        click.echo(f"Sent SIGTERM to daemon (PID {pid})")
    except (ValueError, ProcessLookupError, PermissionError) as exc:
        click.echo(f"Failed to stop daemon: {exc}")
        PID_FILE.unlink(missing_ok=True)


@cli.command()
def status() -> None:
    """Show current daemon status."""
    if not _is_daemon_running():
        click.echo("Daemon is NOT running.")
        if STATE_FILE.exists():
            _print_state()
        return

    click.echo("Daemon is RUNNING.")
    _print_state()


@cli.command()
@click.option("-n", "--lines", default=50, help="Number of lines to show")
def logs(lines: int) -> None:
    """Show recent daemon logs."""
    log_file = LOG_DIR / "daemon.log"
    if not log_file.exists():
        click.echo("No log file found.")
        return

    content = log_file.read_text(encoding="utf-8")
    log_lines = content.strip().split("\n")
    for line in log_lines[-lines:]:
        click.echo(line)


def _is_daemon_running() -> bool:
    """Check if the daemon process is alive."""
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False


def _print_state() -> None:
    """Print the last saved daemon state."""
    if not STATE_FILE.exists():
        click.echo("No state file found.")
        return

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        click.echo(f"  Tick count: {data.get('tick_count', 0)}")
        click.echo(f"  Active sessions: {len(data.get('active_sessions', {}))}")
        click.echo(f"  Completed: {len(data.get('completed_sessions', []))}")
        click.echo(f"  Failed: {len(data.get('failed_sessions', []))}")
        click.echo(f"  Last update: {data.get('timestamp', 'unknown')}")

        active = data.get("active_sessions", {})
        if active:
            click.echo("  --- Active Sessions ---")
            for sid, info in active.items():
                click.echo(f"    {sid}: {info.get('title', '')} ({info.get('repo', '')})")
    except (json.JSONDecodeError, OSError) as exc:
        click.echo(f"Failed to read state: {exc}")


if __name__ == "__main__":
    cli()
