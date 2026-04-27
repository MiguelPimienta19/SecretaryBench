from fastapi import APIRouter, HTTPException, status

from app.models.email import Email, Scenario
from app import store

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("/", response_model=list[Scenario])
def list_scenarios() -> list[Scenario]:
    return list(store.scenarios.values())


@router.post("/", response_model=Scenario, status_code=status.HTTP_201_CREATED)
def create_scenario(scenario: Scenario) -> Scenario:
    if scenario.scenario_id in store.scenarios:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Scenario {scenario.scenario_id} already exists",
        )
    store.scenarios[scenario.scenario_id] = scenario
    for email in scenario.emails:
        store.emails[email.email_id] = email
    return scenario


@router.get("/{scenario_id}", response_model=Scenario)
def get_scenario(scenario_id: int) -> Scenario:
    scenario = store.scenarios.get(scenario_id)
    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario {scenario_id} not found",
        )
    return scenario


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scenario(scenario_id: int) -> None:
    scenario = store.scenarios.pop(scenario_id, None)
    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario {scenario_id} not found",
        )
    for email in scenario.emails:
        store.emails.pop(email.email_id, None)


@router.post("/{scenario_id}/emails", response_model=Email, status_code=status.HTTP_201_CREATED)
def add_email_to_scenario(scenario_id: int, email: Email) -> Email:
    scenario = store.scenarios.get(scenario_id)
    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario {scenario_id} not found",
        )
    if email.email_id in store.emails:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email {email.email_id} already exists",
        )
    scenario.emails.append(email)
    store.emails[email.email_id] = email
    return email
