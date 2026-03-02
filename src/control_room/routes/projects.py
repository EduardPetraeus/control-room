from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/projects", response_class=HTMLResponse)
async def projects_page(request: Request) -> HTMLResponse:
    """Render the detailed projects list."""
    templates = request.app.state.templates
    aggregator = request.app.state.aggregator
    projects = aggregator.get_all_projects()
    return templates.TemplateResponse(
        "projects.html",
        {"request": request, "projects": projects, "page": "projects"},
    )
