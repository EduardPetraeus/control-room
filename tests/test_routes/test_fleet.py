from __future__ import annotations

from fastapi.testclient import TestClient

from control_room.app import create_app


def test_fleet_page_returns_200() -> None:
    """Fleet page should return 200 with page title."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/fleet")
        assert response.status_code == 200
        assert "Fleet" in response.text


def test_fleet_grid_partial_returns_200() -> None:
    """Fleet grid HTMX partial should return 200."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/partials/fleet-grid")
        assert response.status_code == 200


def test_fleet_page_shows_empty_state() -> None:
    """Fleet page with no heartbeats should show empty state message."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/fleet")
        assert response.status_code == 200
        assert "No active Claude Code sessions detected" in response.text


def test_fleet_page_contains_stats_bar() -> None:
    """Fleet page should contain the stats bar with counters."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/fleet")
        assert response.status_code == 200
        assert "Active" in response.text
        assert "Blocked" in response.text
        assert "Idle" in response.text
        assert "Completed" in response.text
        assert "Failed" in response.text


def test_fleet_page_has_htmx_polling() -> None:
    """Fleet page should have HTMX auto-refresh configured."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/fleet")
        assert response.status_code == 200
        assert 'hx-get="/partials/fleet-grid"' in response.text
        assert "every 10s" in response.text
