# Tiny Todo — Domain Glossary

This `CONTEXT.md` contains the domain vocabulary for the Tiny Todo application. It is **totally devoid of implementation details** — no code, no file paths, no framework specifics. It is only terms, definitions, and design decisions.

---

## Terms

| Term | Definition |
|------|-----------|
| **todo** | A single task item with an ID, task text, priority, due date, and done flag |
| **task** | The description of what needs to be done (user-facing string) |
| **priority** | The importance level of a todo: `"low" | "medium" | "high"` |
| **done** | A boolean flag indicating whether the todo has been completed |
| **id** | A monotonic, never-reused integer identifier for each todo |
| **due_date** | An optional ISO-format date (`YYYY-MM-DD`); if past today and not done, renders an "overdue" badge |
| **search** | Case-insensitive substring match on task text; returns matching todos |
| **render** | Filling `page.html`'s placeholders (`{{TODO_ROWS}}`, `{{STAT_TOTAL}}`, `{{STAT_OPEN}}`, `{{STAT_DONE}}`) with live todo data |
| **stats** | The triple `(total, open, done)` — total count of todos, number not done, number done |
| **add** | Function that creates a new todo with given task, priority, and due_date; validates priority is one of low/medium/high |
| **toggle** | Function that flips the `done` flag of the todo with the given id |
| **delete** | Function that removes the todo with the given id from the list |
| **edit** | Function that updates a todo's task text, priority, and due date; exposed in the UI as an inline per-row edit form |
| **HTML escaping** | All user-facing output uses `html.escape()` — user input is never trusted in HTML |
| **JSON persistence** | Todos are saved to `todos.json` via atomic write (`.tmp` rename); the file contains `{"next_id": N, "todos": [...]}` |
| **monotonic ID** | `_next_id` only ever increases; deleted IDs are never reused |

---

## Design decisions

- **Priority values** are constrained to `"low" | "medium" | "high"` — validated in `add()`, default is `"medium"`
- **IDs are monotonic** — `_next_id` starts at 4 and only goes up; deleted IDs are never reused
- **Due dates** in ISO format (`YYYY-MM-DD`) are rendered as an "overdue" badge when the date is past today and the todo is not done
- **HTML escaping** via `html.escape()` is applied everywhere user-facing text appears — never trust user input
- **Editing** is a per-row state: at most one todo is in edit mode at a time, rendered as an inline form pre-filled with its current values; saving posts to `/edit` and persists via `save()`
- **Persistence** uses `todos.json` created on first save; corrupt/missing files fall back silently to the in-memory seed data
- **One todo per id** — ids are unique within the system

---

## Open questions / decisions awaiting resolution

- Should the app support editing existing todos' task text, priority, and due date? (Resolved: yes, via an inline edit form triggered by the ✎ button; editing is a per-row state)
- Should todos support due dates with overdue badging? (Already implemented)
- Should search be case-insensitive? (Already implemented)
- Should search match substrings? (Already implemented)
- How should the UI handle showing/hiding completed todos?
- How should multiple rows be prevented from being edited at once? (Resolved: only one row can be in edit mode at a time via a single `_editing_id`)

---

**Reference:** See `docs/agents/domain.md` for the single-context layout and ADR conventions.