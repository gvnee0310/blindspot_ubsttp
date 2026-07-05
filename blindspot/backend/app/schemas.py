"""Pydantic schemas for HTTP request and response bodies."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

# --- Auth ---


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    display_name: str

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserOut


# --- Sessions & scenarios ---


SessionContext = Literal["hiring", "promotion", "review"]


class SessionCreate(BaseModel):
    context: SessionContext


class ScenarioOut(BaseModel):
    """A scenario as delivered to the frontend. The variant pairing and
    privileged-variant identity are *not* exposed here — only the visible
    content the manager should see.
    """

    id: int
    scene_type: str
    order_index: int
    timed: bool
    payload: dict[str, Any]

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    id: int
    context: SessionContext
    started_at: datetime
    completed_at: datetime | None
    scenarios: list[ScenarioOut]

    model_config = {"from_attributes": True}


# --- Decisions ---


class DecisionCreate(BaseModel):
    """Request body for submitting a manager's response to a scenario."""

    scenario_id: int
    # For multi-select scenes, ``choice`` is a list of candidate IDs.
    # For single-select scenes, it's a single ID. The payload structure is
    # interpreted by the scenario engine based on the scene type.
    choice: dict[str, Any]
    elapsed_ms: int | None = None
    justification: str | None = None


class DecisionOut(BaseModel):
    id: int
    scenario_id: int
    choice: dict[str, Any]
    favoured_privileged: bool | None
    elapsed_ms: int | None
    justification: str | None
    submitted_at: datetime

    model_config = {"from_attributes": True}


# --- Debrief ---


class ProportionOut(BaseModel):
    favoured: int
    total: int
    proportion: float | None
    ci_low: float | None
    ci_high: float | None


class SceneBreakdownOut(BaseModel):
    scene_type: str
    n_decisions: int
    n_favoured: int
    n_against: int
    n_ambiguous: int
    proportion: ProportionOut
    expected_rate: float | None = None


class PairedComparisonOut(BaseModel):
    n_pairs: int
    mean_difference: float
    sd_difference: float | None
    t_statistic: float | None
    p_value: float | None
    ci_low: float | None
    ci_high: float | None


class TimedSplitOut(BaseModel):
    """Untimed vs timed selection rates, with a difference + reliability tier."""

    untimed: ProportionOut
    timed: ProportionOut
    difference: float | None = None
    diff_ci_low: float | None = None
    diff_ci_high: float | None = None
    reliability: str = "too_thin"


class DimensionBreakdownOut(BaseModel):
    dimension: str
    group_a: str
    group_b: str
    n_favoured_a: int
    n_trials: int


class DescriptiveOut(BaseModel):
    """Descriptive analytics block (Week 4 deliverable)."""

    overall: ProportionOut
    by_scene: list[SceneBreakdownOut]
    paired_ratings: PairedComparisonOut | None = None
    n_ties: int = 0
    timed_split: TimedSplitOut | None = None
    by_dimension: list[DimensionBreakdownOut] = []
    n_conflict: int = 0
    n_conflict_overrode_merit: int = 0


class RevealItem(BaseModel):
    """One matched comparison, unmasked for the post-session reveal."""

    scene_type: str
    headline: str
    privileged_names: list[str]
    counterpart_names: list[str]
    what_you_did: str


class BayesianOut(BaseModel):
    """PyMC posterior block (Week 5 deliverable)."""

    posterior_mean: float
    hdi_low: float
    hdi_high: float
    prob_p_above_half: float
    prob_p_above_60: float
    prob_p_below_40: float
    prob_in_rope: float
    prior_prob_in_rope: float
    rope_low: float
    rope_high: float
    n_observations: int
    n_favoured: int
    samples: list[float]


class SceneSummary(BaseModel):
    scene_type: str
    description: str
    favoured_privileged: bool | None
    elapsed_ms: int | None
    research_citation: str


class DebriefOut(BaseModel):
    session_id: int
    headline: str
    narrative: list[str]
    scenes: list[SceneSummary]
    descriptive: DescriptiveOut
    bayesian: BayesianOut
    reveal: list[RevealItem]
