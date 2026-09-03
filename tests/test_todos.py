"""Tests for the todos data/logic layer (the agreed seam).

Run:  python3 -m unittest discover -s tests -v
"""

import os
import tempfile
import unittest
from pathlib import Path

import todos


class TodoTestCase(unittest.TestCase):
    """Isolate persistence from the real todos.json."""

    def setUp(self):
        # Point the store at a throwaway temp file so tests never touch the
        # real todos.json.
        self._tmpdir = tempfile.TemporaryDirectory()
        self._orig_db_path = todos._DB_PATH
        todos._DB_PATH = Path(self._tmpdir.name) / "todos.json"

        # Reset the in-memory state to a known seed, independent of disk.
        self._orig_todos = todos.TODOS
        self._orig_next_id = todos._next_id
        self._orig_filter = todos._filter_priority
        self._orig_query = todos._search_query
        self._orig_editing = getattr(todos, "_editing_id", None)

        todos.TODOS = [
            {"id": 1, "task": "Run the app and add a todo of your own", "done": False,
             "priority": "medium", "due_date": ""},
            {"id": 2, "task": "Do the search() exercise in this file", "done": False,
             "priority": "low", "due_date": ""},
            {"id": 3, "task": "Watch an AI agent add a feature for real", "done": False,
             "priority": "high", "due_date": ""},
        ]
        todos._next_id = 4
        todos._filter_priority = None
        todos._search_query = None
        todos._editing_id = None

    def tearDown(self):
        todos.TODOS = self._orig_todos
        todos._next_id = self._orig_next_id
        todos._filter_priority = self._orig_filter
        todos._search_query = self._orig_query
        todos._editing_id = self._orig_editing
        todos._DB_PATH = self._orig_db_path
        self._tmpdir.cleanup()


class TestRowsHtmlEditMode(TodoTestCase):
    """Clicking edit should turn only that row into an editable form."""

    def test_normal_rows_use_display_not_editable_inputs(self):
        html = todos.rows_html()
        # Display rows show the task in a read-only span, not editable fields.
        self.assertIn('<span class="task">Run the app and add a todo of your own</span>', html)
        self.assertNotIn('<input type="text"', html)
        self.assertNotIn('<select name="priority" class="edit-select"', html)
        self.assertNotIn("input-edit-task", html)

    def test_editing_row_renders_editable_task_input_prefilled(self):
        todos._editing_id = 1
        html = todos.rows_html()
        # The editing row has an editable text input pre-filled with the task.
        self.assertIn('<input type="text" name="task" value="Run the app and add a todo of your own"', html)
        self.assertIn("edit-select", html)          # priority dropdown present
        self.assertIn('name="due_date"', html)       # due date field present
        self.assertNotIn('<span class="task">Run the app', html)  # not stuck in display mode

    def test_only_the_editing_row_is_editable(self):
        todos._editing_id = 2
        html = todos.rows_html()
        # Todo 2's row is editable.
        self.assertIn('<input type="text" name="task" value="Do the search() exercise in this file"', html)
        # Todo 1 and 3 rows remain display rows.
        self.assertIn('<span class="task">Run the app and add a todo of your own</span>', html)
        self.assertIn('<span class="task">Watch an AI agent add a feature for real</span>', html)
        # Only ONE editable task input exists in the whole list.
        self.assertEqual(html.count('class="edit-select"'), 1)

    def test_editing_row_submits_to_edit_route(self):
        todos._editing_id = 1
        html = todos.rows_html()
        self.assertIn('action="/edit"', html)

    def test_edit_form_submits_id_and_task_priority_due_date(self):
        # The /edit route reads id, task, priority, due_date — all must appear.
        todos._editing_id = 1
        html = todos.rows_html()
        self.assertIn('name="id"', html)
        self.assertIn('name="task"', html)
        self.assertIn('name="priority"', html)
        self.assertIn('name="due_date"', html)

    def test_cancel_surfaces_cancel_button_and_exits_edit_mode(self):
        todos._editing_id = 1
        html = todos.rows_html()
        self.assertIn('value="cancel"', html)  # cancel button present
        # After cancel clears editing, rows go back to display mode.
        todos._editing_id = None
        html2 = todos.rows_html()
        self.assertNotIn("edit-select", html2)
        self.assertIn('<span class="task">Run the app and add a todo of your own</span>', html2)


class TestRowsHtmlSearchCaseInsensitive(TodoTestCase):
    """Search applied at render time must be case-insensitive."""

    def test_uppercase_query_matches_lowercase_task(self):
        todos._search_query = "RUN"
        html = todos.rows_html()
        self.assertIn("Run the app and add a todo of your own", html)
        self.assertNotIn("Do the search()", html)
        self.assertNotIn("Watch an AI", html)

    def test_lowercase_query_matches_uppercase_task_ok(self):
        todos._search_query = "ai"
        html = todos.rows_html()
        self.assertIn("Watch an AI agent add a feature for real", html)
        self.assertNotIn("Run the app", html)

    def test_empty_query_shows_all(self):
        todos._search_query = ""
        html = todos.rows_html()
        self.assertIn("Run the app", html)
        self.assertIn("Do the search()", html)
        self.assertIn("Watch an AI", html)

    def test_substring_match(self):
        todos._search_query = "search()"
        html = todos.rows_html()
        self.assertIn("Do the search()", html)
        self.assertNotIn("Run the app", html)

    def test_search_combined_with_priority_filter(self):
        # Todo 1 = medium "Run...", Todo 2 = low "Do the search...",
        # Todo 3 = high "Watch an AI...". Search "watch" + filter high => only todo 3.
        todos._search_query = "watch"
        todos._filter_priority = "high"
        html = todos.rows_html()
        self.assertIn("Watch an AI", html)
        self.assertNotIn("Run the app", html)
        self.assertNotIn("Do the search()", html)

    def test_search_with_filter_high_and_no_query_match(self):
        todos._search_query = "watch"
        todos._filter_priority = "low"
        html = todos.rows_html()
        # A low-priority todo doesn't match "watch", so nothing renders.
        self.assertIn('class="empty"', html)


class TestSearchFunction(TodoTestCase):
    """The pure search() function contract."""

    def test_search_returns_matching_todo(self):
        self.assertEqual([t["id"] for t in todos.search("Run")], [1])

    def test_search_case_insensitive(self):
        self.assertEqual([t["id"] for t in todos.search("rUn")], [1])

    def test_search_no_match_empty(self):
        self.assertEqual(todos.search("xyz"), [])


class TestEditFunction(TodoTestCase):
    """The edit() function contract."""

    def test_edit_updates_task_priority_due_date(self):
        updated = todos.edit(1, "New task", "high", "2026-12-31")
        self.assertEqual(updated["task"], "New task")
        self.assertEqual(updated["priority"], "high")
        self.assertEqual(updated["due_date"], "2026-12-31")

    def test_edit_not_found_returns_none(self):
        self.assertIsNone(todos.edit(999, "x", "high", ""))


class TestEditModeState(TodoTestCase):
    """set_editing / clear_editing drive whether a row is editable."""

    def test_set_editing_marks_one_todo(self):
        todos.set_editing(2)
        self.assertEqual(todos._editing_id, 2)

    def test_clear_editing_resets_to_none(self):
        todos.set_editing(2)
        todos.clear_editing()
        self.assertIsNone(todos._editing_id)

    def test_display_rows_edit_button_targets_start_route(self):
        html = todos.rows_html()
        self.assertIn('formaction="/edit/start"', html)


class TestEditPersists(TodoTestCase):
    """Saving an inline edit updates the stored todo.

    Uses the real save()/load() round-trip via a temp store.
    """

    def test_saved_edit_survives_reload(self):
        todos.clear_editing()
        todos.edit(1, "Persisted change", "high", "2027-01-01")
        todos.save()
        self.assertEqual(todos.TODOS[0]["task"], "Persisted change")
        self.assertEqual(todos.TODOS[0]["priority"], "high")


if __name__ == "__main__":
    unittest.main()
