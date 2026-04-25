"""
In-memory store for the AISA benchmark. Resets every server restart — no persistence.

ID-type convention (why two of these are keyed by str and two by int):

  - Human-authored artifacts use INTEGER ids. Scenarios and fixture emails are
    written ahead of time in Excel, so authors need ids they can type, reference
    by number in `success_criteria` / `puzzle_summary` text, and read in logs.
    Agent-sent emails also use integers (assigned as max+1) so they share a
    namespace with the fixture thread they're replying to and preserve
    chronological order.

  - Runtime-generated artifacts use UUID STRING ids. Todos, calendars, and events
    are created by the agent during a run and are opaque references the server
    hands back. UUIDs prevent collisions and keep the agent from guessing ids.
"""
from typing import Dict
from app.models.todo import TodoResponse
from app.models.email import Email, Scenario
from app.models.calendar import CalendarResponse

# UUID-keyed — agent creates these at runtime
todos_db: Dict[str, TodoResponse] = {}
calendars: Dict[str, CalendarResponse] = {}

# integer-keyed — authored in Excel (scenarios, fixture emails) or assigned max+1 (agent-sent emails)
scenarios: Dict[int, Scenario] = {}
emails: Dict[int, Email] = {}
