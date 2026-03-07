from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/queue", response_class=HTMLResponse)
async def queue_page(request: Request) -> HTMLResponse:
    """Blocker queue showing everything needing human attention."""
    templates = request.app.state.templates
    aggregator = request.app.state.aggregator
    queue = aggregator.get_blocker_queue()
    return templates.TemplateResponse(
        request,
        "queue.html",
        {"queue": queue, "page": "queue"},
    )


@router.get("/partials/queue-list", response_class=HTMLResponse)
async def queue_list_partial(request: Request) -> HTMLResponse:
    """HTMX partial for queue list."""
    templates = request.app.state.templates
    aggregator = request.app.state.aggregator
    queue = aggregator.get_blocker_queue()
    return templates.TemplateResponse(
        request,
        "partials/queue-list.html",
        {"queue": queue},
    )
