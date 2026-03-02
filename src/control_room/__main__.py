from __future__ import annotations

import click
import uvicorn

from control_room.config import get_config


@click.command()
@click.option("--host", default=None, help="Host to bind to")
@click.option("--port", default=None, type=int, help="Port to bind to")
@click.option("--reload/--no-reload", default=None, help="Enable auto-reload")
def main(host: str | None, port: int | None, reload: bool | None) -> None:
    """Start the Control Room dashboard."""
    config = get_config()
    uvicorn.run(
        "control_room.app:create_app",
        factory=True,
        host=host or config.server.host,
        port=port or config.server.port,
        reload=reload if reload is not None else config.server.reload,
    )


if __name__ == "__main__":
    main()
