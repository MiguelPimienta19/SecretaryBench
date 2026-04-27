from typing import Dict
from app.models.todo import TodoResponse
from app.models.email import Email, Scenario

todos_db: Dict[str, TodoResponse] = {}

calendars: Dict[str, dict] = {}

scenarios: Dict[int, Scenario] = {}
emails: Dict[int, Email] = {}
