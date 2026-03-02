from __future__ import annotations

from pydantic import BaseModel, Field


class CommitInfo(BaseModel):
    """Represents a single git commit."""

    hash: str
    author: str
    date: str
    message: str
    repo_name: str = ""


class CommitStats(BaseModel):
    """Aggregated statistics for commits in a time window."""

    total_commits: int
    first_commit_date: str | None
    last_commit_date: str | None
    authors: list[str] = Field(default_factory=list)


class GitHubProjectItem(BaseModel):
    """An item from a GitHub Projects board."""

    title: str
    status: str = ""  # Todo, In Progress, Done
    item_type: str = ""  # Issue, PullRequest, DraftIssue
    url: str = ""
    repo: str = ""
    labels: list[str] = Field(default_factory=list)
    assignee: str = ""


class ActivityEvent(BaseModel):
    """A cross-repo activity event for the timeline."""

    event_type: str  # commit, issue, pr, release
    title: str
    repo_name: str = ""
    date: str = ""
    url: str = ""
    color: str = "gray"  # green, amber, red, blue
