from __future__ import annotations

import calendar as _calendar
import re
import sys
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Optional

from loader import load_scenarios, Email, Scenario
from flow_controller import FlowController
from grader import define_grading_system


SIM_START = datetime(2000, 1, 1, tzinfo=timezone.utc)
SIM_DAYS = 100

_TOKEN_RE = re.compile(r"\{([^}]+)\}")
_DATE_FMT = "%B %d, %Y"
_DATETIME_FMT = "%B %d, %Y at %I:%M %p"


def _add_months(d: datetime, months: int) -> datetime:
    """Add `months` to `d`, clamping the day to the last valid day of the result month."""
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    last_day = _calendar.monthrange(year, month)[1]
    day = min(d.day, last_day)
    return d.replace(year=year, month=month, day=day)


def _parse_time(s: str) -> Optional[tuple[int, int]]:
    """Parse '10am', '2pm', '1:14pm', '12:30pm' -> (hour, minute) in 24h, or None."""
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?(am|pm)$", s)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    suffix = m.group(3)
    if suffix == "pm" and hour != 12:
        hour += 12
    elif suffix == "am" and hour == 12:
        hour = 0
    return hour, minute


def _next_day_of_month(sim_date: datetime, target_dom: int) -> datetime:
    """Return the next future occurrence of `target_dom` on or after sim_date."""
    try:
        candidate = sim_date.replace(day=target_dom)
    except ValueError:
        candidate = _add_months(sim_date, 1)
        last_day = _calendar.monthrange(candidate.year, candidate.month)[1]
        candidate = candidate.replace(day=min(target_dom, last_day))
    if candidate < sim_date:
        nxt = _add_months(sim_date, 1)
        last_day = _calendar.monthrange(nxt.year, nxt.month)[1]
        candidate = nxt.replace(day=min(target_dom, last_day))
    return candidate


def _resolve_one_token(raw: str, sim_date: datetime) -> Optional[str]:
    """Try to resolve a single token (the text inside {...}).

    Returns the resolved string, or None if unrecognized so the caller can
    leave the original token untouched.
    """
    # Normalize: lowercase + strip every whitespace char so "{date- next week}"
    # and "{date-nextweek}" collapse to the same form.
    normalized = re.sub(r"\s+", "", raw.lower())

    if normalized == "date":
        return sim_date.strftime(_DATE_FMT)

    if normalized in ("meeting-link", "link"):
        return "[meeting link]"

    # {date+N} or {date+Nweeks}
    m = re.match(r"^date\+(\d+)(weeks?)?$", normalized)
    if m:
        n = int(m.group(1))
        delta = timedelta(weeks=n) if m.group(2) else timedelta(days=n)
        return (sim_date + delta).strftime(_DATE_FMT)

    if normalized in ("date-tomorrow", "date-nextday"):
        return (sim_date + timedelta(days=1)).strftime(_DATE_FMT)

    if normalized == "date-beginningmonth":
        return sim_date.replace(day=1).strftime(_DATE_FMT)

    # {date-nextmonth} / {date-nextmonth+N}: same day-of-month next month, +N
    m = re.match(r"^date-nextmonth(?:\+(\d+))?$", normalized)
    if m:
        base = _add_months(sim_date, 1)
        if m.group(1):
            base += timedelta(days=int(m.group(1)))
        return base.strftime(_DATE_FMT)

    # All "next week" + relative offset variants:
    #   {date-nextweek}, {date-next-week}, {date- next week},
    #   {nextweek-date}, {nextweek - date}, {nextweek-date +3},
    #   {nextweek -date +5}, {nextweek - date -2}, ...
    # After whitespace strip they collapse onto one of these shapes.
    m = re.match(r"^(?:date-?next-?week|nextweek-?date)([+-]\d+)?$", normalized)
    if m:
        base = sim_date + timedelta(weeks=1)
        if m.group(1):
            base += timedelta(days=int(m.group(1)))
        return base.strftime(_DATE_FMT)

    # {date-thisweek} / {date-this-week} -> ambiguous, treat as today
    if re.match(r"^date-?this-?week$", normalized):
        return sim_date.strftime(_DATE_FMT)

    # {date-14th}, {date-25th} -> next future occurrence of that day-of-month
    m = re.match(r"^date-(\d{1,2})(?:st|nd|rd|th)$", normalized)
    if m:
        return _next_day_of_month(sim_date, int(m.group(1))).strftime(_DATE_FMT)

    # {date-10AM}, {date-1:14PM}, {date-12:30PM} -> today at that time
    m = re.match(r"^date-(.+)$", normalized)
    if m:
        time_parsed = _parse_time(m.group(1))
        if time_parsed is not None:
            hour, minute = time_parsed
            return sim_date.replace(hour=hour, minute=minute, second=0, microsecond=0)\
                .strftime(_DATETIME_FMT)

    return None


def resolve_tokens(text: str, sim_date: datetime) -> str:
    """Replace every {...} date/link token in `text` with a resolved value.

    Tokens that don't match a known pattern (e.g. `{Annual Report 1}`,
    `{contract 2}`, range tokens like `{date-12:30-2:00PM}`) are left as-is
    so they remain visible for downstream review.
    """
    if not text:
        return text

    def _sub(match: re.Match) -> str:
        resolved = _resolve_one_token(match.group(1), sim_date)
        return resolved if resolved is not None else match.group(0)

    return _TOKEN_RE.sub(_sub, text)


def apply_date_substitutions(email: Email, sim_date: datetime) -> Email:
    """Return a copy of `email` with subject and body tokens resolved."""
    e = deepcopy(email)
    e.subject = resolve_tokens(e.subject, sim_date)
    e.body = resolve_tokens(e.body, sim_date)
    return e


def model_interaction_mock(
    emails: list[Email], sim_date: datetime, verbose: bool = True
) -> None:
    """Placeholder for the real model call. Sleeps briefly to simulate latency."""
    if verbose:
        senders = ", ".join(e.sender for e in emails)
        print(f"  [model] serving {len(emails)} email(s) from {senders} "
              f"on {sim_date.strftime('%Y-%m-%d')}")
    time.sleep(0.05)


def run_simulation(
    path: str = "Emails.xlsx",
    sim_days: int = SIM_DAYS,
    sim_start: datetime = SIM_START,
    seed: Optional[int] = 42,
    verbose: bool = True,
) -> dict:
    """Run the full N-day benchmark simulation and return aggregated results."""
    scenarios = load_scenarios(path)
    controller = FlowController(scenarios, seed=seed)
    controller.build_schedule(total_days=sim_days)

    sim_date = sim_start
    total_score = 0
    total_max = 0
    daily_log: list[dict] = []

    # Empty state stand-ins for the grader. It only reads the events
    # attribute on the calendar and the length of the task list, so a
    # SimpleNamespace duck-types the calendar without dragging in pydantic.
    # Real tool state plugs in here once the model + MCP layer is wired up.
    empty_calendar = SimpleNamespace(events=[])
    empty_todos: list = []

    if verbose:
        print(f"Simulation: {len(scenarios)} scenarios over {sim_days} days "
              f"(start {sim_start.strftime('%Y-%m-%d')})\n")

    for day in range(sim_days):
        ready = controller.step(day)

        if ready and verbose:
            print(f"Day {day + 1} ({sim_date.strftime('%Y-%m-%d')}): "
                  f"{len(ready)} email(s) due")

        for email, scenario, idx in ready:
            resolved = apply_date_substitutions(email, sim_date)
            model_interaction_mock([resolved], sim_date, verbose=verbose)
            controller.mark_served(scenario.scenario_id, idx)

        # Grade scenarios that completed today (per-scenario, matches grader design)
        day_score = 0
        day_max = 0
        for scenario in controller.completed_scenarios_today():
            result = define_grading_system(scenario, empty_calendar, empty_todos)
            day_score += result["score"]
            day_max += result["max_score"]
            if verbose and result["max_score"] > 0:
                print(f"  [grader] [{scenario.scenario_type}] {scenario.scenario_id}: "
                      f"{result['score']}/{result['max_score']}")

        total_score += day_score
        total_max += day_max
        if ready or day_max:
            daily_log.append({
                "day": day + 1,
                "date": sim_date.strftime("%Y-%m-%d"),
                "served": len(ready),
                "score": day_score,
                "max_score": day_max,
            })

        sim_date += timedelta(days=1)

    if verbose:
        print(f"\nSimulation complete. Total: {total_score}/{total_max}")
        st = controller.status()
        print(f"Remaining inactive: {st['inactive_count']}, "
              f"active: {st['active_count']}")

    return {
        "total_score": total_score,
        "total_max": total_max,
        "daily_log": daily_log,
        "remaining_inactive": len(controller.inactive_pool),
        "remaining_active": len(controller.active_pool),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "Emails.xlsx"
    run_simulation(path, verbose=True)
