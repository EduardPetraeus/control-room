# Control Room — Governance

## Identity
Control Room is a FastAPI + HTMX + Tailwind dashboard for solo developers managing multiple repos, tasks, and GitHub projects. Part of the Agentic Engineering OS ecosystem.

- Owner: Claus Eduard Petraeus
- Stack: Python 3.9+, FastAPI, Jinja2, HTMX, Tailwind CSS
- Repo: ~/Github repos/control-room/
- Branch policy: all work on feature branches, never commit directly to main

## Scope
- Dashboard pages: /, /tasks, /projects, /metrics
- Collectors: git subprocess, YAML tasks, STATUS.md parser, GitHub CLI
- Data: in-memory cache (30s TTL), no database
- Templates: Jinja2 + HTMX partials with dark theme

### Out of scope
- User authentication (solo dev tool)
- Database or persistent storage
- JavaScript frameworks
- Multi-tenant or team features (solo-first)

## Boundaries
- No secrets in code (use config.yaml for paths, never API keys)
- All collectors must be fault-tolerant (timeout, returncode check, log + return default)
- Never auto-commit to main
- Maximum 15 files modified per session
- All Python files: `from __future__ import annotations`

## Conventions
- `snake_case` variables/functions/modules
- `kebab-case` files/dirs in templates
- `PascalCase` classes
- `_convert_dates()` after every `yaml.safe_load()`
- Conventional Commits for git messages

## Project Structure
```
src/control_room/
  app.py          — FastAPI factory
  config.py       — Pydantic config models
  __main__.py     — CLI entry point
  models/         — Pydantic data models
  collectors/     — Data collection (git, YAML, GitHub)
  routes/         — FastAPI routers
  templates/      — Jinja2 templates
  static/         — CSS
tests/
  test_collectors/
  test_routes/
```

## Theme Colors
- Background: #0a0f0d
- Cards: #111916
- Borders: #1a2f23
- Green: #00ff88, Amber: #ffaa00, Red: #ff4444

## project_context
- Solo dev dashboard, dogfooding the Agentic Engineering OS
- v0.1.0 shipped — all 4 pages, 52 tests, governance applied
- Next: showcase in agentic-engineering docs, explore plugin system

## security_protocol
- No API keys or tokens in code or config.yaml
- GitHub access via `gh` CLI (uses system auth)
- Config paths use `~` expansion, never absolute user paths in committed code

## mandatory_session_protocol
- Start: read STATUS.md, check test status, review backlog/
- During: run tests after significant changes, update STATUS.md
- End: commit with conventional message, update backlog task status

## mandatory_task_reporting
- Tasks tracked in backlog/ as YAML files (ai-pm schema)
- GitHub Issues synced to project board #1
- Status updates: pending → in_progress → done
