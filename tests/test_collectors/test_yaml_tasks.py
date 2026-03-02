from __future__ import annotations

from pathlib import Path

from control_room.collectors.yaml_tasks import load_tasks_from_directory


def test_load_single_task_file(tmp_path: Path) -> None:
    """A YAML file with one task should yield exactly one YamlTask."""
    task_file = tmp_path / "sprint.yaml"
    task_file.write_text(
        "- id: T-001\n  title: Build dashboard\n  status: in-progress\n",
        encoding="utf-8",
    )

    tasks = load_tasks_from_directory(str(tmp_path))

    assert len(tasks) == 1
    assert tasks[0].id == "T-001"
    assert tasks[0].title == "Build dashboard"
    assert tasks[0].status == "in-progress"


def test_load_multiple_files(tmp_path: Path) -> None:
    """Tasks from multiple YAML files are combined into one list."""
    (tmp_path / "a.yaml").write_text("- id: T-001\n  title: First task\n", encoding="utf-8")
    (tmp_path / "b.yml").write_text("- id: T-002\n  title: Second task\n", encoding="utf-8")

    tasks = load_tasks_from_directory(str(tmp_path))

    assert len(tasks) == 2
    ids = {t.id for t in tasks}
    assert ids == {"T-001", "T-002"}


def test_handles_tasks_key(tmp_path: Path) -> None:
    """A YAML file with a top-level 'tasks' key should be supported."""
    task_file = tmp_path / "backlog.yaml"
    task_file.write_text(
        "tasks:\n  - id: T-010\n    title: Wrapped task\n",
        encoding="utf-8",
    )

    tasks = load_tasks_from_directory(str(tmp_path))

    assert len(tasks) == 1
    assert tasks[0].id == "T-010"
    assert tasks[0].title == "Wrapped task"


def test_skips_invalid_yaml(tmp_path: Path) -> None:
    """Invalid YAML files are skipped without raising."""
    bad_file = tmp_path / "broken.yaml"
    bad_file.write_text("{{{invalid", encoding="utf-8")

    tasks = load_tasks_from_directory(str(tmp_path))

    assert tasks == []


def test_empty_directory(tmp_path: Path) -> None:
    """An empty directory returns an empty task list."""
    tasks = load_tasks_from_directory(str(tmp_path))

    assert tasks == []
