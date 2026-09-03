"""End-to-end UI tests using Playwright against the running server.

Run:  .venv/bin/python3 -m unittest tests.test_e2e -v
      (server will be started automatically on localhost:9990)

Each test class gets its own fresh server instance (clean todos.json).
"""

import json
import os
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.request import Request

PROJECT = Path(__file__).resolve().parent.parent
BASE = "http://localhost:9990"
PYTHON = str(PROJECT / ".venv" / "bin" / "python3")
APP_PY = str(PROJECT / "app.py")

_skip_reason = None
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    _skip_reason = "playwright not installed"


def _kill_server():
    try:
        result = subprocess.run(["lsof", "-ti", ":9990"], capture_output=True, text=True)
        for pid in result.stdout.strip().splitlines():
            try:
                os.kill(int(pid), signal.SIGKILL)
            except (ProcessLookupError, ValueError):
                pass
        time.sleep(0.5)
    except Exception:
        pass


def _server_alive():
    try:
        urlopen(BASE, timeout=2)
        return True
    except Exception:
        return False


def _start_server():
    _kill_server()
    (PROJECT / "todos.json").unlink(missing_ok=True)
    proc = subprocess.Popen(
        [PYTHON, APP_PY], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    for _ in range(50):
        if _server_alive():
            return proc
        time.sleep(0.1)
    raise RuntimeError("Server did not start")


@unittest.skipIf(_skip_reason, _skip_reason or "skipped")
class E2ETestCase(unittest.TestCase):
    """Base: one Playwright browser shared, server restarted per class."""

    _server_proc = None

    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch(headless=True)
        cls._server_proc = None

    @classmethod
    def tearDownClass(cls):
        try:
            cls._browser.close()
        except Exception:
            pass
        try:
            cls._pw.stop()
        except Exception:
            pass
        if cls._server_proc:
            cls._server_proc.terminate()
            try:
                cls._server_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                cls._server_proc.kill()

    def setUp(self):
        # Fresh server + clean DB per test so no state leaks between tests
        self.__class__._server_proc = _start_server()
        self.page = self._browser.new_page()

    def tearDown(self):
        try:
            self.page.close()
        except Exception:
            pass
        if self.__class__._server_proc:
            self.__class__._server_proc.terminate()
            try:
                self.__class__._server_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.__class__._server_proc.kill()

    def _goto(self):
        self.page.goto(BASE, wait_until="networkidle")

    def _after_reload(self):
        """Wait for the JS-triggered form submission (page reload) to settle."""
        self.page.wait_for_timeout(500)
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(200)

    def _add_todo(self, task, priority="medium", due_date="", category="", description=""):
        self._goto()
        self.page.fill('input[name="task"]', task)
        if priority:
            self.page.select_option('select[name="priority"]', priority)
        if due_date:
            self.page.fill('input[name="due_date"]', due_date)
        if category:
            self.page.fill('input[name="category"]', category)
        if description:
            self.page.fill('input[name="description"]', description)
        self.page.click('button[type="submit"].btn-primary')
        self.page.wait_for_load_state("networkidle")

    def _find_todo_row(self, text):
        """Find the li row whose .task contains the given text."""
        lis = self.page.query_selector_all("li:not(.empty)")
        for li in lis:
            el = li.query_selector(".task")
            if el and text in el.inner_text():
                return li
        return None

    def _todo_texts(self):
        items = self.page.query_selector_all("li:not(.empty)")
        texts = []
        for li in items:
            el = li.query_selector(".task")
            if el:
                texts.append(el.inner_text())
        return texts

    def _todo_count(self):
        return len(self.page.query_selector_all("li:not(.empty)"))

    def _page_html(self):
        return self.page.content()

    def _toggle_show_done(self):
        """The #showDone checkbox is visually hidden (CSS opacity:0); trigger
        the switch by clicking its wrapping label, which toggles the checkbox."""
        self.page.click("label.switch")


# ── Add todo ────────────────────────────────────────────────────────
class TestAddTodo(E2ETestCase):

    def test_add_todo_appears_in_list(self):
        self._add_todo("Buy groceries")
        self.assertIn("Buy groceries", self._todo_texts())

    def test_add_todo_with_high_priority(self):
        self._add_todo("Urgent fix", priority="high")
        self.assertIn("Urgent fix", self._todo_texts())
        self.assertIn("badge-high", self._page_html())

    def test_add_empty_todo_no_effect(self):
        self._goto()
        c = self._todo_count()
        self.page.fill('input[name="task"]', "   ")
        self.page.click('button[type="submit"].btn-primary')
        self.page.wait_for_load_state("networkidle")
        self.assertEqual(self._todo_count(), c)

    def test_add_todo_with_category_and_description(self):
        self._add_todo("Design work", category="frontend", description="Create mockups")
        self.assertIn("Design work", self._todo_texts())
        self.assertIn("badge-category", self._page_html())


# ── Edit todo ───────────────────────────────────────────────────────
class TestEditTodo(E2ETestCase):

    def test_edit_todo_updates_text(self):
        self._add_todo("Old task name")
        self._goto()
        row = self._find_todo_row("Old task name")
        self.assertIsNotNone(row)
        row.query_selector("[data-edit]").click()
        self.page.wait_for_selector(".modal[open]")
        self.page.fill("#editTask", "Updated task name")
        self.page.click('#editForm button[type="submit"]')
        self.page.wait_for_load_state("networkidle")
        self.assertIn("Updated task name", self._todo_texts())

    def test_edit_todo_changes_priority(self):
        self._add_todo("Task to change", priority="low")
        self._goto()
        row = self._find_todo_row("Task to change")
        self.assertIsNotNone(row)
        row.query_selector("[data-edit]").click()
        self.page.wait_for_selector(".modal[open]")
        self.page.select_option("#editPriority", "high")
        self.page.click('#editForm button[type="submit"]')
        self.page.wait_for_load_state("networkidle")
        html = self._page_html()
        self.assertIn("badge-high", html)

    def test_edit_modal_cancels(self):
        self._add_todo("Cancel test")
        self._goto()
        row = self._find_todo_row("Cancel test")
        row.query_selector("[data-edit]").click()
        self.page.wait_for_selector(".modal[open]")
        self.page.click("#cancelEdit")
        self.page.wait_for_timeout(300)
        self.assertIsNone(self.page.query_selector(".modal[open]"))


# ── Delete todo (with undo) ────────────────────────────────────────
class TestDeleteTodo(E2ETestCase):

    def test_delete_removes_todo(self):
        self._add_todo("To be deleted")
        self._goto()
        row = self._find_todo_row("To be deleted")
        self.assertIsNotNone(row)
        row.query_selector("[data-delete]").click()
        self.page.wait_for_timeout(1000)
        self.assertNotIn("To be deleted", self._todo_texts())

    def test_delete_undo_restores_todo(self):
        self._add_todo("Undo me")
        self._goto()
        row = self._find_todo_row("Undo me")
        self.assertIsNotNone(row)
        row.query_selector("[data-delete]").click()
        self.page.wait_for_selector(".toast.show", timeout=3000)
        self.page.click("#toastUndo")
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(500)
        self.assertIn("Undo me", self._todo_texts())


# ── Toggle done ─────────────────────────────────────────────────────
class TestToggleDone(E2ETestCase):

    def test_toggle_done_marks_complete(self):
        self._add_todo("Complete me")
        self._goto()
        row = self._find_todo_row("Complete me")
        self.assertIsNotNone(row)
        row.query_selector(".tick").click()
        self.page.wait_for_load_state("networkidle")
        # Task toggled to done is hidden by default; turn on show-done to verify
        self._toggle_show_done()
        self._after_reload()
        row = self._find_todo_row("Complete me")
        self.assertIsNotNone(row)
        self.assertIn("done", row.get_attribute("class"))

    def test_toggle_done_again_unmarks(self):
        self._add_todo("Toggle twice")
        self._goto()
        row = self._find_todo_row("Toggle twice")
        self.assertIsNotNone(row)
        row.query_selector(".tick").click()
        self.page.wait_for_load_state("networkidle")
        self._toggle_show_done()
        self._after_reload()
        row = self._find_todo_row("Toggle twice")
        self.assertIsNotNone(row)
        self.assertIn("done", row.get_attribute("class"))
        # Toggle back to open
        row = self._find_todo_row("Toggle twice")
        self.assertIsNotNone(row)
        row.query_selector(".tick").click()
        self.page.wait_for_load_state("networkidle")
        row = self._find_todo_row("Toggle twice")
        self.assertIsNotNone(row)
        cls = row.get_attribute("class") or ""
        self.assertNotIn("done", cls)


# ── Filter by priority ──────────────────────────────────────────────
class TestFilterPriority(E2ETestCase):

    def test_filter_by_high_only_shows_high(self):
        self._add_todo("Low task", priority="low")
        self._add_todo("High task", priority="high")
        self._goto()
        self.page.select_option("#filterSelect", "high")
        self._after_reload()
        todos = self._todo_texts()
        self.assertTrue(any("High task" in t for t in todos))
        self.assertFalse(any("Low task" in t for t in todos))

    def test_filter_all_shows_everything(self):
        self._add_todo("Low task", priority="low")
        self._add_todo("High task", priority="high")
        self._goto()
        self.page.select_option("#filterSelect", "high")
        self._after_reload()
        self.page.select_option("#filterSelect", "")
        self._after_reload()
        todos = self._todo_texts()
        self.assertTrue(any("Low task" in t for t in todos))
        self.assertTrue(any("High task" in t for t in todos))


# ── Search ──────────────────────────────────────────────────────────
class TestSearch(E2ETestCase):

    def test_search_finds_matching_task(self):
        self._add_todo("Unique banana task")
        self._add_todo("Unrelated item")
        self._goto()
        self.page.fill("#searchBox", "banana")
        self.page.wait_for_timeout(600)
        self._after_reload()
        todos = self._todo_texts()
        self.assertTrue(any("banana" in t for t in todos))
        self.assertFalse(any("Unrelated" in t for t in todos))

    def test_search_is_case_insensitive(self):
        self._add_todo("Case insensitive Test")
        self._goto()
        self.page.fill("#searchBox", "INSENSITIVE")
        self.page.wait_for_timeout(600)
        self._after_reload()
        self.assertTrue(any("Case insensitive" in t for t in self._todo_texts()))


# ── Show completed toggle ───────────────────────────────────────────
class TestShowCompleted(E2ETestCase):

    def test_toggle_on_shows_done_tasks(self):
        self._add_todo("Will complete")
        self._goto()
        row = self._find_todo_row("Will complete")
        self.assertIsNotNone(row)
        row.query_selector(".tick").click()
        self.page.wait_for_load_state("networkidle")
        self.assertNotIn("Will complete", self._todo_texts())
        self._toggle_show_done()
        self._after_reload()
        self.assertIn("Will complete", self._todo_texts())

    def test_toggle_off_hides_done_tasks(self):
        self._add_todo("Hide me when done")
        self._goto()
        row = self._find_todo_row("Hide me when done")
        row.query_selector(".tick").click()
        self.page.wait_for_load_state("networkidle")
        self._toggle_show_done()
        self._after_reload()
        self.assertIn("Hide me when done", self._todo_texts())
        self._toggle_show_done()
        self._after_reload()
        self.assertNotIn("Hide me when done", self._todo_texts())

    def test_toggle_on_shows_all_open_and_done(self):
        self._add_todo("Open task")
        self._add_todo("Done task")
        self._goto()
        row = self._find_todo_row("Done task")
        self.assertIsNotNone(row)
        row.query_selector(".tick").click()
        self.page.wait_for_load_state("networkidle")
        self._toggle_show_done()
        self._after_reload()
        todos = self._todo_texts()
        self.assertTrue(any("Open task" in t for t in todos))
        self.assertTrue(any("Done task" in t for t in todos))


# ── Bulk actions ────────────────────────────────────────────────────
class TestBulkActions(E2ETestCase):

    def test_mark_all_done(self):
        self._add_todo("Task A")
        self._add_todo("Task B")
        self._goto()
        self.page.click('form[action="/mark-all-done"] button')
        self.page.wait_for_load_state("networkidle")
        self._toggle_show_done()
        self._after_reload()
        html = self._page_html()
        self.assertGreaterEqual(html.count('class="done"'), 2)

    def test_clear_completed_removes_done(self):
        self._add_todo("Will clear")
        self._goto()
        row = self._find_todo_row("Will clear")
        row.query_selector(".tick").click()
        self.page.wait_for_load_state("networkidle")
        self.page.click('form[action="/clear-completed"] button')
        self.page.wait_for_load_state("networkidle")
        self.assertNotIn("Will clear", self._todo_texts())

    def test_clear_completed_keeps_open(self):
        self._add_todo("Keep me open")
        self._add_todo("Will be done then cleared")
        self._goto()
        row = self._find_todo_row("Will be done then cleared")
        self.assertIsNotNone(row)
        row.query_selector(".tick").click()
        self.page.wait_for_load_state("networkidle")
        self.page.click('form[action="/clear-completed"] button')
        self.page.wait_for_load_state("networkidle")
        todos = self._todo_texts()
        self.assertTrue(any("Keep me open" in t for t in todos))
        self.assertFalse(any("Will be done then cleared" in t for t in todos))


# ── Export ───────────────────────────────────────────────────────────
class TestExport(E2ETestCase):

    def test_export_returns_json(self):
        self._add_todo("Export me", category="work", description="details")
        resp = urlopen(BASE + "/export")
        data = json.loads(resp.read())
        self.assertIsInstance(data, list)
        self.assertIn("Export me", [t["task"] for t in data])

    def test_export_includes_category_and_description(self):
        self._add_todo("Export cat task", category="billing", description="long text")
        resp = urlopen(BASE + "/export")
        data = json.loads(resp.read())
        cat_task = [t for t in data if t.get("category") == "billing"]
        self.assertEqual(len(cat_task), 1)
        self.assertEqual(cat_task[0]["description"], "long text")

    def test_export_content_disposition(self):
        self._add_todo("X")
        resp = urlopen(BASE + "/export")
        self.assertIn("todos.json", resp.headers.get("Content-Disposition", ""))


# ── Categories ──────────────────────────────────────────────────────
class TestCategories(E2ETestCase):

    def test_category_badge_shows_in_list(self):
        self._add_todo("Categorized", category="shopping")
        self._goto()
        self.assertIn("badge-category", self._page_html())
        self.assertIn("shopping", self._page_html())

    def test_category_filter(self):
        self._add_todo("Alpha task", category="alpha")
        self._add_todo("Beta task", category="beta")
        self._goto()
        self.page.select_option("#categoryFilter", "alpha")
        self._after_reload()
        todos = self._todo_texts()
        self.assertTrue(any("Alpha task" in t for t in todos))
        self.assertFalse(any("Beta task" in t for t in todos))


# ── Descriptions ────────────────────────────────────────────────────
class TestDescriptions(E2ETestCase):

    def test_description_toggle_reveals_content(self):
        self._add_todo("Has desc", description="Hidden details here")
        self._goto()
        desc = self.page.query_selector("li .desc")
        self.assertIsNotNone(desc)
        self.assertTrue(desc.get_attribute("hidden") is not None)
        toggle = self.page.query_selector("li .desc-toggle")
        self.assertIsNotNone(toggle)
        toggle.click()
        self.page.wait_for_timeout(200)
        desc = self.page.query_selector("li .desc")
        self.assertIsNone(desc.get_attribute("hidden"))
        self.assertIn("Hidden details here", desc.inner_text())

    def test_no_description_no_toggle(self):
        self._add_todo("No desc task")
        self._goto()
        row = self._find_todo_row("No desc task")
        self.assertIsNotNone(row)
        self.assertIsNone(row.query_selector(".desc-toggle"))


# ── Reset filters ───────────────────────────────────────────────────
class TestResetFilters(E2ETestCase):

    def test_clear_button_resets(self):
        self._add_todo("Visible task", priority="low")
        self._add_todo("Hidden by filter", priority="high")
        self._goto()
        self.page.select_option("#filterSelect", "high")
        self._after_reload()
        self.page.fill("#searchBox", "Hidden")
        self.page.wait_for_timeout(600)
        self._after_reload()
        self.page.click("#clearAll")
        self._after_reload()
        todos = self._todo_texts()
        self.assertTrue(any("Visible task" in t for t in todos))
        self.assertTrue(any("Hidden by filter" in t for t in todos))


if __name__ == "__main__":
    unittest.main()
