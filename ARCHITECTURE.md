# Control Room — Architecture

## Overview

Control Room is a fleet command center for solo developers running parallel Claude Code sessions. Local-first (ADR-002) — runs on developer's machine, reads data from filesystem and GitHub CLI. No database — all data collected fresh with 30s caching.

## Data Flow

```
git repos (subprocess) ──────┐
YAML task files ─────────────┤
STATUS.md/README.md ─────────┤
GitHub CLI (gh) ─────────────┤
session-heartbeat.json ──────┼──→ DataAggregator ──→ DataCache (30s TTL) ──→ FastAPI routes ──→ Jinja2 + HTMX
ai-governance-framework ─────┤                                              ↕
ai-pm TaskEngine ────────────┘                                     JSON API (/agent/master/)
```

## Key Design Decisions

1. **No database** — solo dev tool. Git history + YAML files + GitHub API + heartbeat files are the sources of truth.
2. **HTMX over SPA** — server-rendered HTML with partial updates. No build step, no JS framework.
3. **Subprocess over libraries** — `git` and `gh` CLI are already installed and authenticated.
4. **30s in-memory cache** — fast enough for dashboard, fresh enough for solo workflow.
5. **Local-first** (ADR-002) — heartbeat via filesystem JSON files, no hosted deployment.
6. **Framework integration** — imports ai-governance-framework automation scripts and ai-pm TaskEngine at runtime.

## Governance Layer Mapping

| Layer | Control Room Feature | Route |
|---|---|---|
| Layer 4 (Validation) | Governance collector, drift detection | /projects |
| Layer 5 (Observability) | Fleet dashboard, cost tracking, health scores | /fleet, /costs |
| Layer 6 (Human-in-the-loop) | Blocker queue | /queue |
| Layer 7 (Orchestration) | Master agent API | /agent/master/* |

## Module Responsibilities

| Module | Responsibility |
|---|---|
| `config.py` | Load YAML config, Pydantic validation, path expansion |
| `collectors/git_log.py` | Git subprocess: commits, branches, stats |
| `collectors/yaml_tasks.py` | Load YAML task files from repo directories |
| `collectors/status_md.py` | Regex parser for STATUS.md/README.md metadata |
| `collectors/github.py` | GitHub project items + repo events via `gh` CLI |
| `collectors/heartbeat.py` | Scan repos for session-heartbeat.json files |
| `collectors/governance.py` | Wrap ai-governance-framework automation scripts |
| `collectors/cost.py` | Aggregate costs from heartbeats + COST_LOG.md |
| `collectors/queue.py` | Aggregate blockers from heartbeats, tasks, drift |
| `collectors/task_engine.py` | Wrap ai-pm TaskEngine for critical-path + pick-next |
| `collectors/aggregator.py` | Merge all sources, cache, status color logic |
| `routes/dashboard.py` | / — project cards + activity feed |
| `routes/fleet.py` | /fleet — live session grid with heartbeat data |
| `routes/queue.py` | /queue — prioritized blocker list |
| `routes/tasks.py` | /tasks — kanban board |
| `routes/costs.py` | /costs — cost tracking with budget alerts |
| `routes/projects.py` | /projects — detailed project table |
| `routes/metrics.py` | /metrics — velocity charts |
| `routes/orchestration.py` | /agent/master/* — JSON API for agent orchestration |

## Session Heartbeat Schema

```json
{
  "session_id": "abc123",
  "repo": "ai-governance-framework",
  "branch": "feature/health-check",
  "task": "Implement health check endpoint",
  "progress": 0.6,
  "status": "active",
  "blocker": null,
  "cost_usd": 1.25,
  "tokens_used": 15000,
  "model": "claude-opus-4-6",
  "timestamp": "2026-03-02T14:30:00Z"
}
```

## Status Color Logic

- **Green:** tests passing + commits within 7 days
- **Amber:** no test data OR no commits in 7-30 days
- **Red:** tests failing OR health score < 50%
- **Gray:** no data available
