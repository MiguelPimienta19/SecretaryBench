import os
from pathlib import Path
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

API_BASE = os.environ.get("AISA_API_BASE_URL", "http://localhost:8000")

REPO_ROOT = Path(__file__).resolve().parent.parent
API_REFERENCE_PATH = REPO_ROOT / "docs" / "api_reference.md"

mcp = FastMCP("aisa-internal-system")
client = httpx.Client(base_url=API_BASE, timeout=10.0)


def _call(method: str, path: str, **kwargs: Any) -> Any:
    response = client.request(method, path, **kwargs)
    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"HTTP {response.status_code} {method} {path}: {detail}")
    if response.status_code == 204 or not response.content:
        return None
    return response.json()


# --- Resource ---

@mcp.resource("aisa://api-reference")
def api_reference() -> str:
    """Full operational reference for the AISA API: workflows, scenario_id rules, todo<->event linking, examples."""
    return API_REFERENCE_PATH.read_text()


# --- Health ---

@mcp.tool()
def health_check() -> dict:
    """Check that the AISA service is reachable."""
    return _call("GET", "/")


# --- Todos ---

@mcp.tool()
def list_todos() -> list[dict]:
    """List every todo across all scenarios."""
    return _call("GET", "/todos/")


@mcp.tool()
def get_todo(todo_id: str) -> dict:
    """Fetch one todo by its UUID."""
    return _call("GET", f"/todos/{todo_id}")


@mcp.tool()
def create_todo(
    title: str,
    due_date: str,
    scenario_id: int,
    description: str | None = None,
    calendar_event_id: str | None = None,
) -> dict:
    """Create a todo. due_date is ISO 8601 with timezone (e.g. '2026-05-01T09:00:00Z' or '+00:00'). scenario_id must exist; calendar_event_id (if given) must reference a real event."""
    body: dict[str, Any] = {"title": title, "due_date": due_date, "scenario_id": scenario_id}
    if description is not None:
        body["description"] = description
    if calendar_event_id is not None:
        body["calendar_event_id"] = calendar_event_id
    return _call("POST", "/todos/", json=body)


@mcp.tool()
def update_todo(
    todo_id: str,
    title: str | None = None,
    description: str | None = None,
    due_date: str | None = None,
    completed: bool | None = None,
) -> dict:
    """Partial update — only fields you pass are changed. scenario_id and calendar_event_id are immutable."""
    body: dict[str, Any] = {}
    if title is not None:
        body["title"] = title
    if description is not None:
        body["description"] = description
    if due_date is not None:
        body["due_date"] = due_date
    if completed is not None:
        body["completed"] = completed
    return _call("PATCH", f"/todos/{todo_id}", json=body)


@mcp.tool()
def delete_todo(todo_id: str) -> dict:
    """Delete a todo by its UUID."""
    _call("DELETE", f"/todos/{todo_id}")
    return {"status": "deleted", "todo_id": todo_id}


# --- Calendars ---

@mcp.tool()
def create_calendar(start_date: str) -> dict:
    """Create a fresh 100-day calendar window. start_date is ISO 8601 with timezone (e.g. '2026-04-22T00:00:00Z')."""
    return _call("POST", "/calendars/", json={"start_date": start_date})


@mcp.tool()
def get_calendar(calendar_id: str) -> dict:
    """Fetch a calendar (with all its events) by UUID."""
    return _call("GET", f"/calendars/{calendar_id}")


@mcp.tool()
def delete_calendar(calendar_id: str) -> dict:
    """Delete a calendar and cascade-delete its events."""
    _call("DELETE", f"/calendars/{calendar_id}")
    return {"status": "deleted", "calendar_id": calendar_id}


# --- Events ---

@mcp.tool()
def list_events(calendar_id: str) -> list[dict]:
    """List every event on a given calendar."""
    return _call("GET", f"/calendars/{calendar_id}/events")


@mcp.tool()
def get_event(calendar_id: str, event_id: str) -> dict:
    """Fetch a single event by its UUID."""
    return _call("GET", f"/calendars/{calendar_id}/events/{event_id}")


@mcp.tool()
def create_event(
    calendar_id: str,
    title: str,
    start: str,
    end: str,
    scenario_id: int,
    description: str | None = None,
) -> dict:
    """Create an event. start and end are ISO 8601 with timezone (e.g. '2026-04-22T10:00:00Z'). start < end, both within the calendar's 100-day window. scenario_id must exist."""
    body: dict[str, Any] = {"title": title, "start": start, "end": end, "scenario_id": scenario_id}
    if description is not None:
        body["description"] = description
    return _call("POST", f"/calendars/{calendar_id}/events", json=body)


@mcp.tool()
def update_event(
    calendar_id: str,
    event_id: str,
    title: str,
    start: str,
    end: str,
    scenario_id: int,
    description: str | None = None,
) -> dict:
    """Full replace (PUT) — every field is sent, including description (null clears it). start and end are ISO 8601 with timezone."""
    body: dict[str, Any] = {
        "title": title,
        "start": start,
        "end": end,
        "scenario_id": scenario_id,
        "description": description,
    }
    return _call("PUT", f"/calendars/{calendar_id}/events/{event_id}", json=body)


@mcp.tool()
def delete_event(calendar_id: str, event_id: str) -> dict:
    """Delete a single event from a calendar."""
    _call("DELETE", f"/calendars/{calendar_id}/events/{event_id}")
    return {"status": "deleted", "calendar_id": calendar_id, "event_id": event_id}


# --- Emails ---

@mcp.tool()
def list_emails() -> list[dict]:
    """Every email in the system (fixture + agent-sent) across all scenarios."""
    return _call("GET", "/emails/")


@mcp.tool()
def get_email(email_id: int) -> dict:
    """Fetch one email by integer id."""
    return _call("GET", f"/emails/{email_id}")


@mcp.tool()
def send_email(
    subject: str,
    sender: str,
    recipients: list[str],
    body: str,
    scenario_id: int,
) -> dict:
    """Agent-facing write. The server assigns email_id as (global max existing id) + 1."""
    payload = {
        "subject": subject,
        "sender": sender,
        "recipients": recipients,
        "body": body,
        "scenario_id": scenario_id,
    }
    return _call("POST", "/emails/", json=payload)


# --- Scenarios ---

@mcp.tool()
def list_scenarios() -> list[dict]:
    """Every scenario currently loaded in memory."""
    return _call("GET", "/scenarios/")


@mcp.tool()
def get_scenario(scenario_id: int) -> dict:
    """Fetch a single scenario (with all its emails) by id."""
    return _call("GET", f"/scenarios/{scenario_id}")


@mcp.tool()
def create_scenario(
    scenario_id: int,
    emails: list[dict] | None = None,
    success_criteria: str | None = None,
    puzzle_summary: str | None = None,
) -> dict:
    """Load a scenario (and its fixture emails) into the in-memory store."""
    payload: dict[str, Any] = {"scenario_id": scenario_id, "emails": emails or []}
    if success_criteria is not None:
        payload["success_criteria"] = success_criteria
    if puzzle_summary is not None:
        payload["puzzle_summary"] = puzzle_summary
    return _call("POST", "/scenarios/", json=payload)


@mcp.tool()
def delete_scenario(scenario_id: int) -> dict:
    """Delete a scenario and all of its emails."""
    _call("DELETE", f"/scenarios/{scenario_id}")
    return {"status": "deleted", "scenario_id": scenario_id}


@mcp.tool()
def add_scenario_email(
    scenario_id: int,
    email_id: int,
    subject: str,
    sender: str,
    recipients: list[str],
    body: str,
    created_at: str,
) -> dict:
    """Attach an additional fixture email to an already-loaded scenario. created_at is ISO 8601 with timezone."""
    payload = {
        "email_id": email_id,
        "subject": subject,
        "sender": sender,
        "recipients": recipients,
        "body": body,
        "created_at": created_at,
        "scenario_id": scenario_id,
    }
    return _call("POST", f"/scenarios/{scenario_id}/emails", json=payload)
