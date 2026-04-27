from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Email(BaseModel):
    subject: str
    created_at: datetime
    sender: str
    recipients: list[str]
    body: str
    email_id: int


class Scenario(BaseModel):
    emails: list[Email] = []
    scenario_id: int
    success_criteria: Optional[str] = None
    puzzle_summary: Optional[str] = None
