# SecretaryBench

Repository for the AISA OpenAI Temporal Reasoning Benchmark.

A 100-day simulation that delivers email scenarios to an AI model and grades
its responses. Built as a sequence of decoupled stages (Loader → Flow
Controller → Engine Driver → Grader) connected to an internal FastAPI service
the model uses for tool calls.

---

## Project Structure

```
.
├── README.md                ← this file
├── requirements.txt         ← Python dependencies
├── conftest.py              ← pytest helper (sets sys.path)
├── Emails.xlsx              ← scenario source data
│
├── loader.py                ← Excel → Scenario/Email objects
├── flow_controller.py       ← scenario pool + chain state machine
├── engine.py                ← 100-day loop, token resolution, model mock
├── grader.py                ← scoring against tool state
│
├── app/                     ← internal FastAPI service (Week 1)
│   ├── main.py
│   ├── store.py
│   ├── models/              ← Pydantic schemas
│   └── routers/             ← /todos, /calendars, /emails, /scenarios
│
├── docs/                    ← module-level documentation
│   ├── LOADER.md
│   ├── FLOW_CONTROLLER.md
│   ├── ENGINE.md
│   ├── GRADER.md
│   └── API.md
│
├── instructions/            ← sprint planning & delegation docs
│   ├── sprint-one.md
│   ├── sprint-two.md
│   └── Sprint 2 Questions and Delegation.pdf
│
└── tests/
    ├── test_pipeline.py     ← end-to-end loader + flow + engine + grader
    └── api/                 ← FastAPI service tests (Week 1)
        ├── test_calendars.py
        ├── test_emails.py
        ├── test_scenarios.py
        └── test_todos.py
```

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Running things

| What | Command |
|------|---------|
| Full 100-day simulation | `python3 engine.py` |
| Flow controller smoke test | `python3 flow_controller.py` |
| Loader smoke test | `python3 loader.py Emails.xlsx` |
| Grader smoke test | `python3 grader.py` |
| Pipeline tests (no pytest needed) | `python3 tests/test_pipeline.py` |
| FastAPI service | `uvicorn app.main:app --reload` |
| FastAPI tests | `pytest tests/api/ -v` |
| All tests | `pytest tests/ -v` |

---

## Module overview

| Module | Owner | Purpose |
|--------|-------|---------|
| `loader.py` | Eyasu | Reads `Emails.xlsx` into `Scenario`/`Email` dataclasses. See `docs/LOADER.md`. |
| `flow_controller.py` | Nikita | Manages inactive/active scenario pools and per-day email scheduling. See `docs/FLOW_CONTROLLER.md`. |
| `engine.py` | Nikita | The 100-day simulation loop, date-token resolver, model interaction mock. See `docs/ENGINE.md`. |
| `grader.py` | Anthony | Scores scenarios against tool state (current: prefix-only matching). See `docs/GRADER.md`. |
| `app/` | Nikita / Anthony / Miguel | FastAPI service exposing todo, calendar, email, and scenario endpoints for the model to call. See `docs/API.md`. |

---

## Pipeline at a glance

```
Emails.xlsx
    │
    ▼
loader.py ───────────► [Scenario, ...] ──► flow_controller.py
                                              │
                                              ▼
                                          (inactive pool)
                                              │  build_schedule
                                              ▼
                                          (active pool)
                                              │  step(day)
                                              ▼
                                       engine.py (loop)
                                              │  resolve_tokens
                                              │  model_interaction_mock
                                              │  mark_served
                                              ▼
                                   grader.define_grading_system
                                              │
                                              ▼
                                       score / max_score
```
