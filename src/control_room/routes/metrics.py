from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from control_room.models.metrics import VelocityMetrics

router = APIRouter()


@router.get("/metrics", response_class=HTMLResponse)
async def metrics_page(request: Request) -> HTMLResponse:
    """Render the velocity metrics dashboard page."""
    templates = request.app.state.templates
    aggregator = request.app.state.aggregator

    projects = aggregator.get_all_projects()
    tasks = aggregator.get_all_tasks()

    total_commits = sum(p.commits_30d for p in projects)
    total_tests = sum(p.test_count or 0 for p in projects)
    total_passing = sum(p.test_passing or 0 for p in projects)
    active = sum(1 for p in projects if p.commits_30d > 0)

    done_count = sum(1 for t in tasks if t.status == "done")
    in_progress_count = sum(1 for t in tasks if t.status == "in_progress")
    backlog_count = sum(1 for t in tasks if t.status == "backlog")

    metrics = VelocityMetrics(
        total_commits_30d=total_commits,
        daily_avg_commits=round(total_commits / 30, 1),
        weekly_avg_commits=round(total_commits / 4.3, 1),
        total_tests=total_tests,
        total_tests_passing=total_passing,
        tasks_total=len(tasks),
        tasks_done=done_count,
        tasks_in_progress=in_progress_count,
        tasks_backlog=backlog_count,
        completion_rate=round(done_count / len(tasks) * 100, 1) if tasks else 0.0,
        active_repos=active,
        total_repos=len(projects),
    )

    return templates.TemplateResponse(
        "metrics.html",
        {"request": request, "metrics": metrics, "projects": projects, "page": "metrics"},
    )
