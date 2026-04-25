from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app import store

client = TestClient(app)

BASE_DATE = datetime(2026, 4, 15, 10, 0, 0, tzinfo=timezone.utc).isoformat()

SAMPLE_EMAIL = {
    "email_id": 1,
    "subject": "Hello",
    "created_at": BASE_DATE,
    "sender": "alice@example.com",
    "recipients": ["bob@example.com"],
    "body": "Hi there",
}

SAMPLE_SCENARIO = {
    "scenario_id": 1,
    "emails": [SAMPLE_EMAIL],
}


def setup_function():
    store.emails.clear()
    store.scenarios.clear()


# --- List ---

def test_list_emails_empty():
    response = client.get("/emails/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_emails_returns_all():
    client.post("/scenarios/", json=SAMPLE_SCENARIO)
    response = client.get("/emails/")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["email_id"] == 1


# --- Get ---

def test_get_email_returns_200():
    client.post("/scenarios/", json=SAMPLE_SCENARIO)
    response = client.get("/emails/1")
    assert response.status_code == 200
    assert response.json()["email_id"] == 1
    assert response.json()["subject"] == "Hello"


def test_get_email_not_found_returns_404():
    response = client.get("/emails/999")
    assert response.status_code == 404


# --- Send (POST) ---

def _send_payload(**overrides) -> dict:
    payload = {
        "subject": "Re: Hello",
        "sender": "bob@example.com",
        "recipients": ["alice@example.com"],
        "body": "Got your message",
        "scenario_id": 1,
    }
    payload.update(overrides)
    return payload


def test_send_email_returns_201():
    client.post("/scenarios/", json=SAMPLE_SCENARIO)
    response = client.post("/emails/", json=_send_payload())
    assert response.status_code == 201


def test_send_email_returns_expected_fields():
    client.post("/scenarios/", json=SAMPLE_SCENARIO)
    data = client.post("/emails/", json=_send_payload()).json()
    assert data["subject"] == "Re: Hello"
    assert data["sender"] == "bob@example.com"
    assert data["scenario_id"] == 1
    assert "email_id" in data
    assert "created_at" in data


def test_send_email_missing_scenario_id_returns_422():
    client.post("/scenarios/", json=SAMPLE_SCENARIO)
    payload = _send_payload()
    del payload["scenario_id"]
    response = client.post("/emails/", json=payload)
    assert response.status_code == 422


def test_send_email_nonexistent_scenario_returns_404():
    response = client.post("/emails/", json=_send_payload(scenario_id=999))
    assert response.status_code == 404


def test_send_email_auto_id_is_max_plus_one():
    # fixture seeds email_id=1; next agent-sent email should get id=2
    client.post("/scenarios/", json=SAMPLE_SCENARIO)
    first = client.post("/emails/", json=_send_payload()).json()
    assert first["email_id"] == 2
    second = client.post("/emails/", json=_send_payload()).json()
    assert second["email_id"] == 3


def test_send_email_persists_to_store():
    client.post("/scenarios/", json=SAMPLE_SCENARIO)
    sent = client.post("/emails/", json=_send_payload()).json()
    fetched = client.get(f"/emails/{sent['email_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["email_id"] == sent["email_id"]
