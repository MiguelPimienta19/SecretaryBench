# AISA Internal System — API Reference

Base URL: `http://localhost:8000`

All request and response bodies are JSON. Datetime fields use ISO 8601 (e.g. `"2026-04-22T10:00:00Z"`). All data is in-memory and resets on server restart — there is no persistence between runs.

---

## Core Concepts

### `scenario_id` threads through every write

Every object the agent creates — a todo, a calendar event, a sent email — must be tagged with the `scenario_id` it belongs to.

- **Required** on `POST /todos/`, `POST /calendars/{id}/events`, `POST /emails/`
- **Validated** at create time — the server returns `404` if the `scenario_id` isn't in the store
- **Back-filled** automatically on fixture emails loaded via `POST /scenarios/` and `POST /scenarios/{id}/emails`
- **Immutable after creation** — `PATCH /todos/{id}` cannot change `scenario_id`

### Linking todos to calendar events

When a task requires both a todo and a calendar event, the agent performs two calls:

1. `POST /calendars/{calendar_id}/events` — create the event, receive `event_id`
2. `POST /todos/` with `calendar_event_id` set to that `event_id`

The server validates the `calendar_event_id` exists on some calendar and `404`s otherwise.

### ID assignment conventions

| Resource | ID type | Assigned by |
|---|---|---|
| Todo | UUID string | Server |
| Calendar | UUID string | Server |
| Event | UUID string | Server |
| Scenario | integer | Caller (Excel fixtures) |
| Email (fixture) | integer | Caller |
| Email (agent-sent via `POST /emails/`) | integer | Server — `max(existing_ids, default=0) + 1` |

**Note on `email_id`.** When you send an email via `POST /emails/`, the server assigns `max(all existing email_ids in the global store, default=0) + 1`. The counter is **global, not per-scenario** — if other scenarios are loaded with higher email ids, your reply follows the global maximum. Example: scenario 1 has emails 1–3 and scenario 2 has emails 101–103; a `POST /emails/` to scenario 1 returns `email_id: 104`, not `email_id: 4`. Within a single scenario your sent email always receives an id higher than every email that existed before the call, so relative ordering of ids within one thread still reflects chronology.

---

## Health

### `GET /`

Returns service status.

**Response 200**
```json
{ "status": "ok", "service": "AISA Internal System" }
```

---

## Todos

Todos are created by the agent as it works through a scenario. Each todo is tagged with the scenario it belongs to and may optionally reference a calendar event.

### `POST /todos/`

Create a new todo. The server assigns a UUID and timestamp.

**Request body**
| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | yes | |
| `description` | string | no | |
| `due_date` | datetime | yes | ISO 8601 |
| `scenario_id` | integer | yes | Must reference an existing scenario |
| `calendar_event_id` | string | no | If provided, must reference an existing event on some calendar |

**Example**
```json
{
  "title": "Reply to client proposal",
  "description": "Confirm the meeting time and attach the revised quote",
  "due_date": "2026-05-01T09:00:00Z",
  "scenario_id": 1,
  "calendar_event_id": "8d4e9c20-1234-4abc-b3fc-9f8e7d6c5b4a"
}
```

**Response 201** — `TodoResponse`
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "Reply to client proposal",
  "description": "Confirm the meeting time and attach the revised quote",
  "due_date": "2026-05-01T09:00:00Z",
  "created_at": "2026-04-22T08:00:00Z",
  "completed": false,
  "scenario_id": 1,
  "calendar_event_id": "8d4e9c20-1234-4abc-b3fc-9f8e7d6c5b4a"
}
```

**Response 404**
- `{ "detail": "Scenario <id> not found" }` — `scenario_id` doesn't exist
- `{ "detail": "Calendar event '<id>' not found" }` — `calendar_event_id` doesn't exist on any calendar

**Response 422** — missing or malformed field (e.g. `scenario_id` omitted)

---

### `GET /todos/`

List every todo across all scenarios.

**Response 200** — array of `TodoResponse`

---

### `GET /todos/{todo_id}`

Fetch one todo by its UUID.

**Response 200** — `TodoResponse`
**Response 404** — `{ "detail": "Todo '<id>' not found." }`

---

### `PATCH /todos/{todo_id}`

Partial update — only the fields you send get changed; omitted fields stay as they were.

**Request body** (all fields optional)
| Field | Type | Notes |
|---|---|---|
| `title` | string | |
| `description` | string | |
| `due_date` | datetime | ISO 8601 |
| `completed` | boolean | |

`scenario_id` and `calendar_event_id` cannot be patched — they're fixed at create time.

**Example**
```json
{ "completed": true }
```

**Response 200** — updated `TodoResponse`
**Response 404** — `{ "detail": "Todo '<id>' not found." }`

---

### `DELETE /todos/{todo_id}`

Delete a todo.

**Response 204** — no body
**Response 404** — `{ "detail": "Todo '<id>' not found." }`

---

## Calendars

A calendar has a `start_date` and a 100-day window. Every event on the calendar must fall entirely within that window.

### `POST /calendars/`

Create a new calendar. The server assigns a UUID.

**Request body**
| Field | Type | Required |
|---|---|---|
| `start_date` | datetime | yes |

**Example**
```json
{ "start_date": "2026-04-22T00:00:00Z" }
```

**Response 201** — `CalendarResponse`
```json
{
  "calendar_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "start_date": "2026-04-22T00:00:00Z",
  "events": []
}
```

---

### `GET /calendars/{calendar_id}`

Get a calendar and every event on it.

**Response 200** — `CalendarResponse`
**Response 404** — `{ "detail": "Calendar not found" }`

---

### `DELETE /calendars/{calendar_id}`

Delete a calendar and all of its events.

**Response 204** — no body
**Response 404** — `{ "detail": "Calendar not found" }`

---

### `POST /calendars/{calendar_id}/events`

Add a new event to a calendar.

**Constraints**
- `start` must be strictly before `end`
- Both `start` and `end` must fall within the calendar's 100-day window (`start_date` through `start_date + 100 days`). The upper bound is inclusive — `end` may equal `start_date + 100 days`.
- `scenario_id` must reference an existing scenario

**Request body**
| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | yes | |
| `description` | string | no | |
| `start` | datetime | yes | ISO 8601 |
| `end` | datetime | yes | ISO 8601 |
| `scenario_id` | integer | yes | Must reference an existing scenario |

**Example**
```json
{
  "title": "Kickoff with client",
  "description": "Intro call, 30 min",
  "start": "2026-04-23T09:00:00Z",
  "end": "2026-04-23T09:30:00Z",
  "scenario_id": 1
}
```

**Response 201** — `EventResponse`
```json
{
  "event_id": "8d4e9c20-1234-4abc-b3fc-9f8e7d6c5b4a",
  "title": "Kickoff with client",
  "description": "Intro call, 30 min",
  "start": "2026-04-23T09:00:00Z",
  "end": "2026-04-23T09:30:00Z",
  "scenario_id": 1
}
```

**Response 400**
- `{ "detail": "Event start must be before end" }` — `start >= end`
- `{ "detail": "Event must fall within the 100-day window: <window_start> to <window_end>" }` — the window boundary datetimes are interpolated into the string; use them to adjust your times

**Response 404**
- `{ "detail": "Calendar not found" }` — `calendar_id` doesn't exist
- `{ "detail": "Scenario <id> not found" }` — `scenario_id` doesn't exist

---

### `GET /calendars/{calendar_id}/events`

List every event on a calendar.

**Response 200** — array of `EventResponse`
**Response 404** — `{ "detail": "Calendar not found" }`

---

### `GET /calendars/{calendar_id}/events/{event_id}`

Fetch a single event.

**Response 200** — `EventResponse`
**Response 404**
- `{ "detail": "Calendar not found" }` — `calendar_id` doesn't exist
- `{ "detail": "Event not found" }` — the `event_id` isn't on this calendar

---

### `PUT /calendars/{calendar_id}/events/{event_id}`

**Full replace** — the caller must send every field, not just the ones they want to change. The `event_id` is preserved; everything else is overwritten.

**Request body** — same schema as `POST /calendars/{calendar_id}/events` (including `scenario_id`)

**Response 200** — updated `EventResponse`
**Response 400** — same validation rules as create (ordering, window)
**Response 404** — calendar, event, or scenario not found

---

### `DELETE /calendars/{calendar_id}/events/{event_id}`

Delete a single event from a calendar.

**Response 204** — no body
**Response 404**
- `{ "detail": "Calendar not found" }` — `calendar_id` doesn't exist
- `{ "detail": "Event not found" }` — the `event_id` isn't on this calendar

---

## Emails

Emails come from two sources:

1. **Fixture emails** — loaded into a scenario from Excel via `POST /scenarios/` or `POST /scenarios/{id}/emails`. These carry caller-assigned integer `email_id`s.
2. **Agent-sent emails** — created via `POST /emails/`. The server assigns the `email_id`.

There is no `DELETE /emails/{id}` — the Email API is read/write only.

### `GET /emails/`

List every email in the system (fixture + agent-sent).

**Response 200** — array of `Email`
```json
[
  {
    "email_id": 1,
    "subject": "Welcome",
    "sender": "admin@example.com",
    "recipients": ["user@example.com"],
    "body": "Hello there.",
    "created_at": "2026-04-22T08:00:00Z",
    "scenario_id": 1
  }
]
```

---

### `GET /emails/{email_id}`

Fetch one email by its integer ID.

**Response 200** — `Email`
**Response 404** — `{ "detail": "Email <id> not found" }`

---

### `POST /emails/`

Send a new email as the agent. The server assigns `email_id` as `max(existing_ids, default=0) + 1` and stamps `created_at` with the current UTC time.

**Request body**
| Field | Type | Required | Notes |
|---|---|---|---|
| `subject` | string | yes | |
| `sender` | string | yes | |
| `recipients` | array of string | yes | |
| `body` | string | yes | |
| `scenario_id` | integer | yes | Must reference an existing scenario |

**Example**
```json
{
  "subject": "Re: Kickoff",
  "sender": "agent@company.com",
  "recipients": ["client@example.com"],
  "body": "Confirmed for Thursday at 9am.",
  "scenario_id": 1
}
```

**Response 201** — `Email` (with server-assigned `email_id` and `created_at`)
**Response 404** — `{ "detail": "Scenario <id> not found" }`
**Response 422** — missing or malformed field (e.g. `scenario_id` omitted)

---

## Scenarios

A scenario groups emails together with optional evaluation metadata. Both `scenario_id` and the `email_id` of each fixture email are **integers provided by the caller**.

### `GET /scenarios/`

List every scenario currently loaded.

**Response 200** — array of `Scenario`

---

### `POST /scenarios/`

Load a scenario (and its fixture emails) from the Excel sheet into memory.

**Behavior**
- `scenario_id` must not already be in the store (409 if it is)
- `email_id`s must be unique within the payload (400 if duplicates)
- No fixture email's `email_id` can already exist in the store (409 if it does)
- Every fixture email has its `scenario_id` back-filled automatically — callers don't need to repeat it per row

**Request body**
| Field | Type | Required | Notes |
|---|---|---|---|
| `scenario_id` | integer | yes | Caller-assigned, must be unique |
| `emails` | array of `Email` | no | Defaults to `[]` |
| `success_criteria` | string | no | Internal — used by the evaluator |
| `puzzle_summary` | string | no | Internal — human-readable description |

Each `Email` object in the `emails` array:
| Field | Type | Required |
|---|---|---|
| `email_id` | integer | yes |
| `subject` | string | yes |
| `sender` | string | yes |
| `recipients` | array of string | yes |
| `body` | string | yes |
| `created_at` | datetime | yes |
| `scenario_id` | integer | no (back-filled by server) |

**Example**
```json
{
  "scenario_id": 1,
  "success_criteria": "Agent replies within 1 hour and schedules a follow-up",
  "puzzle_summary": "Client requests a kickoff meeting",
  "emails": [
    {
      "email_id": 101,
      "subject": "Project kickoff",
      "sender": "client@example.com",
      "recipients": ["agent@company.com"],
      "body": "Can we sync sometime this week?",
      "created_at": "2026-04-22T08:00:00Z"
    }
  ]
}
```

**Response 201** — `Scenario` (with `scenario_id` back-filled onto every email)
**Response 400** — `{ "detail": "Duplicate email_ids within scenario payload" }`
**Response 409**
- `{ "detail": "Scenario <id> already exists" }`
- `{ "detail": "Email <id> already exists" }`

---

### `GET /scenarios/{scenario_id}`

Fetch one scenario (with all its emails) by its integer ID.

**Response 200** — `Scenario`
**Response 404** — `{ "detail": "Scenario <id> not found" }`

---

### `DELETE /scenarios/{scenario_id}`

Delete a scenario and every email that belongs to it from the global email store.

**Response 204** — no body
**Response 404** — `{ "detail": "Scenario <id> not found" }`

---

### `POST /scenarios/{scenario_id}/emails`

Attach an additional fixture email to an already-loaded scenario. The email is also registered in the global email store, and its `scenario_id` is back-filled.

**Request body** — full `Email` object (same schema as the inline emails on `POST /scenarios/`)

**Example**
```json
{
  "email_id": 102,
  "subject": "Re: Project kickoff",
  "sender": "client@example.com",
  "recipients": ["agent@company.com"],
  "body": "Thursday 9am works. Talk then.",
  "created_at": "2026-04-22T09:00:00Z"
}
```

**Response 201** — `Email` (with `scenario_id` back-filled)
**Response 404** — `{ "detail": "Scenario <id> not found" }`
**Response 409** — `{ "detail": "Email <id> already exists" }`

---

## Error Responses

| Status | Meaning |
|---|---|
| 400 | Bad request — invalid field values, constraint violation, or duplicate IDs within a payload |
| 404 | Resource not found (includes references to missing `scenario_id` / `calendar_event_id` on create) |
| 409 | Conflict — caller-assigned ID already exists |
| 422 | Validation error — missing or wrong-type fields |
| 500 | Internal server error |

**422 body shape**
```json
{
  "error": "Validation error",
  "detail": [{ "loc": ["body", "field"], "msg": "...", "type": "..." }]
}
```

**500 body shape**
```json
{ "error": "Internal server error", "detail": "..." }
```

---

## Model Summary

### `TodoResponse`
```
id: str (UUID)
title: str
description: str | null
due_date: datetime
created_at: datetime
completed: bool
scenario_id: int | null
calendar_event_id: str | null
```

### `CalendarResponse`
```
calendar_id: str (UUID)
start_date: datetime
events: EventResponse[]
```

### `EventResponse`
```
event_id: str (UUID)
title: str
description: str | null
start: datetime
end: datetime
scenario_id: int | null
```

### `Email`
```
email_id: int
subject: str
sender: str
recipients: str[]
body: str
created_at: datetime
scenario_id: int | null
```

### `Scenario`
```
scenario_id: int
emails: Email[]
success_criteria: str | null
puzzle_summary: str | null
```
