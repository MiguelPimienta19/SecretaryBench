import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.models.todo import TodoCreate, TodoUpdate, TodoResponse
from app import store

router = APIRouter(prefix="/todos", tags=["todos"])


@router.post("/", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
def create_todo(payload: TodoCreate) -> TodoResponse:
    todo_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    todo = TodoResponse(
        id=todo_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        created_at=now,
        completed=False,
    )
    store.todos_db[todo_id] = todo
    return todo


@router.get("/", response_model=list[TodoResponse])
def list_todos() -> list[TodoResponse]:
    return list(store.todos_db.values())


@router.get("/{todo_id}", response_model=TodoResponse)
def get_todo(todo_id: str) -> TodoResponse:
    todo = store.todos_db.get(todo_id)
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Todo '{todo_id}' not found.")
    return todo


@router.put("/{todo_id}", response_model=TodoResponse)
def update_todo(todo_id: str, payload: TodoUpdate) -> TodoResponse:
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
    if todo_id not in store.todos_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Todo '{todo_id}' not found.")
    del store.todos_db[todo_id]
