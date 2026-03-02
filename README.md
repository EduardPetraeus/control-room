# Control Room

Fleet command center for solo developers running parallel Claude Code sessions. Monitor agents, track costs, resolve blockers, and orchestrate tasks — all in one dark-themed browser tab. Built with FastAPI, HTMX, and Tailwind CSS.

## Why

When you run 10-20 parallel Claude Code sessions across multiple repos, you need visibility. Which agents are stuck? What's the cost burning rate? What blockers need human decisions? Control Room answers all of that with auto-refreshing data.

## Pages

| Page | Route | What it shows |
|---|---|---|
| **Dashboard** | `/` | Project cards with color-coded health + activity feed |
| **Fleet** | `/fleet` | Live session grid — status, progress, costs, blockers |
| **Queue** | `/queue` | Prioritized blocker list needing human attention |
| **Tasks** | `/tasks` | 5-column kanban board (YAML + GitHub) |
| **Costs** | `/costs` | Per-session costs, budget alerts, model breakdown |
| **Projects** | `/projects` | Detailed table — branch, version, tests, health scores |
| **Metrics** | `/metrics` | Velocity stats, commit charts, task completion rate |

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/agent/master/plan` | POST | Decompose a goal into subtasks with dependencies |
| `/agent/master/assign` | POST | Route tasks to idle Claude Code sessions |
| `/agent/master/status` | GET | Fleet assessment — sessions, blockers, critical paths |
| `/agent/master/escalate` | POST | Escalate a blocker to human queue |

All dashboard pages auto-refresh via HTMX polling (10-30s intervals).

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
- **Data sources:** git subprocess, YAML files, `gh` CLI, heartbeat JSON, ai-governance-framework, ai-pm
- **Testing:** pytest (172 tests)

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
    heartbeat.py      — Scan repos for session-heartbeat.json files
    governance.py     — Wrap ai-governance-framework automation scripts
    cost.py           — Aggregate costs from heartbeats + COST_LOG.md
    queue.py          — Aggregate blockers from heartbeats, tasks, drift
    task_engine.py    — Wrap ai-pm TaskEngine (critical-path, pick-next)
    aggregator.py     — DataCache (30s TTL) + DataAggregator (merges all)
  models/
    activity.py       — CommitInfo, CommitStats, GitHubProjectItem, ActivityEvent
    project.py        — StatusInfo, ProjectStatus (+ governance fields)
    task.py           — YamlTask, UnifiedTask
    metrics.py        — VelocityMetrics
    heartbeat.py      — SessionHeartbeat, SessionStatus, FleetStatus
    governance.py     — GovernanceHealth, DriftReport, RepoGovernance
    cost.py           — SessionCost, CostSummary
    queue.py          — QueueItem, BlockerQueue
    orchestration.py  — PlanRequest/Response, FleetAssessment, etc.
  routes/
    dashboard.py      — / and /partials/*
    fleet.py          — /fleet and /partials/fleet-grid
    queue.py          — /queue and /partials/queue-list
    tasks.py          — /tasks and /partials/kanban
    costs.py          — /costs and /partials/cost-overview
    projects.py       — /projects
    metrics.py        — /metrics
    orchestration.py  — /agent/master/* (JSON API)
  templates/          — Jinja2 + HTMX with dark theme
  static/             — Custom CSS (scrollbar, skeleton loading)
```

## License

MIT
