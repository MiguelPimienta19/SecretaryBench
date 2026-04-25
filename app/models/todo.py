from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TodoCreate(BaseModel):
    # what the agent sends. scenario_id is required so every todo is attributable.
    title: str
    description: Optional[str] = None
    due_date: datetime
    scenario_id: int
    calendar_event_id: Optional[str] = None


class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    completed: Optional[bool] = None


class TodoResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    due_date: datetime
    created_at: datetime
    completed: bool = False
    scenario_id: Optional[int] = None #if mult scenarios used to see if agent made it for correct scenario
    calendar_event_id: Optional[str] = None #need linking to where the calendar event is. Available to change.