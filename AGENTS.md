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
- **app.py** — HTTP server (stdlib only), routes: `GET /|/export`, `POST /add|/toggle|/delete|/restore|/edit|/filter|/search|/toggle-done|/reset-filters|/mark-all-done|/clear-completed`
- **todos.py** — Logic + data layer (in-memory list + JSON persistence at `todos.json`)
- **page.html** — Template with `{{PLACEHOLDERS}}` filled by `todos.render_page()`
- **tests/test_todos.py** — stdlib unittest suite (50 cases) for the logic layer
- **tests/test_e2e.py** — Playwright E2E suite (29 cases) for the full UI

## Key Conventions
- Port is hardcoded to **9990** in `app.py`
- Persistence: atomic write via `.tmp` rename in `todos.save()`; corrupt `todos.json` is preserved to `todos.json.bak` on load before falling back to seed
- IDs are monotonic (`_next_id`), never reused; `restore()` re-inserts a deleted todo with a fresh id
- Priority values: `"low" | "medium" | "high"` (validated in `add()` and `edit()`)
- Beyond priority/due_date/done, todos carry two optional free-text fields: `category` (rendered as a subtle `badge-category`, filterable via `_filter_category` in `/filter`) and `description` (hidden behind a per-row `desc-toggle`, revealed in a `div.desc`)
- Bulk actions: `mark_all_done()` flips every open todo to done; `clear_completed()` drops all done todos; both exposed as buttons in the stats zone (`POST /mark-all-done|/clear-completed`) and covered by tests
- Export: `GET /export` returns all todos as an `application/json` attachment via `export_json()`
- Due dates: ISO format (`YYYY-MM-DD`), rendered as overdue badge if past today
- HTML escaping via `html.escape()` — never trust user input
- `add()` strips whitespace and is a no-op (returns `None`) for blank tasks; `edit()` preserves existing task text when given blank input
- Completed todos hidden by default via `_show_done` (default `False`); `POST /toggle-done` ON shows **all** open+done tasks (a `done` filter is applied only when OFF)
- View state is shared server-side and AND-composed in `_visible_todos()`: priority filter → category filter → case-insensitive search (`_search_query.lower()` vs lowercased task text) → done-hide; current search/filter values are fed back into the rendered inputs (`{{SEARCH_VALUE}}`, `{{SEL_*}}`, `{{CATEGORY_OPTIONS}}`) and cleared via `POST /reset-filters`
- Editing is **modal-based** (no inline-edit state): rows carry `data-todo` JSON + `data-edit`/`data-delete` buttons; delete uses fetch + toast-undo via `POST /restore`

## Testing
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```
Run this after changing logic in `todos.py` or routes in `app.py`.

### E2E (Playwright)
`tests/test_e2e.py` exercises the full UI with a headless Chromium browser. It
manages its own server lifecycle (spins up `app.py` on port 9990 and wipes
`todos.json` per test). Requires the `.venv` (with `playwright` installed):
```bash
.venv/bin/python3 -m unittest tests.test_e2e -v
```
All flows are covered: add, edit, delete+undo, toggle done, filter by
priority, search, show-completed toggle, bulk actions, export, categories,
descriptions, and filter reset. Must pass 100% before a PR is considered done.

## Tooling
- No `requirements.txt` or `pyproject.toml`; a `.venv/` (gitignored) holds the `playwright` dev dependency for E2E tests
- No CI/CD
- `.gitignore` excludes `__pycache__/`, `*.py[cod]`, `.venv/`, and the local runtime file `todos.json`

## Data File
- `todos.json` created on first save — contains `{"next_id": N, "todos": [...]}`
- Corrupt/missing file falls back to seed data silently (stderr warning only)

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
