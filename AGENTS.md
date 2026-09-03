# Tiny Todo — Agent Guide

## Agent skills

### Issue tracker

GitHub. Triage uses the skill in `.agents/skills/triage/` and the label mapping in
`.agents/skills/setup-matt-pocock-skills/triage-labels.md`
(`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`).

Current tracker state: **all issues resolved and closed** — spec #1 closes out with
sub-issues #10–#17 (linked as real GitHub sub-issues) plus follow-ups #18/#19.

### Domain docs

single-context. See `docs/agents/domain.md`.

## Quick Start
```bash
python3 app.py
# Open http://localhost:9990
```

## Architecture
- **app.py** — HTTP server (stdlib only), routes: `GET /`, `POST /add|/toggle|/delete|/edit|/edit/start|/edit/cancel|/filter|/search`
- **todos.py** — Logic + data layer (in-memory list + JSON persistence at `todos.json`)
- **page.html** — Template with `{{PLACEHOLDERS}}` filled by `todos.render_page()`
- **tests/test_todos.py** — stdlib unittest suite (21 cases) for the logic layer

## Key Conventions
- Port is hardcoded to **9990** in `app.py`
- Persistence: atomic write via `.tmp` rename in `todos.save()`
- IDs are monotonic (`_next_id`), never reused
- Priority values: `"low" | "medium" | "high"` (validated in `add()` and `edit()`)
- Due dates: ISO format (`YYYY-MM-DD`), rendered as overdue badge if past today
- HTML escaping via `html.escape()` — never trust user input
- Search is **case-insensitive**: `rows_html()` compares `_search_query.lower()` against lowercased task text; composes with the priority filter (filter first, then search)
- Edit uses `_editing_id` state + `_display_row_html`/`_edit_row_html`/`_badges_html` helpers; only one row editable at a time; save posts to `POST /edit` (fields `id`, `task`, `priority`, `due_date`)

## Testing
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```
Run this after changing logic in `todos.py` or routes in `app.py`. UI flows are additionally verified with Playwright against the running server.

## Tooling
- No `requirements.txt`, `pyproject.toml`, or virtualenv
- No CI/CD
- `.gitignore` excludes `__pycache__/`, `*.py[cod]`, and the local runtime file `todos.json`

## Data File
- `todos.json` created on first save — contains `{"next_id": N, "todos": [...]}`
- Corrupt/missing file falls back to seed data silently (stderr warning only)