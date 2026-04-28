# engine.py — Pipeline & Time Simulation

`engine.py` is the heartbeat of the 100-day benchmark. It drives the day loop, resolves date placeholders inside email content, hands emails to the model (placeholder for now), and connects to Anthony's grader after each scenario completes.

It coordinates three other modules:
- **`loader.py`** — reads the Excel file into `Scenario`/`Email` objects
- **`flow_controller.py`** — decides which emails are due each day
- **`grader.py`** — scores completed scenarios

---

## How to run

```bash
python3 engine.py                      # default: Emails.xlsx
python3 engine.py path/to/file.xlsx    # custom path
```

Default settings: 100-day simulation starting January 1, 2000, seeded with `seed=42` for reproducibility.

---

## What it does, top-down

```
load_scenarios("Emails.xlsx")                 # 109 Scenario objects
controller = FlowController(scenarios)        # 109 in inactive_pool
controller.build_schedule(total_days=100)

for day in 0..99:
    ready = controller.step(day)              # emails due today
    for email, scenario, idx in ready:
        resolved = apply_date_substitutions(email, sim_date)   # tokens → dates
        model_interaction_mock([resolved], sim_date)           # placeholder
        controller.mark_served(scenario.scenario_id, idx)

    for scenario in controller.completed_scenarios_today():
        result = define_grading_system(scenario, ...)          # Anthony's grader
        # accumulate score

    sim_date += 1 day

return aggregated results
```

Per-day, the engine: (1) asks the controller what's ready, (2) resolves tokens in each email, (3) hands the resolved email to the model mock, (4) tells the controller it was served, (5) grades any scenarios that finished today, (6) ticks the clock.

---

## Token resolution

The Excel sheet uses `{...}` tokens as placeholders for dates and links. The token syntax in the source data is messy and inconsistent — different spacing, different orderings, mixed casing. The resolver normalizes the inside of every token (lowercase + strip whitespace) before matching, so all of these resolve to the same value:

```
{date-nextweek} = {date-next week} = {date-next-week} = {nextweek-date}
```

### Supported tokens

| Token (any spacing) | Resolves to |
|---|---|
| `{date}` | sim date |
| `{date+N}` | sim date + N days |
| `{date+Nweeks}` | sim date + N weeks |
| `{date-tomorrow}`, `{date-nextday}` | sim date + 1 day |
| `{date-thisweek}` (any spacing) | sim date (treated as today, since "this week" is ambiguous) |
| `{date-nextweek}` (any spacing) | sim date + 1 week |
| `{date-next week -N}` | sim date + 1 week − N days |
| `{nextweek-date}` (any spacing) | sim date + 1 week |
| `{nextweek-date +N}` | sim date + 1 week + N days |
| `{nextweek-date -N}` | sim date + 1 week − N days |
| `{date-beginningmonth}` | first day of current month |
| `{date-nextmonth}` | same day-of-month, next month (clamped to last valid day) |
| `{date-nextmonth+N}` | next month, +N days |
| `{date-Nth}` (e.g. `{date-14th}`) | next future occurrence of that day-of-month |
| `{date-10AM}`, `{date-2PM}`, `{date-1:14PM}`, `{date-12:30PM}` | sim date at that time |
| `{link}`, `{meeting-link}` | `[meeting link]` |

### Tokens left as-is (intentionally)

| Token | Why |
|---|---|
| `{Annual Report 1}`, `{contract 2}`, `{Q3 onboarding strategy doc}` | Document references — not date-related, no resolution needed |
| `{date-12:30-2:00PM}` | Time range — ambiguous, defer to team decision |
| `{Tuesday- this week at 3:00 PM}` | Mixed day+time reference — no canonical pattern |
| Anything else unrecognized | Visible in output for review |

The resolver never crashes on an unknown token; it just leaves it untouched.

### Date format

Dates render as `"March 15, 2000"`. Times render as `"March 15, 2000 at 10:00 AM"`.

---

## API

### Public functions

| Function | Purpose |
|---|---|
| `resolve_tokens(text, sim_date)` | Replace every `{...}` in `text` using `sim_date` as the reference. Unknown tokens are left untouched. |
| `apply_date_substitutions(email, sim_date)` | Returns a deep copy of the email with `subject` and `body` token-resolved. |
| `model_interaction_mock(emails, sim_date, verbose=True)` | Placeholder for the real model call. Sleeps ~0.05s. Replace this when MCP is wired up. |
| `run_simulation(path, sim_days, sim_start, seed, verbose)` | The full simulation. Returns `{total_score, total_max, daily_log, remaining_inactive, remaining_active}`. |

### Constants

```python
SIM_START = datetime(2000, 1, 1, tzinfo=timezone.utc)
SIM_DAYS  = 100
```

---

## Connection to the grader

Anthony's `define_grading_system(input, calendar, todo)` accepts either an `Email` or a `Scenario`. The engine calls it with the **`Scenario` object** at scenario completion (when the last email is served), passing the loader's aggregated `success_criteria` list directly.

```python
result = define_grading_system(scenario, calendar=empty_calendar, todo=empty_todos)
```

Why per-scenario instead of per-email:
- Loader aggregates all per-email criteria onto the scenario already
- Most chain emails have `success_criteria = None`, so per-email grading is mostly empty calls
- Tool state accumulates across emails — checking once at the end matches how a real model would build up state

The `grader.py` file is **not modified**. The engine is the only thing that calls it.

### Tool state today vs. tomorrow

Right now the engine passes an **empty `CalendarResponse` and empty todo list** to the grader. The current grader does prefix-only matching, so empty state means most non-`No action` criteria fail. **This is expected** — the score numbers are noise until the model is wired up.

When MCP and the real model are integrated, replace these stand-ins with the live state from the FastAPI service in `app/`.

### When Anthony upgrades the grader for exact-date checking

He can `from engine import resolve_tokens` and call it on each criteria string before parsing. Same resolver as the engine uses — the dates will line up.

---

## What `run_simulation` returns

```python
{
    "total_score": int,
    "total_max": int,
    "daily_log": [
        {"day": 1, "date": "2000-01-01", "served": 3, "score": 0, "max_score": 1},
        ...
    ],
    "remaining_inactive": int,    # scenarios never activated (should be 0 for normal runs)
    "remaining_active": int,      # chains overflowing past day 100 (rare, see Flow Controller doc)
}
```

---

## Notes & gotchas

- **Reproducibility**: seeded with `seed=42` by default. Same seed → same scenario distribution, same chain offsets. Pass `seed=None` for nondeterministic runs.
- **Sim start date**: `January 1, 2000` is arbitrary, chosen to match the calendar model's example. Change it via the `sim_start` parameter — token resolution adapts automatically.
- **Verbose mode**: `verbose=True` prints day-by-day activity. Turn off for batch runs.
- **No model integration yet**: `model_interaction_mock` just prints and sleeps. The MCP team replaces this.
- **Empty grader inputs**: `CalendarResponse(events=[])` and `[]` are passed to the grader. Until the model takes real actions, scores reflect the grader's empty-state behavior, not model performance.
- **Edge case**: chains activated late (~after day 90) with worst-case 2-day gaps can overflow past day 100. The engine reports them in `remaining_active`. To eliminate, either expand `sim_days` or shorten `build_schedule`'s range.

---

## What's intentionally not implemented

- **Real model call** — placeholder only
- **Real tool state during grading** — empty stubs
- **Resolving criteria tokens** — left for Anthony to wire up when he upgrades the grader
- **Persistent results** — `run_simulation` returns a dict; saving to JSON/CSV is the caller's job
- **Mid-run state inspection** — no debug hooks beyond `controller.status()`. Add as needed.
