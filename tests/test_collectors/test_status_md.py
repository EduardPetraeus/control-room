from __future__ import annotations

from pathlib import Path

from control_room.collectors.status_md import get_all_status_info, parse_status_md
from control_room.config import RepoConfig
from control_room.models.project import StatusInfo


class TestParseStatusMd:
    def test_extracts_version(self):
        """Verify version string is extracted from STATUS.md heading."""
        content = "# My Project v0.3.0\nSome description."
        result = parse_status_md(content)
        assert result.version == "v0.3.0"

    def test_extracts_test_counts(self):
        """Verify passing/total test counts are extracted from STATUS.md."""
        content = "## Tests\n864/864 passing\n"
        result = parse_status_md(content)
        assert result.test_passing == 864
        assert result.test_count == 864

    def test_extracts_test_count_simple(self):
        """Verify simple test count format is parsed correctly."""
        content = "Ran 120 tests successfully."
        result = parse_status_md(content)
        assert result.test_count == 120

    def test_extracts_health_score(self):
        """Verify health score percentage is extracted."""
        content = "Overall: 55% health score."
        result = parse_status_md(content)
        assert result.health_score == "55%"

    def test_extracts_status_text(self):
        """Verify status text is extracted from bold-formatted line."""
        content = "# Project\n**Status:** DONE\n"
        result = parse_status_md(content)
        assert "DONE" in result.status_text

    def test_handles_empty_content(self):
        """Verify empty content returns StatusInfo with all None fields."""
        result = parse_status_md("")
        assert isinstance(result, StatusInfo)
        assert result.version is None
        assert result.test_count is None
        assert result.test_passing is None
        assert result.health_score is None
        assert result.current_branch is None
        assert result.status_text == "unknown"

    def test_get_all_status_info_with_file(self, tmp_path: Path):
        """Verify get_all_status_info reads and parses STATUS.md per repo."""
        repo_dir = tmp_path / "my-repo"
        repo_dir.mkdir()
        status_file = repo_dir / "STATUS.md"
        status_file.write_text("# My Repo v1.2.3\n**Status:** SHIPPED\n120 tests\n")

        repo = RepoConfig(name="my-repo", path=str(repo_dir))
        results = get_all_status_info([repo])

        assert "my-repo" in results
        info = results["my-repo"]
        assert info.version == "v1.2.3"
        assert info.test_count == 120
        assert "SHIPPED" in info.status_text
