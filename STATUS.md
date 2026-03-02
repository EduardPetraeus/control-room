# Control Room — Build Status

## Phase 1: Skeleton + Config
- **Status:** DONE
- pyproject.toml, config.yaml, CLAUDE.md
- FastAPI app factory + Jinja2 + HTMX + Tailwind dark theme
- 11/11 config tests passing

## Phase 2: Git + YAML Collectors
- **Status:** DONE
- git_log.py: commits, stats, branch, last_commit_date
- yaml_tasks.py: load from dirs, _convert_dates
- status_md.py: regex parser for version, tests, health, branch
- 18/18 collector tests passing

## Phase 3: Project Cards + Aggregator
- **Status:** DONE
- DataCache with 30s TTL
- DataAggregator with status color logic
- HTMX project cards with auto-refresh
- 8/8 aggregator tests + 2 route tests

## Phase 4: Kanban Board
- **Status:** DONE
- UnifiedTask model with status normalization
- 5-column kanban (backlog, todo, in_progress, review, done)
- Priority sorting, blocked badges

## Phase 5: GitHub Integration + Activity Feed
- **Status:** DONE
- gh CLI integration for project items + repo events
- Activity feed with color-coded timeline
- YAML/GitHub task deduplication
- 9/9 GitHub tests passing

## Phase 6: Metrics + Polish
- **Status:** DONE
- Velocity metrics (commits, tests, completion rate)
- Per-repo commit bar charts
- Detailed projects table with health scores
- Sidebar nav with active state + mobile responsive
- ruff check + format clean
- 52/52 tests passing

## Phase 7: Governance + CI/CD
- **Status:** DONE
- CLAUDE.md upgraded to governance-framework standard (Identity, Scope, Boundaries, project_context, security_protocol, mandatory_session_protocol, mandatory_task_reporting)
- CHANGELOG.md (Keep a Changelog format)
- ARCHITECTURE.md with data flow diagram
- PROJECT_PLAN.md with v0.1.0-v0.3.0 milestones
- docs/adr/ADR-001-fastapi-htmx-no-database.md
- backlog/ with 5 YAML task files (ai-pm schema)
- .github/workflows/ci.yml (Python 3.9 + 3.12 matrix, pytest + ruff)
- .pre-commit-config.yaml (ruff + ruff-format)
- Docstrings on all public test functions
- 5 GitHub issues created and added to project board #1
- ai-standards: 11/11 checks passing
- Health score: 59% (Level 2 Structured, up from 15% Level 0)
- 52/52 tests passing
