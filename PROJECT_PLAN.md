# Control Room — Project Plan

## Vision
Single-pane dashboard for solo developers managing multiple repos, tasks, and GitHub projects.

## Milestones

### v0.1.0 — MVP (DONE)
- [x] FastAPI + HTMX + Tailwind dark theme
- [x] Project cards with health status colors
- [x] 5-column kanban board (YAML + GitHub tasks)
- [x] Projects table with detailed stats
- [x] Metrics page with velocity charts
- [x] Activity feed with cross-repo timeline
- [x] 52 tests, ruff clean, governance applied

### v0.2.0 — Polish & Dogfood
- [ ] Fix Starlette TemplateResponse deprecation warning
- [ ] Add task creation/editing via HTMX forms
- [ ] Notification system for failing tests
- [ ] Customizable refresh interval per page

### v0.3.0 — Plugin System
- [ ] Plugin architecture for custom collectors
- [ ] User-defined dashboard widgets
- [ ] Export metrics to JSON/CSV

## Non-Goals
- Multi-user authentication
- Database persistence
- JavaScript framework
- Mobile native app
