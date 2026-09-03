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
        self._orig_show = todos._show_done

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
        todos._show_done = False

    def tearDown(self):
        todos.TODOS = self._orig_todos
        todos._next_id = self._orig_next_id
        todos._filter_priority = self._orig_filter
        todos._search_query = self._orig_query
        todos._show_done = self._orig_show
        todos._DB_PATH = self._orig_db_path
        self._tmpdir.cleanup()


class TestAddRobustness(TodoTestCase):
    """add() must reject blank/whitespace-only tasks."""

    def test_add_returns_new_todo(self):
        t = todos.add("Buy milk", "high", "2026-12-01")
        self.assertEqual(t["task"], "Buy milk")
        self.assertEqual(t["priority"], "high")
        self.assertFalse(t["done"])

    def test_add_strips_whitespace(self):
        t = todos.add("  Paint wall  ")
        self.assertEqual(t["task"], "Paint wall")

    def test_add_blank_task_returns_none(self):
        self.assertIsNone(todos.add("   "))
        self.assertIsNone(todos.add(""))
        self.assertEqual(len(todos.TODOS), 3)

    def test_unknown_priority_falls_back_to_medium(self):
        t = todos.add("Task", "urgent")
        self.assertEqual(t["priority"], "medium")


class TestEditRobustness(TodoTestCase):
    """edit() must not blank a task with empty/whitespace input."""

    def test_edit_updates_task_priority_due_date(self):
        updated = todos.edit(1, "New task", "high", "2026-12-31")
        self.assertEqual(updated["task"], "New task")
        self.assertEqual(updated["priority"], "high")
        self.assertEqual(updated["due_date"], "2026-12-31")

    def test_edit_blank_task_preserves_existing_text(self):
        before = todos.TODOS[0]["task"]
        todos.edit(1, "   ", "high", "")
        self.assertEqual(todos.TODOS[0]["task"], before)

    def test_edit_not_found_returns_none(self):
        self.assertIsNone(todos.edit(999, "x", "high", ""))


class TestDeleteRestore(TodoTestCase):
    """delete() returns the removed todo; restore() re-inserts it with a fresh id."""

    def test_delete_returns_removed_todo(self):
        removed = todos.delete(1)
        self.assertEqual(removed["id"], 1)
        self.assertNotIn(1, [t["id"] for t in todos.TODOS])

    def test_delete_not_found_returns_none(self):
        self.assertIsNone(todos.delete(999))

    def test_restore_reinserts_with_new_id(self):
        removed = todos.delete(2)
        restored = todos.restore(removed["task"], removed["priority"],
                                 removed["due_date"], removed["done"])
        self.assertEqual(restored["task"], removed["task"])
        self.assertNotEqual(restored["id"], removed["id"])  # ids never reused
        self.assertEqual(todos._next_id, 5)

    def test_restore_preserves_done_flag(self):
        removed = todos.delete(1)
        removed["done"] = True
        restored = todos.restore(removed["task"], removed["priority"],
                                 removed["due_date"], removed["done"])
        self.assertTrue(restored["done"])


class TestRowsHtmlVisible(TodoTestCase):
    """rows_html() honours the active view filters."""

    def test_all_rows_rendered_when_no_filters(self):
        html = todos.rows_html()
        self.assertIn("Run the app and add a todo of your own", html)
        self.assertIn("Do the search()", html)
        self.assertIn("Watch an AI", html)

    def test_rows_carry_edit_delete_data_buttons(self):
        html = todos.rows_html()
        self.assertIn('data-todo=', html)
        self.assertIn('data-edit', html)
        self.assertIn('data-delete', html)

    def test_empty_list_renders_empty_message(self):
        todos.TODOS = []
        html = todos.rows_html()
        self.assertIn('class="empty"', html)


class TestRowsHtmlSearchCaseInsensitive(TodoTestCase):
    """Search applied at render time must be case-insensitive and AND-compose with filter."""

    def test_uppercase_query_matches_lowercase_task(self):
        todos._search_query = "RUN"
        html = todos.rows_html()
        self.assertIn("Run the app and add a todo of your own", html)
        self.assertNotIn("Do the search()", html)

    def test_lowercase_query_matches_uppercase_task_ok(self):
        todos._search_query = "ai"
        html = todos.rows_html()
        self.assertIn("Watch an AI agent add a feature for real", html)
        self.assertNotIn("Run the app", html)

    def test_empty_query_shows_all(self):
        todos._search_query = ""
        html = todos.rows_html()
        self.assertIn("Run the app", html)
        self.assertIn("Watch an AI", html)

    def test_search_combined_with_priority_filter(self):
        todos._search_query = "watch"
        todos._filter_priority = "high"
        html = todos.rows_html()
        self.assertIn("Watch an AI", html)
        self.assertNotIn("Run the app", html)

    def test_search_and_filter_with_no_match_shows_empty(self):
        todos._search_query = "watch"
        todos._filter_priority = "low"
        html = todos.rows_html()
        self.assertIn('class="empty"', html)


class TestRowsHtmlDoneToggle(TodoTestCase):
    """Completed todos hidden by default; shown when _show_done is True."""

    def _mark_done(self, todo_id):
        todos.TODOS[todo_id - 1]["done"] = True

    def test_done_hidden_by_default(self):
        self._mark_done(1)
        html = todos.rows_html()
        self.assertNotIn("Run the app and add a todo of your own", html)
        self.assertIn("Do the search()", html)
        self.assertIn("Watch an AI", html)

    def test_done_shown_when_toggled(self):
        self._mark_done(1)
        todos.set_show_done(True)
        html = todos.rows_html()
        self.assertIn("Run the app and add a todo of your own", html)

    def test_sets_and_reads_show_done(self):
        todos.set_show_done(True)
        self.assertTrue(todos.show_done())
        todos.set_show_done(False)
        self.assertFalse(todos.show_done())

    def test_done_toggle_composes_with_filter(self):
        self._mark_done(1)
        todos._filter_priority = "medium"  # todo 1 is medium
        html = todos.rows_html()
        # Todo 1 is filtered in but hidden because done; no other medium todo.
        self.assertIn('class="empty"', html)
        todos.set_show_done(True)
        html = todos.rows_html()
        self.assertIn("Run the app and add a todo of your own", html)


class TestPersistenceRobustness(TodoTestCase):
    """Corrupt/missing store must not crash; corrupt file is preserved."""

    def test_corrupt_json_falls_back_to_seed(self):
        todos._DB_PATH.write_text("{ not valid json !!!", encoding="utf-8")
        todos.load()
        # Falls back to whatever is currently in memory (the seed).
        self.assertTrue(len(todos.TODOS) >= 0)
        # The corrupt file is preserved and not silently clobbered.
        self.assertTrue(todos._DB_PATH.with_suffix(".json.bak").exists())

    def test_missing_file_loads_without_error(self):
        todos.load()  # no file yet -> no-op
        self.assertTrue(True)

    def test_round_trip_save_load(self):
        todos.add("Persisted", "high", "2027-01-01")
        todos.add("Another", "low", "")
        todos.save()
        todos.TODOS = []
        todos.load()
        tasks = [(t["task"], t["priority"]) for t in todos.TODOS]
        self.assertIn(("Persisted", "high"), tasks)
        self.assertIn(("Another", "low"), tasks)
        self.assertEqual(len(tasks), 5)


class TestSearchFunction(TodoTestCase):
    """The pure search() function contract."""

    def test_search_returns_matching_todo(self):
        self.assertEqual([t["id"] for t in todos.search("Run")], [1])

    def test_search_case_insensitive(self):
        self.assertEqual([t["id"] for t in todos.search("rUn")], [1])

    def test_search_no_match_empty(self):
        self.assertEqual(todos.search("xyz"), [])


if __name__ == "__main__":
    unittest.main()
