from __future__ import annotations

from fastapi.testclient import TestClient

from control_room.app import create_app


def test_dashboard_returns_200():
    """Dashboard route should return 200 with page title."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "Dashboard" in response.text


def test_project_cards_partial_returns_200():
    """Project cards HTMX partial should return 200."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/partials/project-cards")
        assert response.status_code == 200
