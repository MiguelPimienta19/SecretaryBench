# AISA Spring 26 — Internal System

Unified FastAPI service for the AISA Spring 26 benchmark. Exposes four API surfaces — Todos, Calendars, Emails, and Scenarios — that an AI model can call during simulated benchmark runs.

---

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, error handlers, health check
│   ├── store.py         # In-memory data store (resets on restart)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── todo.py      # TodoCreate, TodoUpdate, TodoResponse
│   │   ├── calendar.py  # CalendarCreate, CalendarResponse, EventCreate, EventResponse
│   │   └── email.py     # Email, Scenario
│   └── routers/
│       ├── __init__.py
│       ├── todos.py      # /todos endpoints
│       ├── calendar.py   # /calendars endpoints
│       ├── emails.py     # /emails endpoints
│       └── scenarios.py  # /scenarios endpoints
├── tests/
│   ├── __init__.py
│   ├── test_todos.py     # 18 tests
│   ├── test_calendars.py # 22 tests
│   ├── test_emails.py    # 8 tests
│   └── test_scenarios.py # 18 tests
├── requirements.txt
└── README.md
```

---

## Setup

**1. Create and activate a virtual environment**

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

---

## Running the Server

```bash
uvicorn app.main:app --reload
```

Server starts at **http://127.0.0.1:8000**. `--reload` restarts automatically on file changes.

---

## Interactive API Docs

- **http://127.0.0.1:8000/docs** — Swagger UI
- **http://127.0.0.1:8000/redoc** — ReDoc

---

## API Endpoints

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check — returns `{"status": "ok"}` |

---

### Todos

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/todos/` | Create a todo |
| `GET` | `/todos/` | List all todos |
| `GET` | `/todos/{id}` | Get a todo by ID |
| `PUT` | `/todos/{id}` | Update todo fields (partial update) |
| `DELETE` | `/todos/{id}` | Delete a todo |

**Todo fields**

| Field | Type | Notes |
|-------|------|-------|
| `id` | string (UUID) | Auto-generated |
| `title` | string | Required |
| `description` | string | Optional |
| `due_date` | datetime (ISO 8601) | Required |
| `created_at` | datetime | Auto-set on creation |
| `completed` | boolean | Defaults to `false` |

**Examples**

```bash
# Create
curl -X POST http://127.0.0.1:8000/todos/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Write report", "due_date": "2026-05-01T12:00:00Z"}'

# List all
curl http://127.0.0.1:8000/todos/

# Mark completed
curl -X PUT http://127.0.0.1:8000/todos/<id> \
  -H "Content-Type: application/json" \
  -d '{"completed": true}'

# Delete
curl -X DELETE http://127.0.0.1:8000/todos/<id>
```

---

### Calendars & Events

Calendars define a 100-day time window. Events must fall within that window.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/calendars/` | Create a calendar |
| `GET` | `/calendars/{id}` | Get a calendar with its events |
| `DELETE` | `/calendars/{id}` | Delete a calendar |
| `POST` | `/calendars/{id}/events` | Add an event to a calendar |
| `GET` | `/calendars/{id}/events` | List events in a calendar |
| `GET` | `/calendars/{id}/events/{event_id}` | Get a single event |
| `PUT` | `/calendars/{id}/events/{event_id}` | Update an event |
| `DELETE` | `/calendars/{id}/events/{event_id}` | Delete an event |

**Calendar fields**

| Field | Type | Notes |
|-------|------|-------|
| `calendar_id` | string (UUID) | Auto-generated |
| `start_date` | datetime (ISO 8601) | Required. Defines the start of the 100-day window |
| `events` | list | Events belonging to this calendar |

**Event fields**

| Field | Type | Notes |
|-------|------|-------|
| `event_id` | string (UUID) | Auto-generated |
| `title` | string | Required |
| `description` | string | Optional |
| `start` | datetime (ISO 8601) | Required. Must be before `end` and within the calendar window |
| `end` | datetime (ISO 8601) | Required |

**Examples**

```bash
# Create a calendar
curl -X POST http://127.0.0.1:8000/calendars/ \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2026-04-15T00:00:00Z"}'

# Add an event
curl -X POST http://127.0.0.1:8000/calendars/<id>/events \
  -H "Content-Type: application/json" \
  -d '{"title": "Team sync", "start": "2026-04-16T09:00:00Z", "end": "2026-04-16T10:00:00Z"}'

# List events
curl http://127.0.0.1:8000/calendars/<id>/events
```

---

### Emails

Emails are created as part of a Scenario (or added to one via `POST /scenarios/{id}/emails`). They can be fetched and deleted individually.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/emails/` | List all emails |
| `GET` | `/emails/{id}` | Get an email by ID |
| `DELETE` | `/emails/{id}` | Delete an email (also removes it from its scenario) |

**Email fields**

| Field | Type | Notes |
|-------|------|-------|
| `email_id` | integer | Required. Provided by the caller |
| `subject` | string | Required |
| `sender` | string | Required |
| `recipients` | list of strings | Required |
| `body` | string | Required |
| `created_at` | datetime (ISO 8601) | Required |

**Examples**

```bash
# List all emails
curl http://127.0.0.1:8000/emails/

# Get a specific email
curl http://127.0.0.1:8000/emails/1

# Delete an email
curl -X DELETE http://127.0.0.1:8000/emails/1
```

---

### Scenarios

A scenario groups a set of emails together with optional metadata. Creating a scenario also registers all its emails in the email store.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/scenarios/` | List all scenarios |
| `POST` | `/scenarios/` | Create a scenario |
| `GET` | `/scenarios/{id}` | Get a scenario by ID |
| `DELETE` | `/scenarios/{id}` | Delete a scenario (also removes its emails) |
| `POST` | `/scenarios/{id}/emails` | Add an email to an existing scenario |

**Scenario fields**

| Field | Type | Notes |
|-------|------|-------|
| `scenario_id` | integer | Required. Provided by the caller |
| `emails` | list of Email | Optional. Emails included at creation time |
| `success_criteria` | string | Optional |
| `puzzle_summary` | string | Optional |

**Examples**

```bash
# Create a scenario with emails
curl -X POST http://127.0.0.1:8000/scenarios/ \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": 1,
    "success_criteria": "Agent forwards the email correctly",
    "emails": [{
      "email_id": 1,
      "subject": "Hello",
      "sender": "alice@example.com",
      "recipients": ["bob@example.com"],
      "body": "Hi there",
      "created_at": "2026-04-15T10:00:00Z"
    }]
  }'

# Add an email to an existing scenario
curl -X POST http://127.0.0.1:8000/scenarios/1/emails \
  -H "Content-Type: application/json" \
  -d '{
    "email_id": 2,
    "subject": "Follow-up",
    "sender": "alice@example.com",
    "recipients": ["bob@example.com"],
    "body": "Did you see my last message?",
    "created_at": "2026-04-15T11:00:00Z"
  }'

# Delete a scenario (removes its emails too)
curl -X DELETE http://127.0.0.1:8000/scenarios/1
```

---

## Error Handling

All errors return structured JSON:

| Status | Meaning |
|--------|---------|
| `400` | Invalid request (e.g. event start after end, outside calendar window) |
| `404` | Resource not found |
| `409` | Conflict (e.g. duplicate scenario or email ID) |
| `422` | Validation error (missing required field, wrong type) |
| `500` | Unexpected server error |

Example 404:
```json
{"detail": "Todo 'abc-123' not found."}
```

Example 422:
```json
{"error": "Validation error", "detail": [...]}
```

---

## Running Tests

```bash
pytest tests/ -v
```

Expected output: **66 passed**. Coverage:

| File | Tests | Covers |
|------|-------|--------|
| `test_todos.py` | 18 | Full CRUD, 404/422 errors |
| `test_calendars.py` | 22 | Calendars + events, window validation |
| `test_emails.py` | 8 | List, get, delete, cascade removal |
| `test_scenarios.py` | 18 | Full scenario lifecycle, email management |

---

## Data Persistence

The store is **in-memory only** — all data resets when the server restarts. This is intentional: each benchmark run starts from a clean state.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `pydantic` | Data validation and schemas |
| `pytest` | Test runner |
| `httpx` | HTTP client used by FastAPI's `TestClient` |
