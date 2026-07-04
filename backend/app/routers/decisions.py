"""Decision submission endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.auth import get_current_user
from app.db import get_db
from app.models import Decision, Scenario, SimulationSession, User
from app.schemas import DecisionCreate, DecisionOut
from app.services.scenario_engine import ScenarioEngine

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.post("/", response_model=DecisionOut, status_code=status.HTTP_201_CREATED)
def submit_decision(
    payload: DecisionCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> DecisionOut:
    scenario = db.get(Scenario, payload.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found.")

    sess = db.get(SimulationSession, scenario.session_id)
    if sess is None or sess.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your scenario.")

    if scenario.decision is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Decision already submitted for this scenario.",
        )

    favoured = ScenarioEngine.evaluate_decision(
        scene_type=scenario.scene_type,
        server_payload=scenario.payload,
        choice=payload.choice,
    )

    decision = Decision(
        scenario_id=scenario.id,
        choice=payload.choice,
        favoured_privileged=favoured,
        elapsed_ms=payload.elapsed_ms,
        justification=payload.justification,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return DecisionOut.model_validate(decision)
