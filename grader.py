
from __future__ import annotations

import sys
import os
from typing import Union
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "Instructions", "Week 2"))
from loader import Email, Scenario
from app.models.calendar import CalendarResponse
from app.models.todo import TodoResponse


#NOTE: Stub logic: non-empty criteria = 1 point. Real logic TBD by team.
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

    # Score each criteria entry
    # TO BE IMPLEMENTED: non-empty string = 1 point.
    # In the future implementation inspect calendar and todo to verify actions were taken.
    score = 0
    details = []

    # This is very rough, and not at all what will be final but I wanted to make sure we had something. 
    for criteria in criteria_list:
        if criteria and criteria.strip():
            passed = True
            score += 1
        else:
            passed = False

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
