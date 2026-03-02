from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/fleet", response_class=HTMLResponse)
async def fleet_page(request: Request) -> HTMLResponse:
    """Fleet dashboard showing all active Claude Code sessions."""
    templates = request.app.state.templates
    aggregator = request.app.state.aggregator
    fleet_status = aggregator.get_fleet_status()
    return templates.TemplateResponse(
        "fleet.html",
        {"request": request, "fleet": fleet_status, "page": "fleet"},
    )


@router.get("/partials/fleet-grid", response_class=HTMLResponse)
async def fleet_grid_partial(request: Request) -> HTMLResponse:
    """HTMX partial for fleet session grid."""
    templates = request.app.state.templates
    aggregator = request.app.state.aggregator
    fleet_status = aggregator.get_fleet_status()
    return templates.TemplateResponse(
        "partials/fleet-grid.html",
        {"request": request, "fleet": fleet_status},
    )
