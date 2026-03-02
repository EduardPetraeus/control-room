from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/costs", response_class=HTMLResponse)
async def costs_page(request: Request) -> HTMLResponse:
    """Cost tracking dashboard."""
    templates = request.app.state.templates
    aggregator = request.app.state.aggregator
    costs = aggregator.get_cost_summary()
    return templates.TemplateResponse(
        "costs.html",
        {"request": request, "costs": costs, "page": "costs"},
    )


@router.get("/partials/cost-overview", response_class=HTMLResponse)
async def cost_overview_partial(request: Request) -> HTMLResponse:
    """HTMX partial for cost overview."""
    templates = request.app.state.templates
    aggregator = request.app.state.aggregator
    costs = aggregator.get_cost_summary()
    return templates.TemplateResponse(
        "partials/cost-overview.html",
        {"request": request, "costs": costs},
    )
