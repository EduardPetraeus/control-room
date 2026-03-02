from __future__ import annotations

import datetime
from pathlib import Path

import yaml

from control_room.config import (
    AppConfig,
    RepoConfig,
    ServerConfig,
    _convert_dates,
    load_config,
)


class TestConvertDates:
    def test_converts_date_to_string(self):
        data = {"due": datetime.date(2026, 1, 15)}
        result = _convert_dates(data)
        assert result == {"due": "2026-01-15"}

    def test_converts_datetime_to_string(self):
        data = {"created": datetime.datetime(2026, 1, 15, 10, 30)}
        result = _convert_dates(data)
        assert result == {"created": "2026-01-15T10:30:00"}

    def test_handles_nested_structures(self):
        data = {
            "tasks": [
                {"name": "task1", "due": datetime.date(2026, 3, 1)},
            ]
        }
        result = _convert_dates(data)
        assert result["tasks"][0]["due"] == "2026-03-01"

    def test_passes_through_normal_values(self):
        data = {"name": "test", "count": 42, "active": True}
        result = _convert_dates(data)
        assert result == data


class TestServerConfig:
    def test_defaults(self):
        config = ServerConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.cache_ttl_seconds == 30


class TestRepoConfig:
    def test_expands_tilde(self):
        config = RepoConfig(name="test", path="~/some/path")
        assert "~" not in config.path
        assert Path(config.path).is_absolute()

    def test_stores_name(self):
        config = RepoConfig(name="my-repo", path="/tmp/repo")
        assert config.name == "my-repo"


class TestLoadConfig:
    def test_loads_from_yaml(self, tmp_path):
        config_data = {
            "server": {"port": 9000},
            "repos": [
                {
                    "name": "test-repo",
                    "path": str(tmp_path),
                    "description": "Test",
                }
            ],
        }
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(config_file)
        assert config.server.port == 9000
        assert len(config.repos) == 1
        assert config.repos[0].name == "test-repo"

    def test_returns_default_for_missing_file(self, tmp_path):
        config = load_config(tmp_path / "nonexistent.yaml")
        assert isinstance(config, AppConfig)
        assert len(config.repos) == 0

    def test_returns_default_for_empty_file(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")
        config = load_config(config_file)
        assert isinstance(config, AppConfig)

    def test_handles_dates_in_yaml(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("server:\n  port: 8000\nrepos:\n  - name: test\n    path: /tmp\n")
        config = load_config(config_file)
        assert config.server.port == 8000
