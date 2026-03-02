# Control Room

A single-pane dashboard for solo developers juggling multiple repos, tasks, and GitHub projects. Built with FastAPI, HTMX, and Tailwind CSS — no database, no JS framework, just a fast dark-themed overview of everything that matters.

## Why

When you work across 5-10 repos simultaneously, context gets fragmented. Which repos have failing tests? What tasks are blocked? Where did you last commit? Control Room answers all of that in one browser tab with auto-refreshing data.

## Pages

| Page | What it shows |
|---|---|
| **Dashboard** | Project cards with color-coded health (green/amber/red/gray) + activity feed |
| **Tasks** | 5-column kanban board merging YAML tasks and GitHub project items |
| **Projects** | Detailed table — branch, version, test counts, commits, health scores |
| **Metrics** | Velocity stats, per-repo commit charts, task completion rate |

All data refreshes automatically every 30 seconds via HTMX polling.

## Quick Start

```bash
git clone https://github.com/EduardPetraeus/control-room.git
cd control-room
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Edit config.yaml to point to your repos, then:
python -m control_room
# → http://localhost:8000
```

## Configuration

Edit `config.yaml` to define your repos and GitHub project:

```yaml
server:
  port: 8000
  cache_ttl_seconds: 30

github:
  project_url: "https://github.com/users/YOUR_USERNAME/projects/1"
  username: "YOUR_USERNAME"

repos:
  - name: my-repo
    path: ~/path/to/repo
    task_dir: tasks
    description: "What this repo does"
```

**Task files:** Place YAML files in each repo's `task_dir`. Each file can contain a list of tasks or a `tasks:` key:

```yaml
tasks:
  - id: T-1
    title: Fix login bug
    status: in_progress
    priority: high
```

**GitHub integration** requires the [`gh` CLI](https://cli.github.com/) to be installed and authenticated.

## How It Works

- **No database** — reads git history via subprocess, YAML files from disk, GitHub data via `gh` CLI
- **30s in-memory cache** — fast page loads, fresh enough for a solo workflow
- **Fault-tolerant collectors** — missing repos, bad YAML, or `gh` auth issues are logged and skipped, never crash the app
- **Status color logic:** green (tests passing + recent commits), amber (stale or no tests), red (failing tests or low health), gray (no data)

## Stack

- **Backend:** Python 3.9+, FastAPI, Jinja2, Pydantic v2
- **Frontend:** HTMX (no JS framework), Tailwind CSS (CDN)
- **Data sources:** git subprocess, YAML files, `gh` CLI
- **Testing:** pytest (52 tests)

## Development

```bash
pytest tests/ -v              # Run tests
ruff check . && ruff format . # Lint and format
python -m control_room        # Start dev server (auto-reload by default)
```

## Architecture

```
src/control_room/
  app.py              — FastAPI factory with lifespan
  config.py           — Pydantic config models + YAML loader
  __main__.py         — CLI entry point (click + uvicorn)
  collectors/
    git_log.py        — Recent commits, branch, stats via git subprocess
    yaml_tasks.py     — Load tasks from YAML files across repos
    status_md.py      — Parse STATUS.md/README.md for version, tests, health
    github.py         — GitHub project items + repo events via gh CLI
    aggregator.py     — DataCache (30s TTL) + DataAggregator (merges all sources)
  models/
    activity.py       — CommitInfo, CommitStats, GitHubProjectItem, ActivityEvent
    project.py        — StatusInfo, ProjectStatus
    task.py           — YamlTask, UnifiedTask
    metrics.py        — VelocityMetrics
  routes/
    dashboard.py      — / and /partials/* endpoints
    tasks.py          — /tasks and /partials/kanban
    projects.py       — /projects
    metrics.py        — /metrics
  templates/          — Jinja2 + HTMX with dark theme
  static/             — Custom CSS (scrollbar, skeleton loading)
```

## License

MIT
