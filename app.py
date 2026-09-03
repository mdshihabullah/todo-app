"""Tiny Todo — the web layer (routing + HTTP).

Run:
    python3 app.py
    open http://localhost:9990

Routes:
    GET  /          the page
    GET  /export    download all todos as JSON
    POST /add       add a todo       (form fields: task, priority, due_date, category, description)
    POST /toggle    flip done        (form field: id)
    POST /delete    remove a todo    (form field: id)
    POST /restore   re-insert a deleted todo (form fields: task, priority, due_date, done, category, description)
    POST /edit      edit a todo      (form fields: id, task, priority, due_date, category, description)
    POST /filter    filter by priority + category (form fields: priority, category)
    POST /search    search todos       (form field: query)
    POST /toggle-done  show/hide completed todos (form field: show_done)
    POST /reset-filters  clear the active search + priority/category filter
    POST /mark-all-done  mark every todo as done
    POST /clear-completed remove all completed todos

The logic lives in todos.py — that's the file you'll grow first.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

import todos

PORT = 9990


class TodoHandler(BaseHTTPRequestHandler):
    def _page(self):
        body = todos.render_page().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, to="/"):
        self.send_response(303)  # "see other" — browser follows back to the page
        self.send_header("Location", to)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _form(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        data = self.rfile.read(length).decode("utf-8")
        return parse_qs(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._page()
        elif self.path == "/export":
            self._export()
        else:
            self.send_error(404, "No such page")

    def _export(self):
        body = todos.export_json().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="todos.json"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        form = self._form()
        if self.path == "/add":
            task = form.get("task", [""])[0].strip()
            priority = form.get("priority", ["medium"])[0].strip().lower()
            due_date = form.get("due_date", [""])[0].strip()
            category = form.get("category", [""])[0].strip()
            description = form.get("description", [""])[0].strip()
            todos.add(task, priority, due_date, category, description)
            self._redirect()
        elif self.path == "/toggle":
            todos.toggle(int(form.get("id", ["0"])[0]))
            self._redirect()
        elif self.path == "/delete":
            todos.delete(int(form.get("id", ["0"])[0]))
            self._redirect()
        elif self.path == "/restore":
            task = form.get("task", [""])[0].strip()
            priority = form.get("priority", ["medium"])[0].strip().lower()
            due_date = form.get("due_date", [""])[0].strip()
            done = form.get("done", [""])[0].strip().lower() in ("1", "true", "on")
            category = form.get("category", [""])[0].strip()
            description = form.get("description", [""])[0].strip()
            todos.restore(task, priority, due_date, done, category, description)
            self._redirect()
        elif self.path == "/edit":
            todo_id = int(form.get("id", ["0"])[0])
            task = form.get("task", [""])[0].strip()
            priority = form.get("priority", ["medium"])[0].strip().lower()
            due_date = form.get("due_date", [""])[0].strip()
            category = form.get("category", [""])[0].strip()
            description = form.get("description", [""])[0].strip()
            todos.edit(todo_id, task, priority, due_date, category, description)
            self._redirect()
        elif self.path == "/filter":
            priority = form.get("priority", [""])[0].strip().lower()
            category = form.get("category", [""])[0].strip()
            todos._filter_priority = priority if priority else None
            todos._filter_category = category if category else None
            self._redirect("/")
        elif self.path == "/search":
            query = form.get("query", [""])[0].strip()
            todos._search_query = query if query else None
            self._redirect("/")
        elif self.path == "/toggle-done":
            form_value = form.get("show_done", [""])[0].strip().lower()
            todos.set_show_done(form_value in ("1", "true", "on"))
            self._redirect("/")
        elif self.path == "/reset-filters":
            todos._search_query = None
            todos._filter_priority = None
            todos._filter_category = None
            self._redirect("/")
        elif self.path == "/mark-all-done":
            todos.mark_all_done()
            self._redirect("/")
        elif self.path == "/clear-completed":
            todos.clear_completed()
            self._redirect("/")
        else:
            self.send_error(404)

if __name__ == "__main__":
    print(f"Tiny Todo running at http://localhost:{PORT}  (Ctrl+C to stop)")
    HTTPServer(("", PORT), TodoHandler).serve_forever()
