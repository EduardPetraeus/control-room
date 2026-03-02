from __future__ import annotations

from fastapi.testclient import TestClient

from control_room.app import create_app


def test_costs_page_returns_200() -> None:
    """Costs page should return 200 with page title."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/costs")
        assert response.status_code == 200
        assert "Cost Tracking" in response.text


def test_cost_overview_partial_returns_200() -> None:
    """Cost overview HTMX partial should return 200."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/partials/cost-overview")
        assert response.status_code == 200


def test_costs_page_shows_empty_state() -> None:
    """Costs page with no data should show empty state message."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/costs")
        assert response.status_code == 200
        assert "No cost data available" in response.text


def test_costs_page_contains_stats_bar() -> None:
    """Costs page should contain the stats bar with budget info."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/costs")
        assert response.status_code == 200
        assert "Total Cost" in response.text
        assert "Total Tokens" in response.text
        assert "Budget Used" in response.text
        assert "Budget Limit" in response.text


def test_costs_page_has_htmx_polling() -> None:
    """Costs page should have HTMX auto-refresh configured."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/costs")
        assert response.status_code == 200
        assert 'hx-get="/partials/cost-overview"' in response.text
        assert "every 30s" in response.text


def test_costs_page_has_sidebar_link() -> None:
    """Costs page should have active sidebar link."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/costs")
        assert response.status_code == 200
        assert 'href="/costs"' in response.text
