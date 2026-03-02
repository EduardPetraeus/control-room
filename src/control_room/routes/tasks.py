from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request) -> HTMLResponse:
    """Render the kanban board page."""
    templates = request.app.state.templates
    aggregator = request.app.state.aggregator
    columns = aggregator.get_tasks_by_column()
    return templates.TemplateResponse(
        "tasks.html",
        {"request": request, "columns": columns, "page": "tasks"},
    )


@router.get("/partials/kanban", response_class=HTMLResponse)
async def kanban_partial(request: Request) -> HTMLResponse:
    """Return the kanban board partial for HTMX polling."""
    templates = request.app.state.templates
    aggregator = request.app.state.aggregator
    columns = aggregator.get_tasks_by_column()
    return templates.TemplateResponse(
        "partials/kanban-board.html",
        {"request": request, "columns": columns},
    )
