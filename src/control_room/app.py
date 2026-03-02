from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from control_room.config import get_config

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — setup and teardown."""
    config = get_config()
    app.state.config = config

    from control_room.collectors.aggregator import DataAggregator

    aggregator = DataAggregator(config)
    app.state.aggregator = aggregator

    logger.info("Control Room starting — %d repos configured", len(config.repos))
    yield
    logger.info("Control Room shutting down")


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title="Control Room",
        description="Solo dev dashboard for repos, tasks, and activity",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Static files
    STATIC_DIR.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Templates
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.state.templates = templates

    # Routes
    from control_room.routes.costs import router as costs_router
    from control_room.routes.dashboard import router as dashboard_router
    from control_room.routes.fleet import router as fleet_router
    from control_room.routes.metrics import router as metrics_router
    from control_room.routes.orchestration import router as orchestration_router
    from control_room.routes.projects import router as projects_router
    from control_room.routes.queue import router as queue_router
    from control_room.routes.tasks import router as tasks_router

    app.include_router(costs_router)
    app.include_router(dashboard_router)
    app.include_router(fleet_router)
    app.include_router(metrics_router)
    app.include_router(orchestration_router)
    app.include_router(projects_router)
    app.include_router(queue_router)
    app.include_router(tasks_router)

    return app
