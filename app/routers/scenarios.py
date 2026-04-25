from fastapi import APIRouter, HTTPException, status

from app.models.email import Email, Scenario
from app import store

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("/", response_model=list[Scenario])
def list_scenarios() -> list[Scenario]:
    # returns every scenario currently loaded
    return list(store.scenarios.values())


@router.post("/", response_model=Scenario, status_code=status.HTTP_201_CREATED)
def create_scenario(scenario: Scenario) -> Scenario:
    # loads a scenario (and its fixture emails) from the Excel sheet into memory
    if scenario.scenario_id in store.scenarios:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Scenario {scenario.scenario_id} already exists",
        )

    #this is error catching for if we ever have duplicate emails. 
    payload_ids = [e.email_id for e in scenario.emails]
    if len(payload_ids) != len(set(payload_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate email_ids within scenario payload",
        )
    for email in scenario.emails:
        if email.email_id in store.emails:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email {email.email_id} already exists",
            )

    store.scenarios[scenario.scenario_id] = scenario
    # back-fill scenario_id on every fixture email so they carry attribution like agent-sent ones
    for email in scenario.emails:
        email.scenario_id = scenario.scenario_id
        store.emails[email.email_id] = email
    return scenario


@router.get("/{scenario_id}", response_model=Scenario)
def get_scenario(scenario_id: int) -> Scenario:
    # fetch one scenario (with all its emails) by id
    scenario = store.scenarios.get(scenario_id)
    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario {scenario_id} not found",
        )
    return scenario


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scenario(scenario_id: int) -> None:
    # removes the scenario AND all of its emails from the store
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
    # attach an additional fixture email to an already-loaded scenario
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
    # back-fill scenario_id so the email is attributable even if caller omitted it
    email.scenario_id = scenario_id
    scenario.emails.append(email)
    store.emails[email.email_id] = email
    return email
