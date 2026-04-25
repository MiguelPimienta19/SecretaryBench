import uuid
from datetime import timedelta

from fastapi import APIRouter, HTTPException, status

from app.models.calendar import (
    CalendarCreate,
    CalendarResponse,
    EventCreate,
    EventResponse,
)
from app import store

router = APIRouter(prefix="/calendars", tags=["calendars"])

CALENDAR_DURATION_DAYS = 100


def _validate_event(data: EventCreate, calendar: CalendarResponse):
    # sanity check: event times ordered + inside the 100-day window
    if data.start >= data.end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event start must be before end")

    window_start = calendar.start_date
    window_end = window_start + timedelta(days=CALENDAR_DURATION_DAYS)

    if data.start < window_start or data.end > window_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event must fall within the 100-day window: {window_start} to {window_end}",
        )


def _find_event(calendar: CalendarResponse, event_id: str) -> EventResponse | None:
    # O(n) scan — fine at benchmark scale
    for event in calendar.events:
        if event.event_id == event_id:
            return event
    return None


# --- Calendar endpoints ---

@router.post("/", response_model=CalendarResponse, status_code=status.HTTP_201_CREATED)
def create_calendar(data: CalendarCreate):
    # creates a fresh 100-day calendar window starting from start_date
    calendar_id = str(uuid.uuid4())
    calendar = CalendarResponse(
        calendar_id=calendar_id,
        start_date=data.start_date,
        events=[],
    )
    store.calendars[calendar_id] = calendar
    return calendar


@router.get("/{calendar_id}", response_model=CalendarResponse)
def get_calendar(calendar_id: str):
    # returns the calendar along with all of its events
    calendar = store.calendars.get(calendar_id)
    if calendar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")
    return calendar


@router.delete("/{calendar_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_calendar(calendar_id: str):
    # deletes the calendar and every event on it
    if calendar_id not in store.calendars:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")
    del store.calendars[calendar_id]


# --- Event endpoints ---

@router.post(
    "/{calendar_id}/events",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_event(calendar_id: str, data: EventCreate):
    # add a new event; must fall inside the 100-day window and reference a real scenario
    calendar = store.calendars.get(calendar_id)
    if calendar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    if data.scenario_id not in store.scenarios:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario {data.scenario_id} not found",
        )

    _validate_event(data, calendar)

    event_id = str(uuid.uuid4())
    event = EventResponse(
        event_id=event_id,
        title=data.title,
        description=data.description,
        start=data.start,
        end=data.end,
        scenario_id=data.scenario_id,
    )
    calendar.events.append(event)
    return event


@router.get(
    "/{calendar_id}/events",
    response_model=list[EventResponse],
)
def list_events(calendar_id: str):
    # every event on a given calendar
    calendar = store.calendars.get(calendar_id)
    if calendar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")
    return calendar.events


@router.get(
    "/{calendar_id}/events/{event_id}",
    response_model=EventResponse,
)
def get_event(calendar_id: str, event_id: str):
    # fetch a single event by id
    calendar = store.calendars.get(calendar_id)
    if calendar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    event = _find_event(calendar, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.put(
    "/{calendar_id}/events/{event_id}",
    response_model=EventResponse,
)
def update_event(calendar_id: str, event_id: str, data: EventCreate):
    # full replace — the caller must send every field, not just the ones they want to change
    calendar = store.calendars.get(calendar_id)
    if calendar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    existing = _find_event(calendar, event_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if data.scenario_id not in store.scenarios:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario {data.scenario_id} not found",
        )

    _validate_event(data, calendar)

    updated_event = EventResponse(
        event_id=event_id,
        title=data.title,
        description=data.description,
        start=data.start,
        end=data.end,
        scenario_id=data.scenario_id,
    )
    calendar.events = [e if e.event_id != event_id else updated_event for e in calendar.events]
    return updated_event


@router.delete(
    "/{calendar_id}/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_event(calendar_id: str, event_id: str):
    # removes a single event from a calendar
    calendar = store.calendars.get(calendar_id)
    if calendar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    existing = _find_event(calendar, event_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    calendar.events = [e for e in calendar.events if e.event_id != event_id]
