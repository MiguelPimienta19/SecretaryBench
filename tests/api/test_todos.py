from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app import store

client = TestClient(app)

FUTURE_DATE = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()


def setup_function():
    """Clear the in-memory store before each test."""
    store.todos_db.clear()


# --- Health check ---

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# --- Create ---

def test_create_todo_returns_201():
    response = client.post("/todos/", json={"title": "Buy milk", "due_date": FUTURE_DATE})
    assert response.status_code == 201


def test_create_todo_returns_expected_fields():
    response = client.post("/todos/", json={"title": "Buy milk", "due_date": FUTURE_DATE})
    data = response.json()
    assert data["title"] == "Buy milk"
    assert data["completed"] is False
    assert "id" in data
    assert "created_at" in data
    assert data["description"] is None


def test_create_todo_with_description():
    response = client.post(
        "/todos/",
        json={"title": "Read book", "description": "Chapter 3", "due_date": FUTURE_DATE},
    )
    assert response.status_code == 201
    assert response.json()["description"] == "Chapter 3"


def test_create_todo_missing_title_returns_422():
    response = client.post("/todos/", json={"due_date": FUTURE_DATE})
    assert response.status_code == 422
    assert "error" in response.json()


def test_create_todo_missing_due_date_returns_422():
    response = client.post("/todos/", json={"title": "No date"})
    assert response.status_code == 422


def test_create_todo_invalid_due_date_returns_422():
    response = client.post("/todos/", json={"title": "Bad date", "due_date": "not-a-date"})
    assert response.status_code == 422


# --- List ---

def test_list_todos_empty():
    response = client.get("/todos/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_todos_returns_all():
    client.post("/todos/", json={"title": "Task A", "due_date": FUTURE_DATE})
    client.post("/todos/", json={"title": "Task B", "due_date": FUTURE_DATE})
    response = client.get("/todos/")
    assert response.status_code == 200
    assert len(response.json()) == 2


# --- Get by ID ---

def test_get_todo_by_id():
    created = client.post("/todos/", json={"title": "Find me", "due_date": FUTURE_DATE}).json()
    response = client.get(f"/todos/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_todo_not_found_returns_404():
    response = client.get("/todos/nonexistent-id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# --- Update ---

def test_update_todo_title():
    created = client.post("/todos/", json={"title": "Old title", "due_date": FUTURE_DATE}).json()
    response = client.put(f"/todos/{created['id']}", json={"title": "New title"})
    assert response.status_code == 200
    assert response.json()["title"] == "New title"


def test_update_todo_completed():
    created = client.post("/todos/", json={"title": "Finish me", "due_date": FUTURE_DATE}).json()
    response = client.put(f"/todos/{created['id']}", json={"completed": True})
    assert response.status_code == 200
    assert response.json()["completed"] is True


def test_update_todo_preserves_unchanged_fields():
    created = client.post(
        "/todos/",
        json={"title": "Stable", "description": "Keep this", "due_date": FUTURE_DATE},
    ).json()
    response = client.put(f"/todos/{created['id']}", json={"completed": True})
    updated = response.json()
    assert updated["title"] == "Stable"
    assert updated["description"] == "Keep this"


def test_update_todo_not_found_returns_404():
    response = client.put("/todos/nonexistent-id", json={"title": "Ghost"})
    assert response.status_code == 404


# --- Delete ---

def test_delete_todo():
    created = client.post("/todos/", json={"title": "Delete me", "due_date": FUTURE_DATE}).json()
    response = client.delete(f"/todos/{created['id']}")
    assert response.status_code == 204


def test_delete_todo_removes_from_store():
    created = client.post("/todos/", json={"title": "Gone", "due_date": FUTURE_DATE}).json()
    client.delete(f"/todos/{created['id']}")
    response = client.get(f"/todos/{created['id']}")
    assert response.status_code == 404


def test_delete_todo_not_found_returns_404():
    response = client.delete("/todos/nonexistent-id")
    assert response.status_code == 404
