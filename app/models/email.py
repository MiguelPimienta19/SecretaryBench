from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class EmailCreate(BaseModel):
    # what the agent sends when writing a new email. server fills in email_id and created_at.
    # scenario_id is required so every agent-sent email is attributable.
    subject: str
    sender: str
    recipients: list[str]
    body: str
    scenario_id: int


class Email(BaseModel):
    subject: str
    created_at: datetime
    sender: str
    recipients: list[str]
    body: str
    email_id: int
    scenario_id: Optional[int]= None


class Scenario(BaseModel):
    emails: list[Email] = []
    scenario_id: int
    success_criteria: Optional[str] = None
    puzzle_summary: Optional[str] = None
