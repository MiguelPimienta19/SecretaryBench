from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app import store
from app.models.email import Scenario

client = TestClient(app)

CALENDAR_START = datetime(2026, 4, 15, 0, 0, 0, tzinfo=timezone.utc).isoformat()
EVENT_START = datetime(2026, 4, 16, 9, 0, 0, tzinfo=timezone.utc).isoformat()
EVENT_END = datetime(2026, 4, 16, 10, 0, 0, tzinfo=timezone.utc).isoformat()
# August 1 is 107 days past April 15 — outside the 100-day window
OUTSIDE_START = datetime(2026, 8, 1, 9, 0, 0, tzinfo=timezone.utc).isoformat()
OUTSIDE_END = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc).isoformat()
SCENARIO_ID = 1


def setup_function():
    store.calendars.clear()
    store.scenarios.clear()
    store.scenarios[SCENARIO_ID] = Scenario(scenario_id=SCENARIO_ID, emails=[])


def teardown_function():
    store.calendars.clear()
    store.scenarios.clear()


def _create_calendar():
    return client.post("/calendars/", json={"start_date": CALENDAR_START}).json()


def _create_event(calendar_id: str):
    return client.post(
        f"/calendars/{calendar_id}/events",
        json={"title": "Meeting", "start": EVENT_START, "end": EVENT_END, "scenario_id": SCENARIO_ID},
    ).json()


# --- Calendars ---

def test_create_calendar_returns_201():
    response = client.post("/calendars/", json={"start_date": CALENDAR_START})
    assert response.status_code == 201


def test_create_calendar_returns_expected_fields():
    response = client.post("/calendars/", json={"start_date": CALENDAR_START})
    data = response.json()
    assert "calendar_id" in data
    assert data["events"] == []


def test_get_calendar_returns_200():
    cal = _create_calendar()
    response = client.get(f"/calendars/{cal['calendar_id']}")
    assert response.status_code == 200
    assert response.json()["calendar_id"] == cal["calendar_id"]


def test_get_calendar_not_found_returns_404():
    response = client.get("/calendars/nonexistent")
    assert response.status_code == 404


def test_delete_calendar_returns_204():
    cal = _create_calendar()
    response = client.delete(f"/calendars/{cal['calendar_id']}")
    assert response.status_code == 204


def test_delete_calendar_removes_from_store():
    cal = _create_calendar()
    client.delete(f"/calendars/{cal['calendar_id']}")
    assert client.get(f"/calendars/{cal['calendar_id']}").status_code == 404


def test_delete_calendar_not_found_returns_404():
    response = client.delete("/calendars/nonexistent")
    assert response.status_code == 404


# --- Events ---

def test_create_event_returns_201():
    cal = _create_calendar()
    response = client.post(
        f"/calendars/{cal['calendar_id']}/events",
        json={"title": "Meeting", "start": EVENT_START, "end": EVENT_END, "scenario_id": SCENARIO_ID},
    )
    assert response.status_code == 201


def test_create_event_returns_expected_fields():
    cal = _create_calendar()
    response = client.post(
        f"/calendars/{cal['calendar_id']}/events",
        json={"title": "Meeting", "start": EVENT_START, "end": EVENT_END, "scenario_id": SCENARIO_ID},
    )
    data = response.json()
    assert data["title"] == "Meeting"
    assert "event_id" in data


def test_create_event_with_description():
    cal = _create_calendar()
    response = client.post(
        f"/calendars/{cal['calendar_id']}/events",
        json={"title": "Standup", "description": "Daily sync", "start": EVENT_START, "end": EVENT_END, "scenario_id": SCENARIO_ID},
    )
    assert response.status_code == 201
    assert response.json()["description"] == "Daily sync"


def test_create_event_reversed_times_returns_400():
    cal = _create_calendar()
    response = client.post(
        f"/calendars/{cal['calendar_id']}/events",
        json={"title": "Bad", "start": EVENT_END, "end": EVENT_START, "scenario_id": SCENARIO_ID},
    )
    assert response.status_code == 400


def test_create_event_outside_window_returns_400():
    cal = _create_calendar()
    response = client.post(
        f"/calendars/{cal['calendar_id']}/events",
        json={"title": "Far future", "start": OUTSIDE_START, "end": OUTSIDE_END, "scenario_id": SCENARIO_ID},
    )
    assert response.status_code == 400


def test_create_event_in_missing_calendar_returns_404():
    response = client.post(
        "/calendars/nonexistent/events",
        json={"title": "Meeting", "start": EVENT_START, "end": EVENT_END, "scenario_id": SCENARIO_ID},
    )
    assert response.status_code == 404


def test_list_events_returns_all():
    cal = _create_calendar()
    _create_event(cal["calendar_id"])
    _create_event(cal["calendar_id"])
    response = client.get(f"/calendars/{cal['calendar_id']}/events")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_events_in_missing_calendar_returns_404():
    response = client.get("/calendars/nonexistent/events")
    assert response.status_code == 404


def test_get_event_returns_200():
    cal = _create_calendar()
    event = _create_event(cal["calendar_id"])
    response = client.get(f"/calendars/{cal['calendar_id']}/events/{event['event_id']}")
    assert response.status_code == 200
    assert response.json()["event_id"] == event["event_id"]


def test_get_event_not_found_returns_404():
    cal = _create_calendar()
    response = client.get(f"/calendars/{cal['calendar_id']}/events/nonexistent")
    assert response.status_code == 404


def test_update_event_returns_200():
    cal = _create_calendar()
    event = _create_event(cal["calendar_id"])
    response = client.put(
        f"/calendars/{cal['calendar_id']}/events/{event['event_id']}",
        json={"title": "Updated", "start": EVENT_START, "end": EVENT_END, "scenario_id": SCENARIO_ID},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"


def test_update_event_not_found_returns_404():
    cal = _create_calendar()
    response = client.put(
        f"/calendars/{cal['calendar_id']}/events/nonexistent",
        json={"title": "Ghost", "start": EVENT_START, "end": EVENT_END, "scenario_id": SCENARIO_ID},
    )
    assert response.status_code == 404


def test_delete_event_returns_204():
    cal = _create_calendar()
    event = _create_event(cal["calendar_id"])
    response = client.delete(f"/calendars/{cal['calendar_id']}/events/{event['event_id']}")
    assert response.status_code == 204


def test_delete_event_removes_from_calendar():
    cal = _create_calendar()
    event = _create_event(cal["calendar_id"])
    client.delete(f"/calendars/{cal['calendar_id']}/events/{event['event_id']}")
    assert client.get(f"/calendars/{cal['calendar_id']}/events/{event['event_id']}").status_code == 404


def test_delete_event_not_found_returns_404():
    cal = _create_calendar()
    response = client.delete(f"/calendars/{cal['calendar_id']}/events/nonexistent")
    assert response.status_code == 404
