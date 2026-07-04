"""Debrief endpoint — runs descriptive + Bayesian analysis and generates the narrative."""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.auth import get_current_user
from app.db import get_db
from app.models import Decision, SimulationSession, User
from app.schemas import (
    BayesianOut,
    DebriefOut,
    DescriptiveOut,
    PairedComparisonOut,
    ProportionOut,
    RevealItem,
    SceneBreakdownOut,
    DimensionBreakdownOut,
    SceneSummary,
    TimedSplitOut,
)
from app.services.analysis import (
    compute_bayesian_posterior,
    compute_descriptive_summary,
)
from app.services.narrative import build_headline, build_narrative, build_scene_summaries
from app.services.reveal import build_reveal

router = APIRouter(prefix="/debrief", tags=["debrief"])


@router.get("/{session_id}", response_model=DebriefOut)
def get_debrief(
    session_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> DebriefOut:
    sess = db.get(SimulationSession, session_id)
    if sess is None or sess.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    scenarios = sess.scenarios
    decisions: list[Decision] = [sc.decision for sc in scenarios if sc.decision is not None]

    descriptive = compute_descriptive_summary(scenarios, decisions)
    bayesian = compute_bayesian_posterior(scenarios, decisions)

    headline = build_headline(bayesian)
    narrative = build_narrative(scenarios, decisions, descriptive, bayesian)
    scene_summaries = build_scene_summaries(scenarios, decisions)

    return DebriefOut(
        session_id=session_id,
        headline=headline,
        narrative=narrative,
        scenes=[SceneSummary(**s) for s in scene_summaries],
        descriptive=DescriptiveOut(
            overall=ProportionOut(**asdict(descriptive.overall)),
            by_scene=[
                SceneBreakdownOut(
                    scene_type=b.scene_type,
                    n_decisions=b.n_decisions,
                    n_favoured=b.n_favoured,
                    n_against=b.n_against,
                    n_ambiguous=b.n_ambiguous,
                    proportion=ProportionOut(**asdict(b.proportion)),
                    expected_rate=b.expected_rate,
                )
                for b in descriptive.by_scene
            ],
            paired_ratings=(
                PairedComparisonOut(**asdict(descriptive.paired_ratings))
                if descriptive.paired_ratings is not None
                else None
            ),
            n_ties=descriptive.n_ties,
            by_dimension=[DimensionBreakdownOut(**asdict(d)) for d in descriptive.by_dimension],
            n_conflict=descriptive.n_conflict,
            n_conflict_overrode_merit=descriptive.n_conflict_overrode_merit,
            timed_split=(
                TimedSplitOut(
                    untimed=ProportionOut(**asdict(descriptive.timed_split.untimed)),
                    timed=ProportionOut(**asdict(descriptive.timed_split.timed)),
                    difference=descriptive.timed_split.difference,
                    diff_ci_low=descriptive.timed_split.diff_ci_low,
                    diff_ci_high=descriptive.timed_split.diff_ci_high,
                    reliability=descriptive.timed_split.reliability,
                )
                if descriptive.timed_split is not None
                else None
            ),
        ),
        bayesian=BayesianOut(
            posterior_mean=bayesian.posterior_mean,
            hdi_low=bayesian.hdi_low,
            hdi_high=bayesian.hdi_high,
            prob_p_above_half=bayesian.prob_p_above_half,
            prob_p_above_60=bayesian.prob_p_above_60,
            prob_p_below_40=bayesian.prob_p_below_40,
            prob_in_rope=bayesian.prob_in_rope,
            prior_prob_in_rope=bayesian.prior_prob_in_rope,
            rope_low=bayesian.rope_low,
            rope_high=bayesian.rope_high,
            n_observations=bayesian.n_observations,
            n_favoured=bayesian.n_favoured,
            samples=bayesian.samples,
        ),
        reveal=[RevealItem(**r) for r in build_reveal(scenarios, decisions)],
    )
