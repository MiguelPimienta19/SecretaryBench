import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.models.todo import TodoCreate, TodoUpdate, TodoResponse
from app import store

router = APIRouter(prefix="/todos", tags=["todos"])


def _calendar_event_exists(event_id: str) -> bool:
    # walks every calendar to confirm the event_id is real somewhere
    for cal in store.calendars.values():
        for evt in cal.events:
            if evt.event_id == event_id:
                return True
    return False


@router.post("/", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
def create_todo(payload: TodoCreate) -> TodoResponse:
    # creates a new todo. server generates the UUID and timestamp.
    # validates that scenario_id (and calendar_event_id, if passed) point to real objects.
    if payload.scenario_id not in store.scenarios:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario {payload.scenario_id} not found",
        )
    if payload.calendar_event_id is not None and not _calendar_event_exists(payload.calendar_event_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calendar event '{payload.calendar_event_id}' not found",
        )

    todo_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    todo = TodoResponse(
        id=todo_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        created_at=now,
        completed=False,
        scenario_id=payload.scenario_id,
        calendar_event_id=payload.calendar_event_id,
    )
    store.todos_db[todo_id] = todo
    return todo


@router.get("/", response_model=list[TodoResponse])
def list_todos() -> list[TodoResponse]:
    # returns every todo across all scenarios
    return list(store.todos_db.values())


@router.get("/{todo_id}", response_model=TodoResponse)
def get_todo(todo_id: str) -> TodoResponse:
    # fetch one todo by id
    todo = store.todos_db.get(todo_id)
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Todo '{todo_id}' not found.")
    return todo


@router.patch("/{todo_id}", response_model=TodoResponse)
def update_todo(todo_id: str, payload: TodoUpdate) -> TodoResponse:
    # partial update — only the fields you send get changed. omitted fields stay as they were.
    todo = store.todos_db.get(todo_id)
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Todo '{todo_id}' not found.")

    updated_data = todo.model_dump()
    for field, value in payload.model_dump(exclude_unset=True).items():
        updated_data[field] = value

    updated_todo = TodoResponse(**updated_data)
    store.todos_db[todo_id] = updated_todo
    return updated_todo


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: str) -> None:
    # removes a todo by id
    if todo_id not in store.todos_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Todo '{todo_id}' not found.")
    del store.todos_db[todo_id]
