# Changelog

All notable changes to Control Room are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [0.2.0] - 2026-03-02

### Added
- Fleet dashboard (/fleet) — real-time view of Claude Code sessions via heartbeat files
- Blocker queue (/queue) — prioritized human-in-the-loop queue aggregating agent blockers, blocked tasks, and governance drift
- Cost tracking (/costs) — per-session and fleet-wide cost monitoring with budget alerts
- Master agent API (/agent/master/) — JSON endpoints for task decomposition, session assignment, fleet status, and blocker escalation
- Governance collector — integrates ai-governance-framework automation scripts (health score, drift detection, cost parsing, content quality)
- ai-pm TaskEngine integration — critical-path analysis, pick-next task, dependency resolution, cycle detection across all repos

### Architecture
- ADR-002: Local-first architecture decision (heartbeat via filesystem, no hosted deployment)
- 9 collectors: git_log, yaml_tasks, status_md, github, heartbeat, governance, queue, cost, task_engine
- 7 dashboard pages + 4 JSON API endpoints
- Governance layers mapped: Layer 5 (Observability), Layer 6 (Human-in-the-loop), Layer 7 (Orchestration)

### Infrastructure
- 172 tests (120 new), ruff check + format clean
- ai-governance-framework imported via sys.path
- ai-project-management installed as editable dependency

## [0.1.0] - 2026-03-02

### Added
- FastAPI application with dark-themed dashboard (HTMX + Tailwind)
- Project cards with color-coded health status (green/amber/red/gray)
- 5-column kanban board merging YAML tasks + GitHub project items
- Detailed projects table with branch, version, tests, commits
- Velocity metrics page with per-repo commit charts
- Cross-repo activity feed with color-coded timeline
- Git subprocess collector (commits, branches, stats)
- YAML task file collector with _convert_dates()
- STATUS.md/README.md parser for version, tests, health scores
- GitHub CLI integration (project items + repo events)
- DataCache with 30s TTL for all collectors
- 52 tests, ruff check + format clean
- Governance: CLAUDE.md, CHANGELOG, STATUS.md

### Infrastructure
- pyproject.toml with hatchling build
- config.yaml for 8 repos
- Mobile-responsive sidebar navigation
- HTMX auto-refresh every 30s on all pages
