"""SQLAlchemy ORM models.

The schema captures the entities described in the proposal:

- ``User``: a manager using the platform.
- ``SimulationSession``: one run-through of a simulation context (e.g., Hiring).
- ``Scenario``: a single scene encountered within a session, including the
  variant pair shown to the user.
- ``Decision``: the manager's response to a scenario.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sessions: Mapped[list[SimulationSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class SimulationSession(Base):
    """A single end-to-end simulation run by a manager."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    context: Mapped[str] = mapped_column(String(32), nullable=False)  # 'hiring' | 'promotion' | 'review'
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")
    scenarios: Mapped[list[Scenario]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Scenario.order_index"
    )


class Scenario(Base):
    """A scene within a session.

    ``payload`` carries the candidate-profile pair (or other scene content) as
    JSON so the schema can evolve without migrations. ``variant_dimension``
    records which demographic dimension was varied between the paired profiles
    (e.g., 'gender', 'ethnicity', 'education_prestige').
    """

    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    scene_type: Mapped[str] = mapped_column(String(48), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    timed: Mapped[bool] = mapped_column(default=False, nullable=False)
    variant_dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    session: Mapped[SimulationSession] = relationship(back_populates="scenarios")
    decision: Mapped[Decision | None] = relationship(
        back_populates="scenario", cascade="all, delete-orphan", uselist=False
    )


class Decision(Base):
    """The manager's response to a scenario, plus diagnostic metadata."""

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(
        ForeignKey("scenarios.id"), nullable=False, unique=True
    )

    # Generic decision record. For "select N of M" scenes, ``choice`` is a
    # JSON list of selected candidate IDs. For binary picks, it's the ID of
    # the chosen profile.
    choice: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Whether the choice favoured the variant with the privileged demographic
    # signal. Computed by the scenario engine when the decision is recorded.
    favoured_privileged: Mapped[bool | None] = mapped_column(nullable=True)

    # Elapsed milliseconds from scenario presentation to submission.
    elapsed_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Free-text justification (only present for Justified Decision scenes).
    justification: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    scenario: Mapped[Scenario] = relationship(back_populates="decision")


class AggregateStat(Base):
    """Anonymised aggregate statistics used for cross-user benchmarking.

    Each row stores a summary point that can be queried to plot the platform-wide
    distribution against which an individual manager's results are shown.
    """

    __tablename__ = "aggregate_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scene_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    variant_dimension: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    favoured_rate: Mapped[float] = mapped_column(Float, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
