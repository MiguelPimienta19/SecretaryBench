# MCP Server

The AISA benchmark exposes its tools (todos, calendar, email, scenarios) over MCP so any LLM harness can call them directly. Setup is one step regardless of which harness you use.

FastAPI must be running whenever you use the benchmark:
```bash
uv run uvicorn app.main:app --reload
```

---

## Connecting your harness

### Claude Code — automatic
`.mcp.json` is already in the repo. Clone and open the project — done.

```bash
claude mcp list
# aisa: bash -c uv run python -m mcp_server  - ✓ Connected
```

### Cursor — automatic
`.cursor/mcp.json` is already in the repo. Clone and open the project in Cursor — done. Check the MCP panel in Cursor settings to confirm `aisa` appears as connected.

### Codex — one command
Paste this in your terminal from the project root:
```bash
codex mcp add --name aisa --command bash --args '-c "uv run python -m mcp_server"'
```

If that doesn't work on your version of Codex:
```bash
cat >> ~/.codex/config.toml << 'EOF'

[[mcp_servers]]
name = "aisa"
command = "bash"
args = ["-c", "uv run python -m mcp_server"]
EOF
```

---

## How it actually works

```
┌─────────────────┐  stdio   ┌──────────────────┐   HTTP   ┌──────────────────┐
│   LLM harness   │ ───────► │   MCP server     │ ───────► │   FastAPI        │
│ (Claude Code,   │ ◄─────── │   (mcp_server/)  │ ◄─────── │   (port 8000)    │
│  Cursor, Codex) │          │   thin wrapper   │          │   real logic     │
└─────────────────┘          └──────────────────┘          └──────────────────┘
```

**Two processes, two protocols.**

The left side is stdio — your harness launches `mcp_server` as a subprocess and communicates through pipes. This is the MCP standard. You never see this traffic directly.

The right side is HTTP — the MCP server calls FastAPI exactly like any external client would. This is intentional: all benchmark logic lives in `app/`, not in `mcp_server/`. If behavior is wrong, the bug is in `app/`.

**The MCP server itself does almost nothing.** Each tool in `mcp_server/server.py` is ~3 lines: build a JSON body, call FastAPI, return the response. The tool's docstring becomes its description in the MCP protocol — that's what the agent reads to understand what each tool does.

**The resource.** There's one resource at `aisa://api-reference` that returns the full contents of `docs/api_reference.md`. The agent can fetch this on demand to understand workflows, the `scenario_id` rule, and how todos link to calendar events. Think of it as the agent's manual.

---

## What the agent can see

22 tools across the full API:

| Group | Tools |
|---|---|
| Todos | `list_todos` `get_todo` `create_todo` `update_todo` `delete_todo` |
| Calendars | `create_calendar` `get_calendar` `delete_calendar` |
| Events | `list_events` `get_event` `create_event` `update_event` `delete_event` |
| Emails | `list_emails` `get_email` `send_email` |
| Scenarios | `list_scenarios` `get_scenario` `create_scenario` `delete_scenario` `add_scenario_email` |
| Health | `health_check` |

---

## What to watch out for

**The store resets on every restart.** FastAPI uses in-memory storage — no database. Every time uvicorn stops and restarts, everything is gone. Always seed your scenario before running an agent.

**Seed before the agent runs.** Tools like `create_todo` and `create_event` require `scenario_id` to exist in the store. If it doesn't, they return 404. The agent will see that error — which is fine (it's a feature of the benchmark), but you don't want the agent failing before it even starts.

**Order matters and the agent has to figure it out.** A todo can optionally link to a calendar event via `calendar_event_id`. The API validates that the event exists at creation time — so the agent must create the event first, then the todo. Getting this dependency right is part of what the benchmark is actually testing.

**The agent can see admin tools.** `create_scenario`, `delete_scenario`, and `add_scenario_email` are visible to the agent alongside the regular tools. This is intentional for a research surface — you want to observe what the agent does with full access. For a controlled benchmark run, you may want to filter these out.

**Datetime fields are strict.** All `due_date`, `start`, `end`, and `created_at` fields must be ISO 8601 with timezone (e.g. `2026-05-01T09:00:00Z`). Pydantic v2 is fairly permissive but if you see 422 errors, a malformed datetime is the first thing to check.

---

## Next steps


**Filter admin tools for real benchmark runs.** Right now the agent sees `create_scenario` and `delete_scenario`. For production benchmark runs you probably want those hidden so the agent can't modify the scenario it's being tested on. This means adding a filtered tool surface in `mcp_server/server.py` or running a separate server instance without those tools registered.

**Load scenarios from the Excel file.** Right now scenarios are seeded manually via `POST /scenarios/`. The next milestone is a loader that reads the Excel sheet and seeds all scenarios automatically before a benchmark run starts.

---

## If something isn't connecting

1. **Is FastAPI up?** `curl http://localhost:8000/` → should return `{"status": "ok"}`.
2. **Is the right directory?** `uv run python -m mcp_server` must run from the project root or it won't find the module.
3. **Does the server start cleanly?** Run `uv run python -m mcp_server` manually — it should hang silently waiting for input. If it crashes, the traceback tells you what's wrong.
4. **Is the request shape right?** Check the uvicorn terminal for 422 errors — that means the tool call reached FastAPI but with bad field shapes.
