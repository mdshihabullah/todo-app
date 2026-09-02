# Tiny Todo — Agent Guide

## Agent skills

### Issue tracker

GitHub. See `docs/agents/issue-tracker.md`.

### Triage labels

(note: triage skill not installed, skipping)

### Domain docs

single-context. See `docs/agents/domain.md`.

## Quick Start
```bash
python3 app.py
# Open http://localhost:9990
```

## Architecture
- **app.py** — HTTP server (stdlib only), routes: `GET /`, `POST /add|/toggle|/delete`
- **todos.py** — Logic + data layer (in-memory list + JSON persistence at `todos.json`)
- **page.html** — Template with `{{PLACEHOLDERS}}` filled by `todos.render_page()`

## Key Conventions
- Port is hardcoded to **9990** in `app.py:21`
- Persistence: atomic write via `.tmp` rename in `todos.save()`
- IDs are monotonic (`_next_id`), never reused
- Priority values: `"low" | "medium" | "high"` (validated in `add()`)
- Due dates: ISO format (`YYYY-MM-DD`), rendered as overdue badge if past today
- HTML escaping via `html.escape()` — never trust user input

## No Tooling Configured
- No `requirements.txt`, `pyproject.toml`, or virtualenv
- No test runner, linter, or type checker
- No CI/CD

## Extending
- Add logic in `todos.py` (the "first file you will edit")
- Add routes in `app.py:do_POST`
- Modify template in `page.html`

## Data File
- `todos.json` created on first save — contains `{"next_id": N, "todos": [...]}`
- Corrupt/missing file falls back to seed data silently (stderr warning only)