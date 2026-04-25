from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.models.email import Email, EmailCreate
from app import store

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("/", response_model=list[Email])
def list_emails() -> list[Email]:
    # returns every email in the system (fixture-loaded + agent-sent)
    return list(store.emails.values())


@router.get("/{email_id}", response_model=Email)
def get_email(email_id: int) -> Email:
    # fetch one email by id
    email = store.emails.get(email_id)
    if email is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Email {email_id} not found")
    return email


@router.post("/", response_model=Email, status_code=status.HTTP_201_CREATED)
def send_email(payload: EmailCreate) -> Email:
    # agent-facing write. server assigns email_id as (highest existing id) + 1, always monotonic.
    if payload.scenario_id not in store.scenarios:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario {payload.scenario_id} not found",
        )

    new_id = max(store.emails.keys(), default=0) + 1
    email = Email(
        email_id=new_id,
        created_at=datetime.now(timezone.utc),
        subject=payload.subject,
        sender=payload.sender,
        recipients=payload.recipients,
        body=payload.body,
        scenario_id=payload.scenario_id,
    )
    store.emails[new_id] = email
    return email
