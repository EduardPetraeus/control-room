from __future__ import annotations

import time

from control_room.collectors.aggregator import DataAggregator, DataCache
from control_room.config import AppConfig
from control_room.models.project import ProjectStatus
from control_room.models.task import YamlTask


class TestDataCache:
    """Tests for the DataCache in-memory TTL cache."""

    def test_cache_stores_and_retrieves(self) -> None:
        """Verify cache stores and retrieves values within TTL."""
        cache = DataCache(ttl_seconds=10)
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_cache_expires_after_ttl(self) -> None:
        """Verify cached values expire after TTL elapses."""
        cache = DataCache(ttl_seconds=0.05)
        cache.set("key", "value")
        time.sleep(0.1)
        assert cache.get("key") is None

    def test_cache_clear(self) -> None:
        """Verify clear removes all entries from cache."""
        cache = DataCache(ttl_seconds=10)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None


class TestDetermineStatusColor:
    """Tests for DataAggregator._determine_status_color."""

    def _make_aggregator(self) -> DataAggregator:
        return DataAggregator(config=AppConfig())

    def test_determine_color_green(self) -> None:
        """Verify green status when all tests pass and commits are recent."""
        agg = self._make_aggregator()
        project = ProjectStatus(
            name="test",
            test_count=100,
            test_passing=100,
            commits_30d=5,
        )
        assert agg._determine_status_color(project) == "green"

    def test_determine_color_red_failing(self) -> None:
        """Verify red status when some tests are failing."""
        agg = self._make_aggregator()
        project = ProjectStatus(
            name="test",
            test_count=100,
            test_passing=90,
            commits_30d=5,
        )
        assert agg._determine_status_color(project) == "red"

    def test_determine_color_red_low_health(self) -> None:
        """Verify red status when health score is below threshold."""
        agg = self._make_aggregator()
        project = ProjectStatus(
            name="test",
            health_score="40%",
            commits_30d=3,
        )
        assert agg._determine_status_color(project) == "red"

    def test_determine_color_amber_stale(self) -> None:
        """Verify amber status when repo has no recent commits."""
        agg = self._make_aggregator()
        project = ProjectStatus(
            name="test",
            test_count=100,
            test_passing=100,
            commits_30d=0,
        )
        assert agg._determine_status_color(project) == "amber"

    def test_determine_color_gray(self) -> None:
        """Verify gray status when no data is available."""
        agg = self._make_aggregator()
        project = ProjectStatus(
            name="test",
        )
        assert agg._determine_status_color(project) == "gray"


class TestYamlToUnified:
    """Tests for DataAggregator._yaml_to_unified conversion."""

    def test_basic_conversion(self) -> None:
        """Verify YAML task is converted to unified task with correct fields."""
        aggregator = DataAggregator(AppConfig())
        yaml_task = YamlTask(
            id="T-1", title="Fix bug", status="todo", priority="high", project="test"
        )
        unified = aggregator._yaml_to_unified(yaml_task)
        assert unified.id == "T-1"
        assert unified.status == "todo"
        assert unified.priority_order == 1
        assert unified.source == "yaml"

    def test_blocked_task(self) -> None:
        """Verify blocked tasks are normalized to backlog with blocked flag."""
        aggregator = DataAggregator(AppConfig())
        yaml_task = YamlTask(id="T-2", title="Deploy", status="blocked", blocked_by=["T-1"])
        unified = aggregator._yaml_to_unified(yaml_task)
        assert unified.status == "backlog"
        assert unified.is_blocked is True

    def test_status_normalization(self) -> None:
        """Verify various status strings are normalized to canonical values."""
        aggregator = DataAggregator(AppConfig())
        for status_in, expected in [
            ("wip", "in_progress"),
            ("complete", "done"),
            ("pending", "todo"),
            ("open", "todo"),
        ]:
            task = YamlTask(id="T-3", title="Test", status=status_in)
            assert aggregator._yaml_to_unified(task).status == expected

    def test_priority_sorting(self) -> None:
        """Verify unified tasks sort correctly by priority order."""
        aggregator = DataAggregator(AppConfig())
        tasks = [
            YamlTask(id="T-1", title="Low", priority="low"),
            YamlTask(id="T-2", title="Critical", priority="critical"),
            YamlTask(id="T-3", title="High", priority="high"),
        ]
        unified = [aggregator._yaml_to_unified(t) for t in tasks]
        unified.sort(key=lambda t: t.priority_order)
        assert [t.priority for t in unified] == ["critical", "high", "low"]
