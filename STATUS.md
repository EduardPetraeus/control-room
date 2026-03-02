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
