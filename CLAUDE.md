# Control Room — Repo Rules

## Language
- All code, comments, docstrings, variable names, commit messages, and documentation in English
- Danish only in conversations

## Stack
- Python 3.9+ (use `from __future__ import annotations` in every .py file)
- FastAPI + HTMX + Tailwind CSS (CDN)
- No database — YAML config + in-memory cache (30s TTL)
- No JS framework — vanilla HTMX for interactivity

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

## Conventions
- `snake_case` for variables, functions, modules
- `kebab-case` for file/directory names in templates
- `PascalCase` for classes
- `_convert_dates()` after every `yaml.safe_load()`
- All collectors must be fault-tolerant (timeout, returncode check, log + return default)
- Tests must pass before committing

## Theme Colors
- Background: `#0a0f0d`
- Cards: `#111916`
- Borders: `#1a2f23`
- Green accent: `#00ff88`
- Amber warning: `#ffaa00`
- Red error: `#ff4444`

## Git
- All work on `feature/v1` branch
- Never commit to main directly
- Conventional commits
