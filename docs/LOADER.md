# loader.py — Excel Ingestion & Object Modeling

This reads the Excel spreadsheet and converts every row into structured Python objects that the rest of the system can use.

---

## What it does

1. Opens `Emails.xlsx` and reads all 6 sheets (Will, Thara, Leo, Ellie, Ryan, Jake)
2. Cleans up the raw data (junk rows, blank cells, formatting quirks)
3. Groups rows into scenarios
4. Returns a clean list of `Scenario` objects, each holding a list of `Email` objects

---

## How to run

```bash
python3 loader.py Emails.xlsx
```

---

## The two objects

### `Email`
Represents a single email message.

| Field | Type | Description |
|---|---|---|
| `email_number` | `int` | Position in the thread (1, 2, 3...). 0 if not specified |
| `subject` | `str` | Email subject line |
| `body` | `str` | Full email body — placeholders like `{date-nextweek}` are kept raw |
| `sender` | `str` | Who sent the email (e.g. `"V"`, `"CEO"`) |
| `recipients` | `list[str]` | List of recipients, split from comma-separated string |
| `success_criteria` | `str or None` | What a successful action looks like for this specific email. `None` if not specified in the sheet |

### `Scenario`
Represents a full scenario — one or more emails that belong together.

| Field | Type | Description |
|---|---|---|
| `scenario_id` | `str` | Unique ID. Falls back to `scenario_type` if blank in the sheet |
| `scenario_type` | `str` | Type code from the sheet (e.g. `"T01"`, `"N02"`, `"C08"`) |
| `emails` | `list[Email]` | All emails in this scenario, sorted by email number |
| `success_criteria` | `list[str]` | Collected from every email in the scenario that has criteria. Multi-email scenarios may have criteria on only the last email, or on multiple emails (e.g. C25 has criteria on emails 1 and 3) |
| `puzzle_summary` | `str or None` | Plain-English description of the scenario. `None` if not filled in |

---

## How the sheet is parsed

- **Zero-width spaces** (`\u200b`) in column headers are stripped automatically
- **Blank spacer rows** (no Scenario Type and no Sender) are dropped
- **Junk rows** like `Example:` and `xxx` Scenario IDs are skipped
- **Scenario Type forward-fill** — multi-email scenarios leave the type blank on rows after the first; those blanks are filled downward so every row knows which scenario it belongs to
- **Grouping** — rows are grouped by consecutive Scenario Type blocks, so two separate T01 scenarios get different group IDs
- **Email ordering** — emails within a scenario are sorted by Email # numerically
- **Success Criteria / Puzzle Summary** — these only appear on one row per scenario in the sheet; the loader pulls them up to the Scenario level

---

## Timestamp placeholders

Body and subject fields may contain tokens like:

```
{date-nextweek}
{date-10AM}
{date+2}
{meeting-link}
```

These are stored **as-is** and are not substituted by the loader. The **Engine Driver** is responsible for replacing them with the actual simulation date at serve time.

---

## How to use it in other modules

```python
from loader import load_scenarios

scenarios = load_scenarios("Emails.xlsx")

for scenario in scenarios:
    print(scenario.scenario_type)       # e.g. "T01"
    print(scenario.success_criteria)    # e.g. "TC-{date}"
    for email in scenario.emails:
        print(email.sender, email.body)
```
