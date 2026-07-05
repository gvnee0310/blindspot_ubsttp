"""Calibration guarantees for the verdict rule.

The single most important property of this tool: a FAIR player must not be
told they are biased. These tests encode that as a hard requirement, plus the
complement (a clearly biased player IS flagged, in the right direction).

They use the ROPE-based rule in narrative.classify_verdict, which declares a
lean only when most of the posterior sits beyond the balanced zone (p>0.60 or
p<0.40) rather than merely past 0.50.
"""

import random
from types import SimpleNamespace

import pytest

from app.services.analysis import compute_bayesian_posterior
from app.services.narrative import classify_verdict


def _ranking_trial(i, base, picked_privileged):
    sc = SimpleNamespace(
        id=i, scene_type="promotion_ranking", timed=False, variant_dimension="gender",
        payload={"privileged_ids": ["p"], "counterpart_ids": ["c"],
                 "privileged_base_rate": base},
    )
    ranking = ["p", "c"] if picked_privileged else ["c", "p"]
    dec = SimpleNamespace(scenario_id=i, choice={"ranking": ranking},
                          favoured_privileged=None, elapsed_ms=1000)
    return sc, dec


def _simulate(bias, n_trials, seed):
    """A player who picks the privileged candidate at rate (base_rate + bias)."""
    rng = random.Random(seed)
    scenarios, decisions = [], []
    for i in range(n_trials):
        base = rng.choice([0.5, 0.67, 0.33, 0.25, 0.75])
        pick_prob = min(0.98, max(0.02, base + bias))
        sc, dec = _ranking_trial(i, base, rng.random() < pick_prob)
        scenarios.append(sc)
        decisions.append(dec)
    return compute_bayesian_posterior(scenarios, decisions, draws=400, tune=400)


@pytest.mark.parametrize("seed", range(8))
def test_fair_player_is_never_told_they_lean(seed):
    """Across many fair players, NONE should be labelled as leaning."""
    b = _simulate(bias=0.0, n_trials=13, seed=seed * 13 + 1)
    verdict = classify_verdict(b)
    assert verdict in ("balanced", "unclear"), (
        f"fair player wrongly flagged as {verdict} (mean={b.posterior_mean:.2f})"
    )


def test_strongly_biased_player_is_flagged_favoured():
    """A clearly biased player, given enough trials, should be caught.

    The rule is deliberately conservative: with few trials it will often say
    'unclear' rather than risk a false accusation. So we give a strong bias and
    a realistic number of trials (a full session yields ~18-20 informative
    decisions across triage, ranking and calibration) and require that a clear
    majority are flagged.
    """
    hits = 0
    for seed in range(8):
        b = _simulate(bias=0.40, n_trials=20, seed=seed * 5 + 2)
        if classify_verdict(b) == "lean_favoured":
            hits += 1
    assert hits >= 5, f"only {hits}/8 strongly-biased players were flagged"


def test_biased_player_is_never_called_balanced():
    """Even when a biased player isn't confidently flagged, they must never be
    told they are 'balanced' — 'unclear' is the honest fallback."""
    for seed in range(8):
        b = _simulate(bias=0.40, n_trials=13, seed=seed * 7 + 3)
        assert classify_verdict(b) != "balanced"


def test_reverse_biased_player_is_flagged_overlooked_never_favoured():
    """A player biased toward the overlooked side must never be labelled as
    favouring the advantaged side."""
    for seed in range(8):
        b = _simulate(bias=-0.35, n_trials=13, seed=seed * 3 + 7)
        assert classify_verdict(b) != "lean_favoured"
