"""Tiny Todo — the data and logic layer.

The web layer (app.py) calls these functions. The page (page.html) is
rendered by render_page() below.

>>> This is the first file you will edit: the search() exercise. <<<
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
_search_query = None  # None means show all


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
        print(f"[todos] WARNING: could not load {_DB_PATH.name}: {exc!r}",
              file=sys.stderr)
        return
    loaded = data.get("todos", []) if isinstance(data, dict) else []
    TODOS = [t for t in loaded if isinstance(t, dict) and "id" in t]
    if isinstance(data, dict) and "next_id" in data:
        _next_id = data["next_id"]
    else:
        _seed_next_id()


def add(task, priority="medium", due_date=""):
    """Add a new todo (string). Returns the new todo dict."""
    global _next_id
    if priority not in ("low", "medium", "high"):
        priority = "medium"
    todo = {
        "id": _next_id,
        "task": task,
        "done": False,
        "priority": priority,
        "due_date": due_date or "",
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
    """Remove the todo with this id."""
    global TODOS
    TODOS = [t for t in TODOS if t["id"] != todo_id]
    save()



def edit(todo_id, task, priority, due_date):
    """Edit the todo with this id.

    Returns the updated todo dict, or None if not found.
    """
    global TODOS
    if priority not in ("low", "medium", "high"):
        priority = "medium"
    for todo in TODOS:
        if todo["id"] == todo_id:
            todo["task"] = task
            todo["priority"] = priority
            todo["due_date"] = due_date or ""
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


def stats():
    """Return (total, open, done)."""
    done = sum(1 for t in TODOS if t["done"])
    return (len(TODOS), len(TODOS) - done, done)


# --- rendering -----------------------------------------------------------

load()  # hydrate from disk (falls back to seeds on first run)

def rows_html():
    """Render the todo list as <li> rows with toggle, delete, and edit buttons."""
    out = []
    today = date.today()
    todos_list = TODOS
    if _filter_priority:
        todos_list = [t for t in TODOS if t.get("priority") == _filter_priority]
    if _search_query:
        todos_list = [t for t in todos_list if _search_query in t["task"].lower()]
    for t in todos_list:
        task = html.escape(t["task"])  # never trust user input in HTML
        priority = html.escape(t.get("priority", "medium"))
        cls = ' class="done"' if t["done"] else ""
        tick = "&#8635;" if t["done"] else "&#10003;"  # ↺ : ✓
        badges = f'<span class="badge badge-{priority}">{priority}</span>'
        due_date = t.get("due_date", "")
        if not t["done"] and due_date:
            try:
                if date.fromisoformat(due_date) < today:
                    badges += (
                        ' <span class="badge badge-overdue">overdue</span>'
                    )
            except ValueError:
                pass
        out.append(
            f'<li{cls}>'
            f'<form method="post" action="/toggle" class="row">'
            f'<input type="hidden" name="id" value="{t["id"]}">'
            f'<input type="hidden" name="edit_task" value="{t["task"]}">'
            f'<input type="hidden" name="edit_priority" value="{t["priority"]}">'
            f'<input type="hidden" name="edit_due_date" value="{due_date}">'
            f'<button class="tick" title="toggle">{tick}</button>'
            f'<span class="task">{task}</span>'
            f'{badges}'
            f'<button class="edit" type="submit" name="action" value="edit" title="edit" formaction="/edit">✎</button>'
            f'<button class="del" formaction="/delete" title="delete">&#10005;</button>'
            f'</form></li>'
        )
    return "\n        ".join(out) or '<li class="empty">Nothing here — add something.</li>'


def render_page():
    """Fill page.html's placeholders with live todos."""
    page = (Path(__file__).parent / "page.html").read_text(encoding="utf-8")
    total, open_n, done = stats()
    return (
        page
        .replace("{{TODO_ROWS}}", rows_html())
        .replace("{{STAT_TOTAL}}", str(total))
        .replace("{{STAT_OPEN}}", str(open_n))
        .replace("{{STAT_DONE}}", str(done))
    )
def search(query):
    """Return todos whose task text contains `query`, case-insensitive."""
    query = query.lower()
    return [t for t in TODOS if query in t["task"].lower()]