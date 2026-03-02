from __future__ import annotations

import datetime
import os
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, field_validator


def _convert_dates(data: object) -> object:
    """Recursively convert datetime.date/datetime objects to strings after yaml.safe_load()."""
    if isinstance(data, dict):
        return {k: _convert_dates(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_convert_dates(item) for item in data]
    if isinstance(data, (datetime.date, datetime.datetime)):
        return data.isoformat()
    return data


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    cache_ttl_seconds: int = 30


class GitHubConfig(BaseModel):
    project_url: str = ""
    username: str = ""


class RepoConfig(BaseModel):
    name: str
    path: str
    task_dir: str = "tasks"
    description: str = ""

    @field_validator("path", mode="before")
    @classmethod
    def expand_path(cls, v: str) -> str:
        """Expand ~ and resolve the repo path to an absolute path."""
        return str(Path(os.path.expanduser(v)).resolve())


class AppConfig(BaseModel):
    server: ServerConfig = ServerConfig()
    github: GitHubConfig = GitHubConfig()
    repos: list[RepoConfig] = []


def load_config(config_path: str | Path | None = None) -> AppConfig:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
    config_path = Path(config_path)

    if not config_path.exists():
        return AppConfig()

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    if raw is None:
        return AppConfig()

    data = _convert_dates(raw)
    return AppConfig.model_validate(data)


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Get cached application configuration."""
    return load_config()
