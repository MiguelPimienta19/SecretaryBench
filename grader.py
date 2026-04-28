
from __future__ import annotations

import re
from typing import Union

from loader import Email, Scenario
from app.models.calendar import CalendarResponse
from app.models.todo import TodoResponse


_NO_ACTION = re.compile(r"no\s*action", re.IGNORECASE)


def _check_criteria(criteria: str, calendar: CalendarResponse, todo: list[TodoResponse]) -> bool:
    """
    Check a single criteria string against tool state using prefix-level matching.
    TC- = a todo should have been created
    CC- = a calendar event should have been created
    No action = nothing should have been created
    RS- = a reschedule happened (event exists — rough check)

    Exact date/content verification is not yet implemented.
    """
    if not criteria or not criteria.strip():
        return False

    criteria = criteria.strip()

    # "No action" — model should have done nothing
    if _NO_ACTION.search(criteria):
        return len(todo) == 0 and len(calendar.events) == 0

    passed = True

    # TC- prefix — check that at least one todo exists
    if "TC" in criteria.upper():
        if len(todo) == 0:
            passed = False

    # CC- prefix — check that at least one calendar event exists
    if "CC" in criteria.upper():
        if len(calendar.events) == 0:
            passed = False

    # RS- prefix — check that an event exists (rough: reschedule implies event was modified)
    if "RS" in criteria.upper():
        if len(calendar.events) == 0:
            passed = False

    return passed


def define_grading_system(
    input: Union[Email, Scenario],
    calendar: CalendarResponse,
    todo: list[TodoResponse],
) -> dict:
    """
    Grade a single email or full scenario against the current tool state.

    Args:
        input:    Email object (single email) or Scenario object (email chain)
        calendar: CalendarResponse from Week 2 API — contains events list
        todo:     list of TodoResponse from Week 2 API — contains todo items

    Returns:
        dict with keys:
            score      — points awarded
            max_score  — total possible points
            details    — list of per-criteria results
    """
    if isinstance(input, Email): # Determine type and extract criteria list
        # Single email — wrap its criteria in a list (may be None)
        criteria_list = [input.success_criteria] if input.success_criteria else []
    elif isinstance(input, Scenario): # Scenario — already a list of strings
        criteria_list = input.success_criteria
    else:
        raise TypeError(f"Expected Email or Scenario, got {type(input).__name__}")

    # Score each criteria entry by checking the prefix against tool state.
    # TC- = todo should exist, CC- = calendar event should exist, No action = nothing should exist.
    # Date/content verification still TBD — only action TYPE is checked for now.
    score = 0
    details = []

    for criteria in criteria_list:
        passed = _check_criteria(criteria, calendar, todo)
        if passed:
            score += 1

        details.append({
            "criteria": criteria,
            "passed": passed,
        })

    return {
        "score": score,
        "max_score": len(criteria_list),
        "details": details,
    }


# ---------------------------------------------------------------------------
# CLI quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from datetime import datetime, timezone
    from loader import load_scenarios

    scenarios = load_scenarios("Emails.xlsx")
    print(f"Loaded {len(scenarios)} scenarios\n")

    # Create empty calendar and todo list for demo
    empty_calendar = CalendarResponse(
        calendar_id="demo",
        start_date=datetime.now(timezone.utc),
        events=[],
    )
    empty_todos: list[TodoResponse] = []

    total_score = 0
    total_max = 0

    # Grade each scenario
    for s in scenarios:
        result = define_grading_system(s, calendar=empty_calendar, todo=empty_todos)
        total_score += result["score"]
        total_max += result["max_score"]

        if result["max_score"] > 0:
            print(f"[{s.scenario_type}] {s.scenario_id}: {result['score']}/{result['max_score']}")

    print(f"\nTotal: {total_score}/{total_max}")

    # Also demo single-email grading
    print("\n--- Single email grading demo ---")
    for s in scenarios[:3]:
        for e in s.emails:
            result = define_grading_system(e, calendar=empty_calendar, todo=empty_todos)
            print(f"  Email #{e.email_number} ({e.subject[:40]}): {result['score']}/{result['max_score']}")
