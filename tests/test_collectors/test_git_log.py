from __future__ import annotations

import os
import subprocess

import pytest

from control_room.collectors.git_log import (
    get_commit_stats,
    get_current_branch,
    get_last_commit_date,
    get_recent_commits,
)
from control_room.models.activity import CommitInfo, CommitStats


@pytest.fixture()
def tmp_git_repo(tmp_path):
    """Create a temporary git repository with one commit."""
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Test Author",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test Author",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }
    )
    repo = str(tmp_path)
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=repo,
        env=env,
        check=True,
        capture_output=True,
    )
    readme = tmp_path / "README.md"
    readme.write_text("# Test repo\n")
    subprocess.run(["git", "add", "."], cwd=repo, env=env, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        env=env,
        check=True,
        capture_output=True,
    )
    return repo


def test_get_recent_commits(tmp_git_repo):
    """Recent commits returns at least one CommitInfo for a repo with a commit."""
    commits = get_recent_commits(tmp_git_repo)
    assert len(commits) >= 1
    assert isinstance(commits[0], CommitInfo)
    assert commits[0].author == "Test Author"
    assert commits[0].message == "Initial commit"


def test_get_recent_commits_empty_repo(tmp_path):
    """Non-git directory returns an empty list."""
    commits = get_recent_commits(str(tmp_path))
    assert commits == []


def test_get_commit_stats(tmp_git_repo):
    """Commit stats reflect at least 1 commit and contain the author."""
    stats = get_commit_stats(tmp_git_repo)
    assert isinstance(stats, CommitStats)
    assert stats.total_commits >= 1
    assert "Test Author" in stats.authors
    assert stats.first_commit_date is not None
    assert stats.last_commit_date is not None


def test_get_current_branch(tmp_git_repo):
    """Current branch is 'main' (or 'master' on older git defaults)."""
    branch = get_current_branch(tmp_git_repo)
    assert branch in ("main", "master")


def test_get_last_commit_date(tmp_git_repo):
    """Last commit date is a non-None string."""
    date = get_last_commit_date(tmp_git_repo)
    assert date is not None
    assert isinstance(date, str)
    assert len(date) > 0


def test_get_current_branch_invalid_dir(tmp_path):
    """Non-git directory returns 'unknown'."""
    branch = get_current_branch(str(tmp_path))
    assert branch == "unknown"
