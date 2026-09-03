"""Tiny Todo — the data and logic layer.

The web layer (app.py) calls these functions. The page (page.html) is
rendered by render_page() below.
"""

import html
import json
import sys
from datetime import date
from pathlib import Path

# Persistent store so todos (and their due-dates) survive a server restart.
_DB_PATH = Path(__file__).parent / "todos.json"

# The whole "database" — a plain list of dicts, lost on restart
# (that restart problem becomes an exercise at the end of the session).
TODOS = [
    {"id": 1, "task": "Run the app and add a todo of your own", "done": False, "priority": "medium"},
    {"id": 2, "task": "Do the search() exercise in this file", "done": False, "priority": "low"},
    {"id": 3, "task": "Watch an AI agent add a feature for real", "done": False, "priority": "high"},
]

_next_id = 4  # ids only go up, never reused
_filter_priority = None  # None means show all
_filter_category = None  # None means show all
_search_query = None  # None means show all
_show_done = False  # completed todos hidden by default; toggle to reveal


def _seed_next_id():
    """Ensure _next_id is greater than every existing todo id."""
    global _next_id
    if TODOS:
        _next_id = max(t["id"] for t in TODOS) + 1


def save():
    """Atomically write the current todos (and next id) to the JSON store."""
    tmp = _DB_PATH.with_suffix(_DB_PATH.suffix + ".tmp")
    payload = {"next_id": _next_id, "todos": TODOS}
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(_DB_PATH)  # atomic rename on the same filesystem


def load():
    """Load todos from JSON if present.

    On a missing or corrupt file we warn on stderr and fall back to the
    in-memory seeds already defined above, so the app stays up.
    """
    global TODOS, _next_id
    if not _DB_PATH.exists():
        return
    try:
        data = json.loads(_DB_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        # Never silently destroy the user's data: preserve the corrupt file
        # (once) beside the store, then fall back to seed so the app stays up.
        print(f"[todos] WARNING: could not load {_DB_PATH.name}: {exc!r}",
              file=sys.stderr)
        if not _DB_PATH.with_suffix(_DB_PATH.suffix + ".bak").exists():
            try:
                bak = _DB_PATH.with_suffix(_DB_PATH.suffix + ".bak")
                _DB_PATH.replace(bak)
                print(f"[todos] preserved corrupt file as {bak.name}", file=sys.stderr)
            except OSError:
                pass
        return
    loaded = data.get("todos", []) if isinstance(data, dict) else []
    TODOS = [t for t in loaded if isinstance(t, dict) and "id" in t]
    if isinstance(data, dict) and "next_id" in data:
        _next_id = data["next_id"]
    else:
        _seed_next_id()


def add(task, priority="medium", due_date="", category="", description=""):
    """Add a new todo (string). Returns the new todo dict, or None if the
    task is empty/whitespace-only (robust: nothing is added)."""
    global _next_id
    task = (task or "").strip()
    if not task:
        return None
    if priority not in ("low", "medium", "high"):
        priority = "medium"
    todo = {
        "id": _next_id,
        "task": task,
        "done": False,
        "priority": priority,
        "due_date": due_date or "",
        "category": (category or "").strip(),
        "description": (description or "").strip(),
    }
    TODOS.append(todo)
    _next_id += 1
    save()
    return todo


def toggle(todo_id):
    """Flip the done flag of the todo with this id. Returns it, or None."""
    for todo in TODOS:
        if todo["id"] == todo_id:
            todo["done"] = not todo["done"]
            save()
            return todo
    return None

def delete(todo_id):
    """Remove the todo with this id. Returns the removed todo dict (for undo),
    or None if it wasn't found."""
    global TODOS
    removed = None
    for t in TODOS:
        if t["id"] == todo_id:
            removed = t
            break
    if removed is not None:
        TODOS = [t for t in TODOS if t["id"] != todo_id]
        save()
    return removed


def restore(task, priority="medium", due_date="", done=False, category="", description=""):
    """Re-insert a previously deleted todo. IDs are monotonic and never reused,
    so a restored todo gets a fresh id (the original is gone for good)."""
    global _next_id
    task = (task or "").strip()
    if not task:
        return None
    if priority not in ("low", "medium", "high"):
        priority = "medium"
    todo = {
        "id": _next_id,
        "task": task,
        "done": done,
        "priority": priority,
        "due_date": due_date or "",
        "category": (category or "").strip(),
        "description": (description or "").strip(),
    }
    TODOS.append(todo)
    _next_id += 1
    save()
    return todo


def edit(todo_id, task, priority, due_date, category="", description=""):
    """Edit the todo with this id.

    A blank/whitespace task preserves the existing text rather than wiping it
    (robust against accidental clearing). Returns the updated todo dict, or
    None if not found.
    """
    global TODOS
    if priority not in ("low", "medium", "high"):
        priority = "medium"
    new_task = (task or "").strip()
    for todo in TODOS:
        if todo["id"] == todo_id:
            if new_task:
                todo["task"] = new_task
            todo["priority"] = priority
            todo["due_date"] = due_date or ""
            todo["category"] = (category or "").strip()
            todo["description"] = (description or "").strip()
            save()
            return todo
    return None


def filter_by_priority(priority):
    """Return todos matching this priority.

    If priority is empty, returns all todos.
    """
    if not priority:
        return TODOS
    return [t for t in TODOS if t.get("priority") == priority]


def set_show_done(show):
    """Control whether completed todos are rendered (view filter)."""
    global _show_done
    _show_done = bool(show)


def show_done():
    """Return whether completed todos are currently shown."""
    return _show_done


def stats():
    """Return (total, open, done)."""
    done = sum(1 for t in TODOS if t["done"])
    return (len(TODOS), len(TODOS) - done, done)


def mark_all_done():
    """Mark every todo as done. Returns the number of todos updated."""
    updated = 0
    for t in TODOS:
        if not t["done"]:
            t["done"] = True
            updated += 1
    if updated:
        save()
    return updated


def clear_completed():
    """Remove all completed todos. Returns the number removed."""
    global TODOS
    keep = [t for t in TODOS if not t["done"]]
    removed = len(TODOS) - len(keep)
    TODOS = keep
    if removed:
        save()
    return removed


def export_json():
    """Return all todos as a JSON export payload (list of todo dicts)."""
    return json.dumps(TODOS, indent=2, ensure_ascii=False)


# --- rendering -----------------------------------------------------------

load()  # hydrate from disk (falls back to seeds on first run)

def _visible_todos():
    """Apply the active view filters in order: priority, then category, then
    search, then the completed/hidden-by-default toggle. Filters AND-compose,
    and the completed toggle is a separate view concern layered on top."""
    todos_list = TODOS
    if _filter_priority:
        todos_list = [t for t in todos_list if t.get("priority") == _filter_priority]
    if _filter_category:
        c = _filter_category.lower()
        todos_list = [t for t in todos_list if c == (t.get("category") or "").lower()]
    if _search_query:
        q = _search_query.lower()
        todos_list = [t for t in todos_list if q in t["task"].lower()]
    if not _show_done:
        todos_list = [t for t in todos_list if not t.get("done")]
    return todos_list


def rows_html():
    """Render the visible todo list as <li> rows for edit/delete via modal + toast."""
    out = []
    today = date.today()
    for t in _visible_todos():
        out.append(_display_row_html(t, today))
    if not out:
        return '<li class="empty">Nothing here — add something.</li>'
    return "\n        ".join(out)


def _display_row_html(t, today):
    """Render a todo row. Data attributes drive the modal edit and the delete
    toast-undo in the browser; no server-side inline-edit state is needed."""
    task = html.escape(t["task"])  # never trust user input in HTML
    priority = html.escape(t.get("priority", "medium"))
    cls = ' class="done"' if t["done"] else ""
    tick = "&#8635;" if t["done"] else "&#10003;"  # ↺ : ✓
    badges = _badges_html(t, today, priority)
    desc = html.escape(t.get("description", ""))
    data = html.escape(
        json.dumps({
            "id": t["id"], "task": t["task"], "priority": t.get("priority", "medium"),
            "due_date": t.get("due_date", ""),
            "category": t.get("category", ""),
            "description": t.get("description", ""),
        }), quote=True
    )
    desc_html = (
        f'<div class="desc" hidden>{desc}</div>'
        if t.get("description")
        else ""
    )
    desc_toggle = (
        '<button class="desc-toggle" type="button" title="Show description" '
        'aria-label="Toggle description">&#8943;</button>'
        if t.get("description")
        else ""
    )
    return (
        f'<li{cls} data-todo="{data}">'
        f'<form method="post" action="/toggle" class="row">'
        f'<input type="hidden" name="id" value="{t["id"]}">'
        f'<button class="tick" title="toggle">{tick}</button>'
        f'<span class="task">{task}</span>'
        f'{badges}'
        f'{desc_toggle}'
        f'<button class="edit" type="button" title="edit" data-edit aria-label="Edit">✎</button>'
        f'<button class="del" type="button" title="delete" data-delete aria-label="Delete">&#10005;</button>'
        f'</form>{desc_html}</li>'
    )


def _badges_html(t, today, priority):
    """Build the category/priority/overdue badge markup for a todo."""
    badges = ""
    category = (t.get("category") or "").strip()
    if category:
        badges += f'<span class="badge badge-category">{html.escape(category)}</span> '
    badges += f'<span class="badge badge-{priority}">{priority}</span>'
    due_date = t.get("due_date", "")
    if not t["done"] and due_date:
        try:
            if date.fromisoformat(due_date) < today:
                badges += (
                    ' <span class="badge badge-overdue">overdue</span>'
                )
        except ValueError:
            pass
    return badges


def render_page():
    """Fill page.html's placeholders with live todos."""
    page = (Path(__file__).parent / "page.html").read_text(encoding="utf-8")
    total, open_n, done = stats()
    search_value = html.escape(_search_query or "", quote=True)
    fp = _filter_priority or ""
    fc = _filter_category or ""
    search_active = "is-active" if _search_query else ""
    sel_low = " selected" if fp == "low" else ""
    sel_med = " selected" if fp == "medium" else ""
    sel_high = " selected" if fp == "high" else ""

    cats = sorted({(t.get("category") or "").strip() for t in TODOS if (t.get("category") or "").strip()})
    category_options = ""
    for c in cats:
        selected = " selected" if c.lower() == fc.lower() else ""
        category_options += f'<option value="{html.escape(c, quote=True)}"{selected}>{html.escape(c)}</option>'

    return (
        page
        .replace("{{TODO_ROWS}}", rows_html())
        .replace("{{STAT_TOTAL}}", str(total))
        .replace("{{STAT_OPEN}}", str(open_n))
        .replace("{{STAT_DONE}}", str(done))
        .replace("{{SHOW_DONE}}", "checked" if _show_done else "")
        .replace("{{SEARCH_VALUE}}", search_value)
        .replace("{{SEARCH_ACTIVE}}", search_active)
        .replace("{{SEL_LOW}}", sel_low)
        .replace("{{SEL_MED}}", sel_med)
        .replace("{{SEL_HIGH}}", sel_high)
        .replace("{{CATEGORY_OPTIONS}}", category_options)
    )
def search(query):
    """Return todos whose task text contains `query`, case-insensitive."""
    query = query.lower()
    return [t for t in TODOS if query in t["task"].lower()]