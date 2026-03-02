# ADR-001: FastAPI + HTMX with no database

## Status
Accepted

## Date
2026-03-02

## Context
Need a dashboard to monitor 8+ repos, YAML tasks, and GitHub project board. Options considered:
- Streamlit (easy, but limited layout control)
- Next.js (overkill for solo dev tool)
- FastAPI + HTMX (lightweight, server-rendered, no JS build step)

## Decision
Use FastAPI + HTMX + Tailwind CSS (CDN). No database — read git history, YAML files, and GitHub CLI directly. 30s in-memory cache.

## Consequences
- Pro: Zero infrastructure, starts in 2 seconds, no migrations
- Pro: HTMX gives reactivity without JS framework complexity
- Pro: Jinja2 templates are simple and readable
- Con: No persistent history (can't track trends over time)
- Con: Cache invalidation is time-based only (no event-driven refresh)
- Con: Cold start reads all repos sequentially (could be slow with many repos)
