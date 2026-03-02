from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from control_room.app import create_app
from control_room.config import AppConfig, RepoConfig, ServerConfig


@pytest.fixture
def app_config(tmp_path) -> AppConfig:
    """Create a test configuration."""
    return AppConfig(
        server=ServerConfig(host="127.0.0.1", port=8000, reload=False),
        repos=[
            RepoConfig(
                name="test-repo",
                path=str(tmp_path / "test-repo"),
                task_dir="tasks",
                description="A test repository",
            ),
        ],
    )


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    app = create_app()
    return TestClient(app)
