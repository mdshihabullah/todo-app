## Problem Statement

The Tiny Todo application requires a comprehensive specification for enhancing the user interface with search and edit capabilities, along with code refactoring to support these features and prepare the codebase for ticket-based development. The user needs to be able to search through todo items from the UI, edit existing todo items, and have the codebase structured for future ticket-driven development via the /to-tickets skill. Currently, the application supports basic add/toggle/delete operations with priority levels, due dates, and search functionality, but the UI interactions for searching and editing need to be fully realized and the codebase needs restructuring for ticket workflow.

## Solution

The solution involves finalizing the UI components for search and edit operations that were partially implemented, ensuring all features integrate seamlessly with the existing codebase, and refactoring the code to establish clean seams for ticket-based development. The application already has backend logic for search, filter, and edit operations in todos.py and app.py, and UI elements in page.html. The spec aims to solidify these implementations, address any remaining gaps, and restructure the codebase so that future features can be broken down into tracer-bullet tickets using the /to-tickets skill. The refactoring should minimize seams across the codebase, ideally having one primary seam that separates the data layer (todos.py) from the web layer (app.py), with the template (page.html) as the rendering boundary.

## User Stories

1. As a user, I want to search for todos by typing in a search field, so that I can find specific tasks quickly
2. As a user, I want the search to be case-insensitive and match substrings within task text, so that I can find tasks even if I don't remember the exact wording
3. As a user, I want to see search results filtered in real-time as I type, so that the list narrows down to matching items
4. As a user, I want to click an edit button on any todo row, so that I can modify the task, priority, or due date
5. As a user, I want the edit form to pre-fill with the current todo values, so that I can quickly make changes without re-entering information
6. As a user, I want to submit the edit form and have the todo updated persistently, so that my changes survive server restarts
7. As a user, I want to filter the todo list by priority (Low/Medium/High/All), so that I can focus on tasks of a specific importance level
8. As a user, I want the priority filter to work in conjunction with search, so that I can narrow down by both task text and priority
9. As a user, I want the todo list to show all items when no filter or search is active, so that I don't lose track of my full workload
10. As a developer, I want the codebase structured with clear seams between the data layer, web layer, and template, so that I can break down work into independent tickets
11. As a developer, I want the todos.py data layer to expose clean functions (add, toggle, delete, edit, search, filterByPriority) that can be tested and called independently, so that the /to-tickets skill can create self-contained tickets
12. As a developer, I want the app.py web layer to have well-defined routes (/add, /toggle, /delete, /edit, /filter, /search) that accept form POST requests, so that route handlers can be ticketized
13. As a developer, I want the page.html template to have placeholders and structure that support the UI features without requiring major redesign, so that template changes are minimal and focused
14. As a developer, I want the AGENTS.md and CONTEXT.md to document the domain vocabulary and agent skills, so that future OpenCode sessions can ramp up quickly
15. As a developer, I want the JSON persistence (todos.json) to be atomic and reliable, so that tickets dealing with data persistence don't risk corrupting the store

## Implementation Decisions

- The search functionality uses a case-insensitive substring match on task text, implemented in todos.py search() and filtered further by _search_query state in rows_html()
- The edit operation uses hidden form inputs per row to pre-fill task, priority, and due_date, submitted to POST /edit which calls todos.edit() and saves persistently
- The priority filter uses a global _filter_priority state in todos.py that modifies which todos are rendered in rows_html()
- Search and filter operate independently but can be combined - _search_query and _filter_priority are checked in sequence within rows_html()
- The JSON persistence format remains {"next_id": N, "todos": [...]} with atomic write via .tmp rename, preserving the existing data layer contract
- The app.py routes maintain the same pattern: parse form data, call todos functions, then _redirect("/") to re-render the page
- The page.html template additions (search form, priority filter dropdown, edit buttons) are minimal and follow the existing styling conventions
- The code refactoring aims to have one primary seam: the boundary between todos.py (data layer) and app.py (web layer), with render_page() and rows_html() in todos.py as the rendering seam
- No new external dependencies are introduced - the application continues using stdlib only (http.server, json, html, datetime, pathlib)
- The domain vocabulary from CONTEXT.md is respected throughout: todo, task, priority, done, id, due_date, search, render, stats, add, toggle, delete, HTML escaping, JSON persistence, monotonic ID

## Testing Decisions

- Tests should focus on external behavior: the search function returns todos whose task text contains the query (case-insensitive), the edit function updates and returns the modified todo or None, filterByPriority returns matching todos or all, and rows_html respects _filter_priority and _search_query states
- The existing test pattern (from the session) validates search('Run') returns the todo with "Run" in its task, edit updates task/priority/due_date correctly, and rows_html renders the correct number of items under different filter/query combinations
- Prior art in the codebase includes the search() function tests and the toggle/add/delete flow; new tests should follow the same red-green-refactor pattern
- Modules to test: todos.search(), todos.edit(), todos.filter_by_priority(), and the rows_html() rendering logic with filter/query states
- The /to-tickets skill will create self-contained tickets where each ticket's implementation can be verified by running the existing test harness (python3 -c "import sys; sys.path.insert(0, '.'); import todos" followed by behavior verification)

## Out of Scope

- Building a full JavaScript front-end or browser-based interactivity beyond the current HTML form POST pattern
- Adding a separate test framework or test configuration (no requirements.txt, pyproject.toml, or test runner is configured)
- Changing the JSON persistence format or introducing a database migration
- Modifying the hardcoded port 9990 or the basic app.py routing structure
- Creating new HTML pages or redesigning the template layout beyond the added form elements
- Implementing user authentication, accounts, or multi-user support
- Adding undo/redo functionality for edit operations
- Supporting due dates prior to app epoch or invalid date formats beyond the basic ValueError handling

## Further Notes

- The three features (search, edit, priority filter) were already partially implemented in this session; this spec formalizes them and prepares the codebase for ticket-based development
- The CONTEXT.md domain glossary should be kept in sync with any new terms introduced
- The AGENTS.md already documents the agent skills block; future sessions should reference these files
- The transition to /to-tickets skill will break each user story into tracer-bullet tickets with blocking edges; the codebase's single seam (todos.py vs app.py boundary) will make ticket isolation feasible
- If the user wants to proceed to the /to-tickets skill, the tickets should be created with clear blocking relationships: e.g., "search UI ticket" depends on "search function exists" ticket, "edit UI ticket" depends on "edit function exists" ticket, and "refactoring ticket" depends on both and establishes the primary seam
- The spec's user stories are intentionally extensive to cover all aspects of the feature from both user and developer perspectives, ensuring the /to-tickets skill can derive meaningful, testable tickets from them