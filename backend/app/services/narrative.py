"""Narrative generator — short, plain-language debrief text.

Rules learned from user testing: no jargon ("advantaged signal" is out),
no wall of text, three honest verdicts (lean / balanced / can't tell yet),
and every number gets one plain sentence before any statistics appear.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.data.bias_research import lookup_research
from app.models import Decision, Scenario
from app.services.analysis import BayesianPosterior, DescriptiveSummary


def _scene_human_label(scene_type: str) -> str:
    return {
        "inbox_triage": "Shortlisting",
        "performance_calibration": "Rating",
        "promotion_ranking": "Ranking",
    }.get(scene_type, scene_type)


def _dimension_label(dim: str) -> str:
    return {
        "gender": "gender",
        "race": "race",
        "nationality": "nationality",
    }.get(dim, dim)


# Verdict decision rule (ROPE-based, deliberately conservative)
# ------------------------------------------------------------------
# A "lean" is declared only when most of the posterior sits OUTSIDE the
# balanced zone — i.e. p is not just above 0.5 but meaningfully past 0.60
# (or below 0.40). Using the ROPE boundary instead of 0.5 makes the verdict
# robust to small-sample noise: a fair player who happens to drift just past
# 0.5 no longer trips a false "biased" verdict, because they won't clear 0.60.
LEAN_EVIDENCE = 0.85   # need 85% of posterior mass beyond the balanced zone
BALANCED_EVIDENCE = 0.50


def classify_verdict(bayes: BayesianPosterior) -> str:
    """Return one of: 'lean_favoured', 'lean_overlooked', 'balanced', 'unclear'."""
    if bayes.n_observations < 3:
        return "unclear"
    if bayes.prob_p_above_60 >= LEAN_EVIDENCE:
        return "lean_favoured"
    if bayes.prob_p_below_40 >= LEAN_EVIDENCE:
        return "lean_overlooked"
    if bayes.prob_in_rope >= BALANCED_EVIDENCE and bayes.prob_in_rope > bayes.prior_prob_in_rope:
        return "balanced"
    return "unclear"


def build_headline(bayes: BayesianPosterior) -> str:
    verdict = classify_verdict(bayes)
    if bayes.n_observations == 0:
        return "We didn't get enough decisions to say anything this time."
    return {
        "lean_favoured": "Your picks leaned toward the names that usually get the benefit of the doubt.",
        "lean_overlooked": "Your picks leaned the other way — toward the names that usually get overlooked.",
        "balanced": "You mostly went by the work, not the name. This run looks balanced.",
        "unclear": "Too close to call this run — the choices don't clearly point either way.",
    }[verdict]


def build_narrative(
    scenarios: Sequence[Scenario],
    decisions: Sequence[Decision],
    descriptive: DescriptiveSummary,
    bayes: BayesianPosterior,
) -> list[str]:
    """Short, plain findings. Keywords and numbers are wrapped in **double
    asterisks** so the UI can bold them; the text reads fine without markup too.
    """
    points: list[str] = []

    # 1. The core count: equal-on-paper picks.
    if descriptive.overall.total > 0 and descriptive.overall.proportion is not None:
        fav = descriptive.overall.favoured
        tot = descriptive.overall.total
        if tot == 1:
            points.append(
                "You had **1 choice** between two people who were equally qualified. You "
                f"picked the favoured name **{'that time' if fav == 1 else 'the other one'}**."
            )
        else:
            points.append(
                f"You faced **{tot} choices** between two people who were equally qualified. "
                f"You picked the favoured name **{fav} of those {tot} times**."
            )

    # 2. Conflict trials — the clearest evidence.
    if descriptive.n_conflict > 0:
        if descriptive.n_conflict_overrode_merit > 0:
            points.append(
                f"**{descriptive.n_conflict_overrode_merit} time"
                f"{'s' if descriptive.n_conflict_overrode_merit != 1 else ''}**, you chose the "
                "favoured name even though the other person was **clearly more qualified**. "
                "These are the choices most worth a second look."
            )
        else:
            points.append(
                f"When the favoured name was the **weaker** candidate, you chose the stronger "
                "person **every time**. That's exactly what you'd want."
            )

    # 3. Ties.
    if descriptive.n_ties:
        points.append(
            f"You rated **{descriptive.n_ties} identical pair"
            f"{'s' if descriptive.n_ties != 1 else ''}** exactly the same — the fair call when "
            "two records match."
        )

    # 4. Verdict, stated plainly with the key number bolded.
    rope_pct = f"{bayes.prob_in_rope:.0%}"
    prior_pct = f"{bayes.prior_prob_in_rope:.0%}"
    if bayes.prob_in_rope - bayes.prior_prob_in_rope > 0.03:
        points.append(
            f"Putting it together, the model now sees a **{rope_pct} chance** your choices are "
            f"genuinely even-handed — up from **{prior_pct}** before you started. Your picks "
            "moved the needle toward balance."
        )
    else:
        points.append(
            f"Putting it together, the model sees a **{rope_pct} chance** your choices are "
            f"genuinely even-handed, based on your **{bayes.n_observations} decisions**."
        )

    return points


def build_scene_summaries(
    scenarios: Sequence[Scenario], decisions: Sequence[Decision]
) -> list[dict]:
    by_id = {d.scenario_id: d for d in decisions}
    out: list[dict] = []
    for sc in scenarios:
        d = by_id.get(sc.id)
        research = lookup_research(sc.scene_type, sc.variant_dimension)
        role = sc.payload.get("role", "")
        out.append(
            {
                "scene_type": sc.scene_type,
                "description": (
                    _scene_human_label(sc.scene_type)
                    + (f" — {role}" if role else "")
                    + f" ({_dimension_label(sc.variant_dimension)}"
                    + (", timed" if sc.timed else "")
                    + ")"
                ),
                "favoured_privileged": None if d is None else d.favoured_privileged,
                "elapsed_ms": None if d is None else d.elapsed_ms,
                "research_citation": f"{research.citation} — {research.summary}",
            }
        )
    return out
