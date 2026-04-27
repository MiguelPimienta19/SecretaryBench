from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start: datetime
    end: datetime


class EventResponse(BaseModel):
    event_id: str
    title: str
    description: Optional[str] = None
    start: datetime
    end: datetime


class CalendarCreate(BaseModel):
    start_date: datetime


class CalendarResponse(BaseModel):
    calendar_id: str
    start_date: datetime
    events: list[EventResponse] = []
