# Control Room — Architecture

## Overview

Control Room is a read-only dashboard that aggregates data from multiple sources into a single browser tab. No database — all data is collected fresh (with 30s caching).

## Data Flow

```
git repos (subprocess) ──┐
YAML task files ─────────┼──→ DataAggregator ──→ DataCache (30s TTL) ──→ FastAPI routes ──→ Jinja2 + HTMX
STATUS.md/README.md ─────┤
GitHub CLI (gh) ─────────┘
```

## Key Design Decisions

1. **No database** — solo dev tool, read-only. Git history + YAML files + GitHub API are the sources of truth.
2. **HTMX over SPA** — server-rendered HTML with partial updates. No build step, no JS framework.
3. **Subprocess over libraries** — `git` and `gh` CLI are already installed and authenticated. No need for GitPython or PyGithub.
4. **30s in-memory cache** — fast enough for dashboard, fresh enough for solo workflow.

## Module Responsibilities

| Module | Responsibility |
|---|---|
| `config.py` | Load YAML config, Pydantic validation, path expansion |
| `collectors/git_log.py` | Git subprocess: commits, branches, stats |
| `collectors/yaml_tasks.py` | Load YAML task files from repo directories |
| `collectors/status_md.py` | Regex parser for STATUS.md/README.md metadata |
| `collectors/github.py` | GitHub project items + repo events via `gh` CLI |
| `collectors/aggregator.py` | Merge all sources, cache, status color logic |
| `routes/` | FastAPI endpoints: full pages + HTMX partials |
| `templates/` | Jinja2 with HTMX attributes for auto-refresh |

## Status Color Logic

- **Green:** tests passing + commits within 7 days
- **Amber:** no test data OR no commits in 7-30 days
- **Red:** tests failing OR health score < 50%
- **Gray:** no data available
