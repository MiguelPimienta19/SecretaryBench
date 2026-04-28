# grader.py — Systems Grader

`grader.py` exposes a single function, `define_grading_system(input, calendar, todo)`, which takes either an `Email` or `Scenario` object along with a `CalendarResponse` (from `app.models.calendar`) and a `list[TodoResponse]` (from `app.models.todo`) and returns a score dict. It first checks whether the input is a single email or a full scenario, if it's an email, it wraps that email's `success_criteria` string into a list, and if it's a scenario, it uses the already-collected `success_criteria` list directly. Each criteria string is then checked against the tool state using prefix-level matching via the `_check_criteria` helper. **This will need to be updated once we decide what the final success criteria looks like.**

## Prefix-Level Checking

The grader parses the prefix of each criteria string to determine what type of action the model should have taken, then verifies that action against the current calendar and todo state:

| Prefix | Expected Action | Check |
|---|---|---|
| `TC-` | Model should have created a todo | `len(todo) > 0` |
| `CC-` | Model should have created a calendar event | `len(calendar.events) > 0` |
| `RS-` | Model should have rescheduled an event | `len(calendar.events) > 0` |
| `No action` | Model should have done nothing | `len(todo) == 0` AND `len(calendar.events) == 0` |

Criteria strings without a recognized prefix (freeform like "Add task", "Delegate Task") pass by default — these need team decision on how to handle.

A single criteria string can contain multiple prefixes (e.g. `TC-{date} && CC-{date}`). The current implementation checks all matching prefixes — if any expected action is missing, the criteria fails.

## What's Not Yet Implemented

Exact date and content verification is not implemented. The prefix check confirms the model took the right *type* of action but not that the date, time, or title are correct. This requires resolved date expressions from the Engine Driver (e.g. `{nextweek-date +3}` → actual date) and is the next step for the team.
