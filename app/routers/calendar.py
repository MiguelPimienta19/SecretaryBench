import uuid
from datetime import timedelta

from fastapi import APIRouter, HTTPException, status

from app.models.calendar import (
    CalendarCreate,
    CalendarResponse,
    EventCreate,
    EventResponse,
)
from app.store import calendars

router = APIRouter(prefix="/calendars", tags=["calendars"])

CALENDAR_DURATION_DAYS = 100


def _validate_event(data: EventCreate, calendar: dict):
    if data.start >= data.end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event start must be before end")

    window_start = calendar["start_date"]
    window_end = window_start + timedelta(days=CALENDAR_DURATION_DAYS)

    if data.start < window_start or data.end > window_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event must fall within the 100-day window: {window_start} to {window_end}",
        )


# --- Calendar endpoints ---

@router.post("/", response_model=CalendarResponse, status_code=status.HTTP_201_CREATED)
def create_calendar(data: CalendarCreate):
    calendar_id = str(uuid.uuid4())
    calendar = {
        "calendar_id": calendar_id,
        "start_date": data.start_date,
        "events": {},
    }
    calendars[calendar_id] = calendar
    return CalendarResponse(
        calendar_id=calendar_id,
        start_date=data.start_date,
        events=[],
    )


@router.get("/{calendar_id}", response_model=CalendarResponse)
def get_calendar(calendar_id: str):
    if calendar_id not in calendars:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    calendar = calendars[calendar_id]

    return CalendarResponse(
        calendar_id=calendar["calendar_id"],
        start_date=calendar["start_date"],
        events=list(calendar["events"].values()),
    )


@router.delete("/{calendar_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_calendar(calendar_id: str):
    if calendar_id not in calendars:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    del calendars[calendar_id]


# --- Event endpoints ---

@router.post(
    "/{calendar_id}/events",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_event(calendar_id: str, data: EventCreate):
    if calendar_id not in calendars:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    calendar = calendars[calendar_id]
    _validate_event(data, calendar)

    event_id = str(uuid.uuid4())
    event = {
        "event_id": event_id,
        "title": data.title,
        "description": data.description,
        "start": data.start,
        "end": data.end,
    }
    calendar["events"][event_id] = event

    return EventResponse(**event)


@router.get(
    "/{calendar_id}/events",
    response_model=list[EventResponse],
)
def list_events(calendar_id: str):
    if calendar_id not in calendars:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    return list(calendars[calendar_id]["events"].values())


@router.get(
    "/{calendar_id}/events/{event_id}",
    response_model=EventResponse,
)
def get_event(calendar_id: str, event_id: str):
    if calendar_id not in calendars:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    calendar = calendars[calendar_id]

    if event_id not in calendar["events"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    return EventResponse(**calendar["events"][event_id])


@router.put(
    "/{calendar_id}/events/{event_id}",
    response_model=EventResponse,
)
def update_event(calendar_id: str, event_id: str, data: EventCreate):
    if calendar_id not in calendars:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    calendar = calendars[calendar_id]

    if event_id not in calendar["events"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    _validate_event(data, calendar)

    updated_event = {
        "event_id": event_id,
        "title": data.title,
        "description": data.description,
        "start": data.start,
        "end": data.end,
    }
    calendar["events"][event_id] = updated_event

    return EventResponse(**updated_event)


@router.delete(
    "/{calendar_id}/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_event(calendar_id: str, event_id: str):
    if calendar_id not in calendars:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    calendar = calendars[calendar_id]

    if event_id not in calendar["events"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    del calendar["events"][event_id]
