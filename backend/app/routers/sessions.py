"""Simulation session endpoints."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.auth import get_current_user
from app.db import get_db
from app.models import Scenario, SimulationSession, User
from app.schemas import ScenarioOut, SessionCreate, SessionOut
from app.services.scenario_engine import ScenarioEngine

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _public_scenario(sc: Scenario) -> ScenarioOut:
    """Convert a Scenario to the public-facing shape, stripping server-only fields."""
    payload = dict(sc.payload)
    for key in ("privileged_ids", "counterpart_ids", "privileged_id",
                "counterpart_id", "privileged_base_rate", "pairs",
                "merit_edge", "strong_ids", "weak_ids"):
        payload.pop(key, None)
    return ScenarioOut(
        id=sc.id,
        scene_type=sc.scene_type,
        order_index=sc.order_index,
        timed=sc.timed,
        payload=payload,
    )


def _serialise_session(sess: SimulationSession) -> SessionOut:
    return SessionOut(
        id=sess.id,
        context=sess.context,  # type: ignore[arg-type]
        started_at=sess.started_at,
        completed_at=sess.completed_at,
        scenarios=[_public_scenario(sc) for sc in sess.scenarios],
    )


@router.post("/", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> SessionOut:
    engine = ScenarioEngine()
    plans = engine.build_scenes(context=payload.context)

    sess = SimulationSession(user_id=user.id, context=payload.context)
    db.add(sess)
    db.flush()  # need sess.id before adding scenarios

    for idx, plan in enumerate(plans):
        sc = Scenario(
            session_id=sess.id,
            scene_type=plan.scene_type,
            order_index=idx,
            timed=plan.timed,
            variant_dimension=plan.variant_dimension,
            payload=plan.server_payload,
        )
        db.add(sc)

    db.commit()
    db.refresh(sess)
    return _serialise_session(sess)


@router.get("/", response_model=list[SessionOut])
def list_sessions(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> list[SessionOut]:
    """List the current user's sessions, most recent first."""
    from sqlalchemy import select

    stmt = (
        select(SimulationSession)
        .where(SimulationSession.user_id == user.id)
        .order_by(SimulationSession.started_at.desc())
    )
    rows = db.scalars(stmt).all()
    return [_serialise_session(s) for s in rows]


@router.get("/{session_id}", response_model=SessionOut)
def get_session(
    session_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> SessionOut:
    sess = db.get(SimulationSession, session_id)
    if sess is None or sess.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return _serialise_session(sess)


@router.post("/{session_id}/complete", response_model=SessionOut)
def complete_session(
    session_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> SessionOut:
    sess = db.get(SimulationSession, session_id)
    if sess is None or sess.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    if sess.completed_at is None:
        sess.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(sess)
    return _serialise_session(sess)
