from __future__ import annotations

import datetime
import logging
from pathlib import Path

import yaml

from control_room.config import RepoConfig
from control_room.models.task import YamlTask

logger = logging.getLogger(__name__)


def _convert_dates(data: object) -> object:
    """Recursively convert datetime.date/datetime objects to strings."""
    if isinstance(data, dict):
        return {k: _convert_dates(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_convert_dates(item) for item in data]
    if isinstance(data, (datetime.date, datetime.datetime)):
        return data.isoformat()
    return data


def load_tasks_from_directory(task_dir: str, project_name: str = "") -> list[YamlTask]:
    """Load all tasks from YAML files in a directory.

    Each YAML file can contain either a top-level list of tasks or a dict
    with a ``tasks`` key holding a list.  Files that cannot be parsed are
    logged and skipped so one bad file never blocks the rest.
    """
    task_path = Path(task_dir)
    tasks: list[YamlTask] = []

    if not task_path.is_dir():
        logger.warning("Task directory does not exist: %s", task_dir)
        return tasks

    for file in sorted(task_path.iterdir()):
        if file.suffix not in (".yaml", ".yml"):
            continue

        try:
            raw = yaml.safe_load(file.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            logger.warning("Skipping invalid YAML file %s: %s", file, exc)
            continue
        except FileNotFoundError:
            logger.warning("File not found: %s", file)
            continue

        if raw is None:
            continue

        data = _convert_dates(raw)

        # Support top-level list or a dict with a "tasks" key.
        if isinstance(data, dict):
            task_list = data.get("tasks", [])
        elif isinstance(data, list):
            task_list = data
        else:
            logger.warning("Unexpected top-level type in %s, skipping", file)
            continue

        for entry in task_list:
            try:
                task = YamlTask.model_validate(entry)
                if project_name:
                    task.project = project_name
                tasks.append(task)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping invalid task in %s: %s", file, exc)

    return tasks


def get_all_project_tasks(repos: list[RepoConfig]) -> list[YamlTask]:
    """Collect tasks from every configured repo's task directory.

    Silently skips repos whose task directory does not exist.
    """
    all_tasks: list[YamlTask] = []

    for repo in repos:
        task_dir = str(Path(repo.path) / repo.task_dir)
        if not Path(task_dir).is_dir():
            continue
        all_tasks.extend(load_tasks_from_directory(task_dir, project_name=repo.name))

    return all_tasks
