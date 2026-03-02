# Control Room — Project Plan

## Vision
Fleet command center for solo developers running parallel Claude Code sessions across multiple repos. Single-pane view of agents, tasks, costs, blockers, and governance health.

## Milestones

### v0.1.0 — MVP (DONE)
- [x] FastAPI + HTMX + Tailwind dark theme
- [x] Project cards with health status colors
- [x] 5-column kanban board (YAML + GitHub tasks)
- [x] Projects table with detailed stats
- [x] Metrics page with velocity charts
- [x] Activity feed with cross-repo timeline
- [x] 52 tests, ruff clean, governance applied

### v0.2.0 — Fleet Command Center (DONE — on feature branch, pending merge)
- [x] Fleet dashboard (/fleet) — heartbeat-based session monitoring
- [x] Blocker queue (/queue) — human-in-the-loop decision queue
- [x] Cost tracking (/costs) — per-session costs with budget alerts
- [x] Master agent API (/agent/master/) — plan, assign, status, escalate
- [x] Governance collector — ai-governance-framework automation integration
- [x] ai-pm TaskEngine integration — critical-path, pick-next, dependency resolution
- [x] ADR-002: Local-first architecture decision
- [x] 172 tests, ruff clean

### v0.3.0 — Live Fleet (NEXT)
- [ ] Claude Code hook for auto-generating session-heartbeat.json
- [ ] Heartbeat writer library (pip installable for other projects)
- [ ] Task creation/editing via HTMX forms in queue page
- [ ] Fix Starlette TemplateResponse deprecation warnings
- [ ] Live test with 5+ parallel Claude Code sessions

### v0.4.0 — Intelligence
- [ ] LLM-powered goal decomposition (replace rule-based _decompose_goal)
- [ ] Auto-resolution patterns for known blocker types
- [ ] Cost optimization recommendations (model routing suggestions)
- [ ] Notification system for budget alerts and stuck agents

### v0.5.0 — Plugin System
- [ ] Plugin architecture for custom collectors
- [ ] User-defined dashboard widgets
- [ ] Export metrics to JSON/CSV

## Non-Goals
- Multi-user authentication
- Database persistence
- JavaScript framework
- Mobile native app
- Hosted/cloud deployment (local-first per ADR-002)
