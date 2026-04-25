# AISA Spring 26 — Internal System

An LLM benchmark that tests whether AI agents can handle **time complexity** through realistic email-thread scenarios. The agent reads a scenario's emails, then uses the tool APIs (Todos, Calendars, Emails) to complete the tasks described in those threads.

The benchmark now ships with an **MCP server** — agents call the API as MCP tools directly from Claude Code or any compatible harness. See `MCP.md` for setup.

---

## What Changed (Last Session)

- **`scenario_id` is now required on every write.** Every `POST /todos/`, `POST /calendars/{id}/events`, and `POST /emails/` must include a `scenario_id` that already exists in the store. The server returns `404` otherwise. This is the single biggest behavioral change.
- **Email API is read/write only.** There is no `DELETE /emails/{id}`. The old README listed one — it does not exist.
- **Todo updates are `PATCH`, not `PUT`.** `PATCH /todos/{id}` is a partial update; omitted fields stay unchanged. `scenario_id` and `calendar_event_id` are immutable after creation.
- **Calendar event updates are full replace.** `PUT /calendars/{id}/events/{event_id}` requires all fields, including `scenario_id`.
- **Todos can link to calendar events.** `POST /todos/` accepts an optional `calendar_event_id`; the server validates the event exists. Create the event first, then the todo.
- **Package manager is `uv`.** No more `pip` or `venv` — use `uv sync`, `uv run`, `uv add`.
- **MCP server added** (`mcp_server/`). Exposes all 22 API routes as tools. `.mcp.json` in the repo root wires it up automatically in Claude Code.

For the full, agent-facing API contract see **`docs/api_reference.md`**.

---

## Project Structure

```
.
├── app/
│   ├── main.py           # FastAPI app, error handlers, health check
│   ├── store.py          # In-memory store (resets on restart)
│   ├── models/
│   │   ├── todo.py       # TodoCreate, TodoUpdate, TodoResponse
│   │   ├── calendar.py   # CalendarCreate, CalendarResponse, EventCreate, EventResponse
│   │   └── email.py      # Email, Scenario
│   └── routers/
│       ├── todos.py
│       ├── calendar.py
│       ├── emails.py
│       └── scenarios.py
├── mcp_server/           # MCP wrapper — thin HTTP clients over FastAPI
├── docs/
│   └── api_reference.md  # Authoritative agent-facing reference
├── tests/
│   ├── test_todos.py     # 18 tests
│   ├── test_calendars.py # 22 tests
│   ├── test_emails.py    # 8 tests
│   └── test_scenarios.py # 18 tests
├── .mcp.json             # Auto-registers MCP server in Claude Code
├── MCP.md                # MCP setup and usage guide
└── pyproject.toml
```

---

## Setup

```bash
uv sync
```

That's it. No manual `venv` creation, no `pip install`.

---

## Running

**1. Start FastAPI** (required — keep this running the whole time):

```bash
uv run uvicorn app.main:app --reload
```

Server starts at `http://127.0.0.1:8000`. Swagger UI at `/docs`, ReDoc at `/redoc`.

**2. The MCP server** starts automatically via `.mcp.json` when you open Claude Code in this repo. Verify with:

```bash
claude mcp list
# aisa: bash -c uv run python -m mcp_server  ✓ Connected
```

See `MCP.md` for non-Claude-Code clients (MCP Inspector, Claude Desktop, custom harnesses).

---

## Running Tests

```bash
uv run pytest tests/ -v
```

Expected: **66 passed**.

| File | Tests |
|------|-------|
| `test_todos.py` | 18 |
| `test_calendars.py` | 22 |
| `test_emails.py` | 8 |
| `test_scenarios.py` | 18 |

---

## Core Concepts

### `scenario_id` threads through every write

Every object the agent creates must be tagged with a `scenario_id`. The server validates the scenario exists and returns `404` if it doesn't. Load a scenario first via `POST /scenarios/` before calling any create endpoint.

```
POST /scenarios/  →  POST /emails/
                      POST /calendars/{id}/events
                      POST /todos/
```

### Linking todos to calendar events

When a task requires both a calendar event and a todo:

1. `POST /calendars/{calendar_id}/events` — get back `event_id`
2. `POST /todos/` with `calendar_event_id` set to that `event_id`

Order matters — the server validates `calendar_event_id` exists at todo creation time.

### In-memory store

All data resets when uvicorn restarts. Every benchmark run starts clean. This is intentional.

---

## API Surface

Full reference with request/response shapes, error codes, and examples: **`docs/api_reference.md`**.

Quick endpoint map:

| Group | Method | Path |
|-------|--------|------|
| Health | `GET` | `/` |
| Todos | `POST` | `/todos/` |
| | `GET` | `/todos/` |
| | `GET` | `/todos/{id}` |
| | `PATCH` | `/todos/{id}` ← partial update |
| | `DELETE` | `/todos/{id}` |
| Calendars | `POST` | `/calendars/` |
| | `GET` | `/calendars/{id}` |
| | `DELETE` | `/calendars/{id}` |
| Events | `POST` | `/calendars/{id}/events` |
| | `GET` | `/calendars/{id}/events` |
| | `GET` | `/calendars/{id}/events/{event_id}` |
| | `PUT` | `/calendars/{id}/events/{event_id}` ← full replace |
| | `DELETE` | `/calendars/{id}/events/{event_id}` |
| Emails | `GET` | `/emails/` |
| | `GET` | `/emails/{id}` |
| | `POST` | `/emails/` ← no DELETE |
| Scenarios | `GET` | `/scenarios/` |
| | `POST` | `/scenarios/` |
| | `GET` | `/scenarios/{id}` |
| | `DELETE` | `/scenarios/{id}` |
| | `POST` | `/scenarios/{id}/emails` |

### Key constraints

- `PATCH /todos/{id}` — partial update only; `scenario_id` and `calendar_event_id` cannot be changed
- `PUT /calendars/{id}/events/{event_id}` — full replace; send every field
- Calendar events must fall within the calendar's 100-day window (`start_date` through `start_date + 100 days`)
- Agent-sent email IDs: `max(all existing email_ids in store, default=0) + 1` — the counter is global, not per-scenario

### Error codes

| Status | Meaning |
|--------|---------|
| `400` | Invalid field values, constraint violation (e.g. event outside window) |
| `404` | Resource not found — also fires when `scenario_id` or `calendar_event_id` reference is missing |
| `409` | Conflict — caller-assigned ID already exists |
| `422` | Missing required field or wrong type |
| `500` | Unexpected server error |

---

## Tooling

| Tool | Version / Notes |
|------|-----------------|
| Package manager | `uv` — use `uv add`, `uv sync`, `uv run` |
| Framework | FastAPI |
| Validation | Pydantic v2 |
| Test runner | pytest via `uv run pytest` |
