from fastapi import APIRouter, HTTPException, status

from app.models.email import Email
from app import store

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("/", response_model=list[Email])
def list_emails() -> list[Email]:
    return list(store.emails.values())


@router.get("/{email_id}", response_model=Email)
def get_email(email_id: int) -> Email:
    email = store.emails.get(email_id)
    if email is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Email {email_id} not found")
    return email


@router.delete("/{email_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_email(email_id: int) -> None:
    email = store.emails.pop(email_id, None)
    if email is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Email {email_id} not found")
    for scenario in store.scenarios.values():
        scenario.emails = [e for e in scenario.emails if e.email_id != email_id]
