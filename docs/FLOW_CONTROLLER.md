# flow_controller.py — Pool & Chain State Management

`flow_controller.py` manages which scenarios are in flight at any point during the 100-day simulation. It owns the **inactive pool**, the **active pool**, and the per-email state machine inside each active chain.

It exposes three things to the rest of the system:
- `EmailState` enum — `READY_TO_SERVE`, `AWAITING_SERVE`, `SERVED`
- `ActiveScenario` — wraps a `Scenario` and tracks per-email day offsets and served flags
- `FlowController` — the public entry point used by the Engine Driver

---

## How to run (smoke test)

```bash
python3 flow_controller.py
```

Walks through the first 7 simulated days, prints which emails are being served and which scenarios complete each day.

---

## The two pools

- **Inactive pool** — scenarios that have not yet started. They live here until their scheduled day arrives.
- **Active pool** — scenarios currently in progress. A single-email scenario lives here briefly (1 day). A multi-email chain stays here across multiple days until every email has been served.

When a scenario activates, the controller generates randomized per-email day offsets (described below), creates an `ActiveScenario` wrapper, and moves it from `inactive_pool` → `active_pool`.

---

## Email states (within an active chain)

Each email in an active chain is in exactly one state on any given day:

| State | Meaning |
|---|---|
| `READY_TO_SERVE` | Due today (its `email_day_offset` matches today's relative day) and not yet served. |
| `AWAITING_SERVE` | Scheduled for a future day in this chain. |
| `SERVED` | Already delivered to the model. |

The state is computed on demand from `start_day`, `email_day_offsets`, and `served` — no separate state field is stored.

---

## Chain timing — randomized intra-chain delays

Chains do **not** all serve on the same day, and they do not strictly serve one email per day. Each email after the first lands a small random gap after its predecessor:

| Gap from previous email | Probability |
|---|---|
| 0 days (same day) | 50% |
| 1 day later | 30% |
| 2 days later | 20% |

Examples for a 4-email chain starting on day N:
- Most likely: `[0, 0, 1, 1]` — emails arrive in two clusters
- Sometimes: `[0, 1, 1, 3]` — spread over a few days
- Sometimes: `[0, 0, 0, 0]` — rapid same-day burst
- Rarely: `[0, 2, 4, 6]` — slow drip

Expected chain duration: `(L − 1) × 0.7` days, so a 4-email chain averages ~2 days, a 6-email chain averages ~3.5 days. Worst case (all 2-day gaps) is `(L − 1) × 2` days.

> **Edge case**: scenarios activated very late (after ~day 90) can have chains that overflow past day 100. The simulation reports any leftover as `Remaining active: N` at the end. Decide later whether to extend the sim window, drain remaining chains, or shorten the schedule range.

---

## Day scheduling

`build_schedule(total_days=100)` shuffles all 109 scenarios randomly and deals them out **round-robin** across day slots. With 109 scenarios over 100 days, days 0–8 each get 2 starts; days 9–99 each get 1 start. The shuffle is seeded for reproducibility.

A scenario only enters the active pool on its scheduled day — not before.

---

## API

### `ActiveScenario`

| Attribute / method | Purpose |
|---|---|
| `scenario` | The underlying `Scenario` object from the loader. |
| `start_day` | Absolute sim-day this chain activated. |
| `email_day_offsets` | Per-email day offset relative to `start_day`. |
| `served` | Parallel `list[bool]` — flips True as each email is served. |
| `emails_due(current_day)` | Returns `[(index, Email), ...]` for unserved emails scheduled for today. |
| `email_states(current_day)` | Returns `{index: EmailState}` snapshot from today's perspective. |
| `mark_email_served(index)` | Flips `served[index]` to True. |
| `is_complete` (property) | True when every email has been served. |

### `FlowController`

| Method | Purpose |
|---|---|
| `__init__(scenarios, seed=None)` | Loads all scenarios into the inactive pool. `seed` controls shuffle + chain-gap RNG. |
| `build_schedule(total_days)` | Round-robins inactive scenarios across day slots. Must be called before `step`. |
| `step(day)` | Advances to `day`. Activates today's scheduled scenarios, then returns `[(email, scenario, email_index), ...]` due today across all active chains. |
| `mark_served(scenario_id, email_index)` | Engine calls this after each delivery. Removes the chain from `active_pool` once it's complete and queues the scenario for grading. |
| `completed_scenarios_today()` | Scenarios that just completed during this day's `mark_served` calls. Cleared at the start of every `step()`. |
| `status(day=None)` | Pool snapshot for logging — counts + per-active-scenario state breakdown. |

---

## How the Engine Driver uses it

The simulation loop in `engine.py` looks like this:

```python
controller = FlowController(scenarios, seed=42)
controller.build_schedule(total_days=100)

for day in range(100):
    ready = controller.step(day)                       # [(email, scenario, idx), ...]

    for email, scenario, idx in ready:
        resolved = apply_date_substitutions(email, sim_date)
        model_interaction_mock([resolved], sim_date)
        controller.mark_served(scenario.scenario_id, idx)

    for scenario in controller.completed_scenarios_today():
        result = define_grading_system(scenario, calendar=..., todo=...)
        # accumulate score

    sim_date += timedelta(days=1)
```

`step()` and `mark_served()` form the core loop; `completed_scenarios_today()` is the bridge to Anthony's grader (per-scenario grading at completion).

---

## What's intentionally not implemented

- **No "drain" at sim end.** Chains that overflow past day 100 stay in `active_pool`. Caller can read `controller.active_pool` post-simulation if it wants to handle them.
- **No re-entry.** Once a scenario is in `active_pool` and progressing, there's no mechanism to pause/restart it.
- **Round-robin only.** Day distribution is uniform shuffle + round-robin. No weighted scheduling, no day-of-week patterns, no clustering.
- **No back-pressure.** If 5 chains are all active and each fires 2 emails today, the engine gets 10 emails in one iteration. The model mock handles them sequentially, but there's no rate limit.

These are all intentional simplifications for sprint 2. Hooks are in place to extend any of them later.
