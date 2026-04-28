from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import random

from loader import Scenario, Email


class EmailState(Enum):
    """State of an email within an active scenario chain."""
    AWAITING_SERVE = "awaiting_serve"   # later in the chain, not its turn yet
    READY_TO_SERVE = "ready_to_serve"   # due today, not yet served
    SERVED = "served"                   # already delivered to the model


_CHAIN_GAP_CHOICES = [0, 1, 2]
_CHAIN_GAP_WEIGHTS = [0.5, 0.3, 0.2]


def _generate_email_offsets(num_emails: int, rng: random.Random) -> list[int]:
    """Generate per-email day offsets within a chain.

    Email 0 is always offset 0 (the day the chain activates). Each subsequent
    email lands 0/1/2 days after its predecessor, weighted 50/30/20.
    """
    offsets = [0]
    for _ in range(num_emails - 1):
        gap = rng.choices(_CHAIN_GAP_CHOICES, weights=_CHAIN_GAP_WEIGHTS, k=1)[0]
        offsets.append(offsets[-1] + gap)
    return offsets


@dataclass
class ActiveScenario:
    """A scenario currently being delivered. Tracks per-email state across days."""
    scenario: Scenario
    start_day: int                         # absolute sim-day the chain activated
    email_day_offsets: list[int]           # offset (in days) per email from start_day
    served: list[bool] = field(default_factory=list)

    def __post_init__(self):
        if not self.served:
            self.served = [False] * len(self.scenario.emails)

    def emails_due(self, current_day: int) -> list[tuple[int, Email]]:
        """Return (index, email) for every unserved email scheduled for today."""
        rel_day = current_day - self.start_day
        return [
            (i, email)
            for i, email in enumerate(self.scenario.emails)
            if self.email_day_offsets[i] == rel_day and not self.served[i]
        ]

    def email_states(self, current_day: int) -> dict[int, EmailState]:
        """Snapshot of every email's state from today's perspective."""
        rel_day = current_day - self.start_day
        states: dict[int, EmailState] = {}
        for i in range(len(self.scenario.emails)):
            if self.served[i]:
                states[i] = EmailState.SERVED
            elif self.email_day_offsets[i] == rel_day:
                states[i] = EmailState.READY_TO_SERVE
            else:
                states[i] = EmailState.AWAITING_SERVE
        return states

    def mark_email_served(self, index: int) -> None:
        self.served[index] = True

    @property
    def is_complete(self) -> bool:
        return all(self.served)


class FlowController:
    """Manages the inactive/active scenario pools and per-day email scheduling."""

    def __init__(self, scenarios: list[Scenario], seed: Optional[int] = None):
        self.inactive_pool: list[Scenario] = list(scenarios)
        self.active_pool: list[ActiveScenario] = []
        self._schedule: dict[int, list[Scenario]] = {}
        self._just_completed: list[Scenario] = []
        self._rng = random.Random(seed)

    def build_schedule(self, total_days: int) -> None:
        """Distribute inactive scenarios round-robin across `total_days`.

        Shuffles for randomized ordering, then assigns each scenario to a day
        slot. With more scenarios than days, some days get 2 starts; with
        fewer, some days get 0 starts.
        """
        shuffled = list(self.inactive_pool)
        self._rng.shuffle(shuffled)
        self._schedule = {d: [] for d in range(total_days)}
        for i, scenario in enumerate(shuffled):
            self._schedule[i % total_days].append(scenario)

    def step(self, day: int) -> list[tuple[Email, Scenario, int]]:
        """Advance simulation by one day.

        Activates any scenarios scheduled to start today, then collects every
        email due today across all active scenarios. Returns
        (email, scenario, email_index) tuples.
        """
        self._just_completed = []

        # Activate today's scheduled scenarios
        for scenario in self._schedule.get(day, []):
            if scenario in self.inactive_pool:
                self.inactive_pool.remove(scenario)
            offsets = _generate_email_offsets(len(scenario.emails), self._rng)
            self.active_pool.append(
                ActiveScenario(
                    scenario=scenario,
                    start_day=day,
                    email_day_offsets=offsets,
                )
            )

        # Collect emails due today
        ready: list[tuple[Email, Scenario, int]] = []
        for active in self.active_pool:
            for idx, email in active.emails_due(day):
                ready.append((email, active.scenario, idx))

        return ready

    def mark_served(self, scenario_id: str, email_index: int) -> None:
        """Engine calls this after delivering an email. Advances chain state.

        If the scenario completes (all emails served), it is removed from the
        active pool and queued for grading via `completed_scenarios_today`.
        """
        for active in self.active_pool:
            if active.scenario.scenario_id == scenario_id:
                active.mark_email_served(email_index)
                if active.is_complete:
                    self._just_completed.append(active.scenario)
                    self.active_pool.remove(active)
                return

    def completed_scenarios_today(self) -> list[Scenario]:
        """Scenarios that finished during this day's `mark_served` calls.

        Cleared at the start of every `step()`. The engine reads this after
        serving all of today's emails to know which scenarios to grade.
        """
        return list(self._just_completed)

    def status(self, day: Optional[int] = None) -> dict:
        """Pool snapshot for logging."""
        return {
            "inactive_count": len(self.inactive_pool),
            "active_count": len(self.active_pool),
            "active_scenarios": [
                {
                    "id": a.scenario.scenario_id,
                    "type": a.scenario.scenario_type,
                    "start_day": a.start_day,
                    "offsets": a.email_day_offsets,
                    "served": a.served,
                    "states": (
                        {i: s.value for i, s in a.email_states(day).items()}
                        if day is not None else None
                    ),
                }
                for a in self.active_pool
            ],
        }


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from loader import load_scenarios

    scenarios = load_scenarios("Emails.xlsx")
    controller = FlowController(scenarios, seed=42)
    controller.build_schedule(total_days=100)

    print(f"Loaded {len(scenarios)} scenarios into inactive pool\n")

    for day in range(7):
        ready = controller.step(day)
        print(f"Day {day}: {len(ready)} email(s) due")
        for email, scenario, idx in ready:
            subject = email.subject[:50] if email.subject else "(no subject)"
            print(f"  [{scenario.scenario_type}] email {idx + 1}/{len(scenario.emails)}: "
                  f"{subject!r}")
        for email, scenario, idx in ready:
            controller.mark_served(scenario.scenario_id, idx)
        completed = controller.completed_scenarios_today()
        if completed:
            ids = ", ".join(s.scenario_type for s in completed)
            print(f"  -> completed today: {ids}")
        print()

    status = controller.status()
    print(f"Pool status: inactive={status['inactive_count']}, "
          f"active={status['active_count']}")
