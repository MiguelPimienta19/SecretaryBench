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
    "emails": [],
    "success_criteria": "Agent responds correctly",
}


def setup_function():
    store.emails.clear()
    store.scenarios.clear()


# --- List ---

def test_list_scenarios_empty():
    response = client.get("/scenarios/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_scenarios_returns_all():
    client.post("/scenarios/", json=SAMPLE_SCENARIO)
    client.post("/scenarios/", json={**SAMPLE_SCENARIO, "scenario_id": 2})
    response = client.get("/scenarios/")
    assert response.status_code == 200
    assert len(response.json()) == 2


# --- Create ---

def test_create_scenario_returns_201():
    response = client.post("/scenarios/", json=SAMPLE_SCENARIO)
    assert response.status_code == 201


def test_create_scenario_returns_expected_fields():
    response = client.post("/scenarios/", json=SAMPLE_SCENARIO)
    data = response.json()
    assert data["scenario_id"] == 1
    assert data["success_criteria"] == "Agent responds correctly"
    assert data["emails"] == []


def test_create_scenario_with_null_optional_fields():
    response = client.post("/scenarios/", json={"scenario_id": 2, "emails": []})
    assert response.status_code == 201
    data = response.json()
    assert data["success_criteria"] is None
    assert data["puzzle_summary"] is None


def test_create_scenario_registers_emails_in_store():
    scenario = {**SAMPLE_SCENARIO, "emails": [SAMPLE_EMAIL]}
    client.post("/scenarios/", json=scenario)
    assert client.get("/emails/1").status_code == 200


def test_create_scenario_duplicate_id_returns_409():
    client.post("/scenarios/", json=SAMPLE_SCENARIO)
    response = client.post("/scenarios/", json=SAMPLE_SCENARIO)
    assert response.status_code == 409


# --- Get ---

def test_get_scenario_returns_200():
    client.post("/scenarios/", json=SAMPLE_SCENARIO)
    response = client.get("/scenarios/1")
    assert response.status_code == 200
    assert response.json()["scenario_id"] == 1


def test_get_scenario_not_found_returns_404():
    response = client.get("/scenarios/999")
    assert response.status_code == 404


# --- Delete ---

def test_delete_scenario_returns_204():
    client.post("/scenarios/", json=SAMPLE_SCENARIO)
    response = client.delete("/scenarios/1")
    assert response.status_code == 204


def test_delete_scenario_removes_from_store():
    client.post("/scenarios/", json=SAMPLE_SCENARIO)
    client.delete("/scenarios/1")
    assert client.get("/scenarios/1").status_code == 404


def test_delete_scenario_removes_its_emails():
    scenario = {**SAMPLE_SCENARIO, "emails": [SAMPLE_EMAIL]}
    client.post("/scenarios/", json=scenario)
    client.delete("/scenarios/1")
    assert client.get("/emails/1").status_code == 404


def test_delete_scenario_not_found_returns_404():
    response = client.delete("/scenarios/999")
    assert response.status_code == 404


# --- Add email ---

def test_add_email_to_scenario_returns_201():
    client.post("/scenarios/", json=SAMPLE_SCENARIO)
    response = client.post("/scenarios/1/emails", json=SAMPLE_EMAIL)
    assert response.status_code == 201
    assert response.json()["email_id"] == 1


def test_add_email_to_scenario_registers_in_emails_store():
    client.post("/scenarios/", json=SAMPLE_SCENARIO)
    client.post("/scenarios/1/emails", json=SAMPLE_EMAIL)
    assert client.get("/emails/1").status_code == 200


def test_add_email_appears_in_scenario():
    client.post("/scenarios/", json=SAMPLE_SCENARIO)
    client.post("/scenarios/1/emails", json=SAMPLE_EMAIL)
    scenario = client.get("/scenarios/1").json()
    assert any(e["email_id"] == 1 for e in scenario["emails"])


def test_add_duplicate_email_returns_409():
    client.post("/scenarios/", json=SAMPLE_SCENARIO)
    client.post("/scenarios/1/emails", json=SAMPLE_EMAIL)
    response = client.post("/scenarios/1/emails", json=SAMPLE_EMAIL)
    assert response.status_code == 409


def test_add_email_to_missing_scenario_returns_404():
    response = client.post("/scenarios/999/emails", json=SAMPLE_EMAIL)
    assert response.status_code == 404
