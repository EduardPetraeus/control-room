from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Render the main dashboard page."""
    templates = request.app.state.templates
    aggregator = request.app.state.aggregator
    projects = aggregator.get_all_projects()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"projects": projects, "page": "dashboard"},
    )


@router.get("/partials/project-cards", response_class=HTMLResponse)
async def project_cards_partial(request: Request) -> HTMLResponse:
    """Return the project cards partial for HTMX polling."""
    templates = request.app.state.templates
    aggregator = request.app.state.aggregator
    projects = aggregator.get_all_projects()
    return templates.TemplateResponse(
        request,
        "partials/project-cards.html",
        {"projects": projects},
    )


@router.get("/partials/activity-feed", response_class=HTMLResponse)
async def activity_feed_partial(request: Request) -> HTMLResponse:
    """Return the activity feed partial for HTMX polling."""
    templates = request.app.state.templates
    aggregator = request.app.state.aggregator
    events = aggregator.get_activity_feed()
    return templates.TemplateResponse(
        request,
        "partials/activity-feed.html",
        {"events": events},
    )
