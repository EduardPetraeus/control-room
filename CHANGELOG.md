# Changelog

All notable changes to Control Room are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).

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
