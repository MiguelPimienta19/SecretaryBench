"""Pipeline tests for flow_controller.py and engine.py.

Run from the repo root with:
    python3 tests/test_pipeline.py

Exits 0 on success, 1 on any failure. Each test prints PASS/FAIL with detail.
No external test framework — plain assertions + a tiny harness so anyone on the
team can run it without installing pytest.
"""
from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime, timedelta, timezone

# Make repo-root modules (loader, flow_controller, engine, grader) importable
# regardless of where this script is launched from.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Tests rely on the working dir for "Emails.xlsx" — make it deterministic.
os.chdir(_REPO_ROOT)

from loader import load_scenarios, Email, Scenario
from flow_controller import (
    FlowController,
    ActiveScenario,
    EmailState,
    _generate_email_offsets,
)
from engine import (
    resolve_tokens,
    apply_date_substitutions,
    run_simulation,
    SIM_START,
)


# ---------------------------------------------------------------------------
# Tiny test harness
# ---------------------------------------------------------------------------

_results: list[tuple[str, bool, str]] = []


def test(name: str):
    """Decorator: run the function, capture pass/fail + any traceback."""
    def deco(fn):
        try:
            fn()
            _results.append((name, True, ""))
            print(f"  PASS  {name}")
        except AssertionError as e:
            _results.append((name, False, str(e) or "assertion failed"))
            print(f"  FAIL  {name}  -- {e or 'assertion failed'}")
        except Exception as e:
            tb = traceback.format_exc(limit=3)
            _results.append((name, False, f"{type(e).__name__}: {e}"))
            print(f"  FAIL  {name}  -- {type(e).__name__}: {e}")
            print(tb)
        return fn
    return deco


def section(label: str):
    print(f"\n--- {label} ---")


# Reference date used across token tests: a Wednesday in mid-March
REF = datetime(2000, 3, 15, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# 1. Token resolver tests
# ---------------------------------------------------------------------------

section("Token resolver")


@test("plain {date}")
def _():
    out = resolve_tokens("today is {date}", REF)
    assert "March 15, 2000" in out, out


@test("{date+N} day arithmetic")
def _():
    assert "March 17, 2000" in resolve_tokens("{date+2}", REF)
    assert "March 22, 2000" in resolve_tokens("{date+7}", REF)


@test("{date+Nweeks} week arithmetic")
def _():
    assert "March 29, 2000" in resolve_tokens("{date+2weeks}", REF)
    assert "April 05, 2000" in resolve_tokens("{date+3weeks}", REF)


@test("{date-tomorrow} and {date-nextday}")
def _():
    assert "March 16, 2000" in resolve_tokens("{date-tomorrow}", REF)
    assert "March 16, 2000" in resolve_tokens("{date-nextday}", REF)


@test("{date-nextweek} all spacing variants resolve identically")
def _():
    a = resolve_tokens("{date-nextweek}", REF)
    b = resolve_tokens("{date-next week}", REF)
    c = resolve_tokens("{date-next-week}", REF)
    assert a == b == c, (a, b, c)
    assert "March 22, 2000" in a, a


@test("{nextweek-date} all spacing variants resolve identically")
def _():
    a = resolve_tokens("{nextweek-date}", REF)
    b = resolve_tokens("{nextweek - date}", REF)
    c = resolve_tokens("{nextweek -date}", REF)
    assert a == b == c, (a, b, c)
    assert "March 22, 2000" in a, a


@test("{nextweek-date +N} relative offsets")
def _():
    assert "March 25, 2000" in resolve_tokens("{nextweek-date +3}", REF)
    assert "March 27, 2000" in resolve_tokens("{nextweek -date +5}", REF)
    assert "March 20, 2000" in resolve_tokens("{nextweek - date -2}", REF)


@test("{date-nextmonth} = same day next month (clamped)")
def _():
    # March 15 -> April 15
    assert "April 15, 2000" in resolve_tokens("{date-nextmonth}", REF)
    # End of month clamps: Jan 31 -> Feb 29 (leap year)
    end_of_month = datetime(2000, 1, 31, tzinfo=timezone.utc)
    assert "February 29, 2000" in resolve_tokens("{date-nextmonth}", end_of_month)


@test("{date-nextmonth+N}")
def _():
    assert "April 18, 2000" in resolve_tokens("{date-nextmonth+3}", REF)


@test("{date-beginningmonth} = first of current month")
def _():
    assert "March 01, 2000" in resolve_tokens("{date-beginningmonth}", REF)


@test("{date-Nth} day-of-month, future-or-this-month")
def _():
    assert "March 18, 2000" in resolve_tokens("{date-18th}", REF)  # later this month
    assert "April 14, 2000" in resolve_tokens("{date-14th}", REF)  # already past, next month


@test("{date-10AM}, {date-2PM}, {date-1:14PM} render with time")
def _():
    out = resolve_tokens("{date-10AM}", REF)
    assert "March 15, 2000" in out and "10:00 AM" in out, out
    out = resolve_tokens("{date-2PM}", REF)
    assert "02:00 PM" in out, out
    out = resolve_tokens("{date-1:14PM}", REF)
    assert "01:14 PM" in out, out


@test("{link} and {meeting-link}")
def _():
    assert "[meeting link]" in resolve_tokens("{link}", REF)
    assert "[meeting link]" in resolve_tokens("{meeting-link}", REF)


@test("unknown tokens left as-is")
def _():
    # Non-date tokens like document references should pass through
    assert resolve_tokens("see {Annual Report 1}", REF) == "see {Annual Report 1}"
    assert resolve_tokens("review {contract 2}", REF) == "review {contract 2}"
    # Range tokens are intentionally not resolved
    assert "{date-12:30-2:00PM}" in resolve_tokens("{date-12:30-2:00PM}", REF)


@test("multiple tokens in one string")
def _():
    out = resolve_tokens("from {date} to {date+3}", REF)
    assert "March 15, 2000" in out
    assert "March 18, 2000" in out


@test("apply_date_substitutions does not mutate original")
def _():
    e = Email(
        email_number=1, subject="meet {date}", body="see you {date+2}",
        sender="X", recipients=["Y"], success_criteria=None,
    )
    resolved = apply_date_substitutions(e, REF)
    assert e.subject == "meet {date}"        # original untouched
    assert e.body == "see you {date+2}"
    assert "March 15, 2000" in resolved.subject
    assert "March 17, 2000" in resolved.body


# ---------------------------------------------------------------------------
# 2. _generate_email_offsets tests
# ---------------------------------------------------------------------------

section("Chain offset generation")


@test("offsets are non-decreasing and start at 0")
def _():
    import random
    rng = random.Random(123)
    for length in [1, 2, 3, 4, 5, 6]:
        offsets = _generate_email_offsets(length, rng)
        assert len(offsets) == length, offsets
        assert offsets[0] == 0, offsets
        for i in range(1, len(offsets)):
            assert offsets[i] >= offsets[i - 1], offsets
            assert offsets[i] - offsets[i - 1] in (0, 1, 2), offsets


@test("single-email chain has [0]")
def _():
    import random
    assert _generate_email_offsets(1, random.Random(0)) == [0]


@test("offset distribution roughly matches 50/30/20 weights")
def _():
    import random
    rng = random.Random(42)
    counts = {0: 0, 1: 0, 2: 0}
    n_trials = 5000
    for _ in range(n_trials):
        offsets = _generate_email_offsets(2, rng)
        counts[offsets[1] - offsets[0]] += 1
    # expected ratios 0.5 / 0.3 / 0.2; allow 5% slack
    assert 0.45 < counts[0] / n_trials < 0.55, counts
    assert 0.25 < counts[1] / n_trials < 0.35, counts
    assert 0.15 < counts[2] / n_trials < 0.25, counts


# ---------------------------------------------------------------------------
# 3. FlowController tests with synthetic scenarios
# ---------------------------------------------------------------------------

section("FlowController pool behavior")


def _make_email(num: int, criteria=None) -> Email:
    return Email(
        email_number=num,
        subject=f"subject {num}",
        body=f"body {num}",
        sender="S", recipients=["R"],
        success_criteria=criteria,
    )


def _make_scenario(sid: str, n_emails: int, criteria=None) -> Scenario:
    return Scenario(
        scenario_id=sid,
        scenario_type=sid,
        emails=[_make_email(i + 1) for i in range(n_emails)],
        success_criteria=criteria or [],
        puzzle_summary=None,
    )


@test("inactive_pool seeded with all scenarios on construction")
def _():
    scenarios = [_make_scenario(f"S{i}", 1) for i in range(5)]
    fc = FlowController(scenarios)
    assert len(fc.inactive_pool) == 5
    assert len(fc.active_pool) == 0


@test("build_schedule round-robins across days")
def _():
    scenarios = [_make_scenario(f"S{i}", 1) for i in range(10)]
    fc = FlowController(scenarios, seed=0)
    fc.build_schedule(total_days=5)
    # 10 scenarios / 5 days = exactly 2 per day
    for d in range(5):
        assert len(fc._schedule[d]) == 2, fc._schedule[d]


@test("step() activates scheduled scenarios")
def _():
    scenarios = [_make_scenario(f"S{i}", 1) for i in range(3)]
    fc = FlowController(scenarios, seed=0)
    fc.build_schedule(total_days=3)
    ready = fc.step(0)
    assert len(ready) == 1
    assert len(fc.active_pool) == 1
    assert len(fc.inactive_pool) == 2


@test("single-email scenario completes in one day")
def _():
    s = _make_scenario("X", 1, criteria=["TC-{date}"])
    fc = FlowController([s], seed=0)
    fc.build_schedule(total_days=1)
    ready = fc.step(0)
    assert len(ready) == 1
    email, scenario, idx = ready[0]
    assert scenario.scenario_id == "X"
    fc.mark_served("X", idx)
    completed = fc.completed_scenarios_today()
    assert len(completed) == 1
    assert completed[0].scenario_id == "X"
    assert len(fc.active_pool) == 0


@test("multi-email chain spans multiple days when offsets > 0")
def _():
    s = _make_scenario("M", 3)
    fc = FlowController([s], seed=0)
    fc.build_schedule(total_days=10)
    # Force a known offset pattern by injecting an ActiveScenario directly
    fc.inactive_pool.remove(s)
    active = ActiveScenario(scenario=s, start_day=0, email_day_offsets=[0, 1, 2])
    fc.active_pool.append(active)
    fc._schedule = {d: [] for d in range(10)}  # disable auto-activation

    ready_d0 = fc.step(0)
    assert len(ready_d0) == 1, ready_d0
    fc.mark_served("M", ready_d0[0][2])
    assert not fc.completed_scenarios_today()

    ready_d1 = fc.step(1)
    assert len(ready_d1) == 1, ready_d1
    fc.mark_served("M", ready_d1[0][2])
    assert not fc.completed_scenarios_today()

    ready_d2 = fc.step(2)
    assert len(ready_d2) == 1, ready_d2
    fc.mark_served("M", ready_d2[0][2])
    completed = fc.completed_scenarios_today()
    assert len(completed) == 1


@test("multi-email chain with zero gaps fires all on same day")
def _():
    s = _make_scenario("B", 4)
    fc = FlowController([s], seed=0)
    fc.inactive_pool.remove(s)
    active = ActiveScenario(scenario=s, start_day=0, email_day_offsets=[0, 0, 0, 0])
    fc.active_pool.append(active)
    fc._schedule = {0: []}

    ready = fc.step(0)
    assert len(ready) == 4
    for _e, _s, idx in ready:
        fc.mark_served("B", idx)
    completed = fc.completed_scenarios_today()
    assert len(completed) == 1


@test("email_states reflects READY / AWAITING / SERVED correctly")
def _():
    s = _make_scenario("E", 3)
    a = ActiveScenario(scenario=s, start_day=5, email_day_offsets=[0, 1, 2])

    states_d5 = a.email_states(5)
    assert states_d5[0] == EmailState.READY_TO_SERVE
    assert states_d5[1] == EmailState.AWAITING_SERVE
    assert states_d5[2] == EmailState.AWAITING_SERVE

    a.mark_email_served(0)
    states_d6 = a.email_states(6)
    assert states_d6[0] == EmailState.SERVED
    assert states_d6[1] == EmailState.READY_TO_SERVE
    assert states_d6[2] == EmailState.AWAITING_SERVE


@test("completed_scenarios_today resets each step()")
def _():
    s = _make_scenario("R", 1)
    fc = FlowController([s], seed=0)
    fc.build_schedule(total_days=2)
    fc.step(0)
    ready = fc.step(0)  # idempotent activation check
    # Find served scenario
    if ready:
        for _e, _s, idx in ready:
            fc.mark_served("R", idx)
    fc.completed_scenarios_today()
    fc.step(1)  # next step
    assert fc.completed_scenarios_today() == []  # cleared on new step


# ---------------------------------------------------------------------------
# 4. End-to-end simulation with the real Excel data
# ---------------------------------------------------------------------------

section("End-to-end simulation")


@test("run_simulation completes without errors")
def _():
    result = run_simulation("Emails.xlsx", verbose=False, seed=42)
    assert "total_score" in result
    assert "total_max" in result
    assert isinstance(result["daily_log"], list)


@test("all 109 scenarios get scheduled (none left in inactive pool)")
def _():
    result = run_simulation("Emails.xlsx", verbose=False, seed=42)
    assert result["remaining_inactive"] == 0, result


@test("vast majority of scenarios complete within 100 days")
def _():
    result = run_simulation("Emails.xlsx", verbose=False, seed=42)
    # Allow a small overflow (worst-case chains activated late in the sim)
    assert result["remaining_active"] <= 5, result


@test("daily_log has entries for active days")
def _():
    result = run_simulation("Emails.xlsx", verbose=False, seed=42)
    served_total = sum(d["served"] for d in result["daily_log"])
    # Total emails served across the sim should be close to total emails.
    # (May be less if some chains overflow.)
    scenarios = load_scenarios("Emails.xlsx")
    total_emails = sum(len(s.emails) for s in scenarios)
    assert served_total >= total_emails * 0.95, (served_total, total_emails)


@test("grader is invoked and returns valid scores")
def _():
    result = run_simulation("Emails.xlsx", verbose=False, seed=42)
    assert result["total_max"] > 0
    assert 0 <= result["total_score"] <= result["total_max"]


@test("simulation is reproducible with same seed")
def _():
    a = run_simulation("Emails.xlsx", verbose=False, seed=99)
    b = run_simulation("Emails.xlsx", verbose=False, seed=99)
    assert a["total_score"] == b["total_score"]
    assert a["total_max"] == b["total_max"]
    assert len(a["daily_log"]) == len(b["daily_log"])


@test("different seeds produce different schedules")
def _():
    a = run_simulation("Emails.xlsx", verbose=False, seed=1)
    b = run_simulation("Emails.xlsx", verbose=False, seed=2)
    # daily_log content should differ even if totals happen to match
    assert a["daily_log"] != b["daily_log"]


@test("date tokens get resolved before reaching grader")
def _():
    # Sanity check by hand-resolving a sample email and checking content
    scenarios = load_scenarios("Emails.xlsx")
    sample = next(
        (e for s in scenarios for e in s.emails if "{date" in e.body),
        None,
    )
    if sample is None:
        return  # nothing to test
    resolved = apply_date_substitutions(sample, REF)
    # Resolved body should NOT contain certain bare date tokens we know we handle
    # (it may still contain unknown / range / document tokens — that's expected)
    handled = ["{date}", "{date+1}", "{date-tomorrow}", "{date-nextweek}"]
    for tok in handled:
        if tok in sample.body:
            assert tok not in resolved.body, f"unresolved token: {tok}"


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed (of {len(_results)})")
    print(f"{'=' * 50}")
    if failed:
        print("\nFailures:")
        for name, ok, msg in _results:
            if not ok:
                print(f"  - {name}: {msg}")
        sys.exit(1)
    sys.exit(0)
