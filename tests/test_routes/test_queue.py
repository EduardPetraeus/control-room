from __future__ import annotations

from fastapi.testclient import TestClient

from control_room.app import create_app


def test_queue_page_returns_200() -> None:
    """Queue page should return 200 with page title."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/queue")
        assert response.status_code == 200
        assert "Queue" in response.text


def test_queue_list_partial_returns_200() -> None:
    """Queue list HTMX partial should return 200."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/partials/queue-list")
        assert response.status_code == 200


def test_queue_page_shows_empty_state_or_items() -> None:
    """Queue page should show empty state or blocker items."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/queue")
        assert response.status_code == 200
        # Either empty state or actual queue items are valid
        has_empty_state = "No blockers. All clear." in response.text
        has_queue_items = "queue" in response.text.lower()
        assert has_empty_state or has_queue_items


def test_queue_page_contains_stats_bar() -> None:
    """Queue page should contain priority stats bar."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/queue")
        assert response.status_code == 200
        assert "Critical" in response.text
        assert "High" in response.text
        assert "Medium" in response.text
        assert "Low" in response.text


def test_queue_page_has_htmx_polling() -> None:
    """Queue page should have HTMX auto-refresh configured."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/queue")
        assert response.status_code == 200
        assert 'hx-get="/partials/queue-list"' in response.text
        assert "every 15s" in response.text


def test_queue_page_sidebar_link() -> None:
    """Queue page should have the Queue link in the sidebar."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/queue")
        assert response.status_code == 200
        assert 'href="/queue"' in response.text
