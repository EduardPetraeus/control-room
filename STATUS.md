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

## Phase 8: Governance Collector (Issue #2)
- **Status:** DONE
- collectors/governance.py wrapping ai-governance-framework automation scripts
- Health score calculation via health_score_calculator.calculate_score()
- Drift detection via drift_detector.detect_drift()
- Cost log parsing via governance_dashboard.parse_cost_log()
- Content quality via content_quality_checker.run_quality_check()
- models/governance.py: GovernanceHealth, DriftReport, RepoGovernance models
- ProjectStatus extended with governance field
- All fault-tolerant with try/except and safe defaults
- 63/63 tests passing (11 new)

## Phase 9: Heartbeat + Fleet Dashboard (Issue #1)
- **Status:** DONE
- models/heartbeat.py: SessionHeartbeat, SessionStatus, FleetStatus
- collectors/heartbeat.py: filesystem-based heartbeat scanning (local-first per ADR-002)
- routes/fleet.py: GET /fleet + GET /partials/fleet-grid
- Fleet dashboard with session cards, color-coded status, progress bars
- HTMX auto-refresh every 10s
- Sidebar updated with Fleet link
- 84/84 tests passing (21 new)

## Phase 10: Blocker/Question Queue (Issue #3)
- **Status:** DONE
- models/queue.py: QueueItem, QueueItemType, QueueItemPriority, BlockerQueue
- collectors/queue.py: aggregates from heartbeat blockers, YAML blocked tasks, governance drift
- routes/queue.py: GET /queue + GET /partials/queue-list
- Priority-sorted queue: critical > high > medium > low
- HTMX auto-refresh every 15s
- Maps to Layer 6 (Human-in-the-loop) in governance architecture
- 158/158 tests passing (25 new)

## Phase 11: Cost Tracking Dashboard (Issue #4)
- **Status:** DONE
- models/cost.py: SessionCost, CostSummary with budget tracking
- collectors/cost.py: aggregates from heartbeat costs + governance COST_LOG.md
- routes/costs.py: GET /costs + GET /partials/cost-overview
- Budget progress bar, alert at 80% threshold, cost-by-model breakdown
- HTMX auto-refresh every 30s
- Maps to Layer 5 (Observability) in governance architecture

## Phase 12: ai-pm TaskEngine Integration
- **Status:** DONE
- collectors/task_engine.py wrapping ai-pm TaskEngine for fleet-wide use
- get_critical_path(): longest dependency chain per repo
- get_next_task(): highest-priority ready task with resolved deps
- get_fleet_next_tasks(): next available task across all repos
- detect_cycles(): circular dependency detection
- DataAggregator extended with get_critical_paths() and get_next_tasks()

## Phase 13: Master Agent API (Issue #10)
- **Status:** DONE
- models/orchestration.py: PlanRequest/Response, AssignRequest/Response, FleetAssessment, EscalateRequest/Response
- routes/orchestration.py: JSON API at /agent/master/
  - POST /plan — rule-based goal decomposition into subtasks
  - POST /assign — match tasks to idle sessions
  - GET /status — fleet assessment aggregating all data sources
  - POST /escalate — queue blockers for human resolution
- Maps to Layer 7 (Orchestration) in governance architecture

## Phase 14: Design Decisions
- **Status:** DONE
- docs/adr/ADR-002-local-first-architecture.md — local-first over hosted
- TASK-006 resolved

## Current Totals
- **172/172 tests passing**
- **ruff check + format clean**
- **7 pages:** Dashboard, Fleet, Queue, Tasks, Costs, Projects, Metrics
- **4 API endpoints:** /agent/master/plan, /assign, /status, /escalate
- **9 collectors:** git_log, yaml_tasks, status_md, github, heartbeat, governance, queue, cost, task_engine
- **Framework integrations:** ai-governance-framework (5 scripts), ai-project-management (TaskEngine)
