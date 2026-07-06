"""Tests for descriptive + Bayesian analysis
"""

from types import SimpleNamespace

import pytest

from app.services.analysis import (
    compute_bayesian_posterior,
    compute_descriptive_summary,
    extract_observations,
)


def _triage(sid=1):
    return SimpleNamespace(
        id=sid, scene_type="inbox_triage", variant_dimension="gender",
        payload={"privileged_ids": [f"p{i}" for i in range(6)],
                 "counterpart_ids": [f"c{i}" for i in range(6)]})


def _calib(sid=2):
    return SimpleNamespace(
        id=sid, scene_type="performance_calibration", variant_dimension="gender",
        payload={"privileged_id": f"pp{sid}", "counterpart_id": f"cc{sid}"})


def _rank(sid=3, n_priv=2):
    return SimpleNamespace(
        id=sid, scene_type="promotion_ranking", variant_dimension="gender",
        payload={"privileged_ids": [f"rp{i}" for i in range(n_priv)],
                 "counterpart_ids": [f"rc{i}" for i in range(3 - n_priv)],
                 "privileged_base_rate": n_priv / 3})


def _dec(sid, choice):
    return SimpleNamespace(scenario_id=sid, choice=choice)


# ---------------------------------------------------------------- extraction


def test_balanced_shortlist_is_informative_not_discarded():
    obs = extract_observations(
        [_triage()], [_dec(1, {"selected_ids": ["p0", "p1", "c0", "c1"]})])
    assert obs.binom_k == [2]
    assert obs.binom_n == [4]  # 2-of-4 enters the likelihood as evidence toward 0.5


def test_ranking_base_rate_recorded():
    obs = extract_observations(
        [_rank(3, n_priv=2)], [_dec(3, {"ranking": ["rp0", "rc0", "rp1"]})])
    assert obs.bern_y == [1]
    assert obs.bern_base == [pytest.approx(2 / 3)]


def test_calibration_tie_counted_separately():
    obs = extract_observations(
        [_calib(2)], [_dec(2, {"ratings": {"pp2": 4, "cc2": 4}})])
    assert obs.n_ties == 1
    assert obs.bern_y == []


# ---------------------------------------------------------------- descriptive


def test_descriptive_pools_only_symmetric_trials():
    scenarios = [_triage(1), _rank(3, n_priv=2)]
    decisions = [
        _dec(1, {"selected_ids": ["p0", "p1", "p2", "c0"]}),  # 3-of-4
        _dec(3, {"ranking": ["rp0", "rc0", "rp1"]}),
    ]
    desc = compute_descriptive_summary(scenarios, decisions)
    # Overall = triage only (ranking base 2/3 must not pollute the 50% baseline).
    assert desc.overall.total == 4
    assert desc.overall.favoured == 3
    rank_row = next(b for b in desc.by_scene if b.scene_type == "promotion_ranking")
    assert rank_row.expected_rate == pytest.approx(2 / 3)


def test_paired_t_test_with_three_pairs():
    scenarios = [_calib(i) for i in (10, 11, 12)]
    decisions = [
        _dec(10, {"ratings": {"pp10": 5, "cc10": 3}}),
        _dec(11, {"ratings": {"pp11": 4, "cc11": 3}}),
        _dec(12, {"ratings": {"pp12": 5, "cc12": 4}}),
    ]
    desc = compute_descriptive_summary(scenarios, decisions)
    assert desc.paired_ratings is not None
    assert desc.paired_ratings.n_pairs == 3
    assert desc.paired_ratings.mean_difference == pytest.approx((2 + 1 + 1) / 3)
    assert desc.paired_ratings.t_statistic is not None


# ---------------------------------------------------------------- Bayesian


@pytest.fixture(scope="module")
def warm_pymc():
    compute_bayesian_posterior(
        [_triage()], [_dec(1, {"selected_ids": ["p0", "c0"]})], draws=100, tune=100)


def test_neutral_prior_no_data(warm_pymc):
    b = compute_bayesian_posterior([], [], draws=400, tune=400)
    assert b.n_observations == 0
    assert 0.45 < b.posterior_mean < 0.55  # neutral, NOT research-tilted
    assert 0.4 < b.prob_p_above_half < 0.6


def test_fair_behaviour_stays_near_half(warm_pymc):
    scenarios = [_triage(1), _calib(2), _rank(3, n_priv=2)]
    decisions = [
        _dec(1, {"selected_ids": ["p0", "p1", "c0", "c1"]}),   # balanced
        _dec(2, {"ratings": {"pp2": 4, "cc2": 4}}),            # tie
        _dec(3, {"ranking": ["rp0", "rc0", "rp1"]}),           # base-rate-consistent
    ]
    b = compute_bayesian_posterior(scenarios, decisions, draws=400, tune=400)
    assert b.prob_p_above_half < 0.75  # no strong bias claim for fair play


def test_biased_behaviour_detected(warm_pymc):
    scenarios = [_triage(1), _calib(2), _calib(4), _rank(3, n_priv=1)]
    decisions = [
        _dec(1, {"selected_ids": ["p0", "p1", "p2", "p3"]}),   # 4-of-4
        _dec(2, {"ratings": {"pp2": 5, "cc2": 3}}),
        _dec(4, {"ratings": {"pp4": 5, "cc4": 3}}),
        _dec(3, {"ranking": ["rp0", "rc0", "rc1"]}),           # top priv at base 1/3
    ]
    b = compute_bayesian_posterior(scenarios, decisions, draws=400, tune=400)
    assert b.posterior_mean > 0.65
    assert b.prob_p_above_half > 0.9


def test_hdi_tightens_with_more_data(warm_pymc):
    few = compute_bayesian_posterior(
        [_triage(1)], [_dec(1, {"selected_ids": ["p0", "c0"]})], draws=400, tune=400)
    scenarios = [_triage(i) for i in range(1, 5)]
    decisions = [_dec(i, {"selected_ids": ["p0", "p1", "c0", "c1"]}) for i in range(1, 5)]
    many = compute_bayesian_posterior(scenarios, decisions, draws=400, tune=400)
    assert (many.hdi_high - many.hdi_low) < (few.hdi_high - few.hdi_low)


# ---------------------------------------------------------------- ROPE & timed


def _timed_triage(sid, timed):
    s = _triage(sid)
    s.timed = timed
    return s


def test_rope_fields_present_and_consistent(warm_pymc):
    b = compute_bayesian_posterior(
        [_triage(1)], [_dec(1, {"selected_ids": ["p0", "p1", "c0", "c1"]})],
        draws=400, tune=400)
    assert 0.0 <= b.prob_in_rope <= 1.0
    assert b.rope_low == 0.40 and b.rope_high == 0.60
    # Prior mass in the ROPE under Normal(0,1) on the logit is ~0.31.
    assert 0.25 < b.prior_prob_in_rope < 0.40


def test_balanced_behaviour_grows_rope_mass(warm_pymc):
    scenarios = [_triage(i) for i in range(1, 4)]
    decisions = [_dec(i, {"selected_ids": ["p0", "p1", "c0", "c1"]}) for i in range(1, 4)]
    b = compute_bayesian_posterior(scenarios, decisions, draws=400, tune=400)
    # Perfectly balanced data must move belief TOWARD balance, not just fail
    # to prove bias. This is the "tool can conclude fairness" guarantee.
    assert b.prob_in_rope > b.prior_prob_in_rope


def test_timed_split_computed():
    scenarios = [_timed_triage(1, False), _timed_triage(2, True)]
    decisions = [
        _dec(1, {"selected_ids": ["p0", "p1", "c0", "c1"]}),   # balanced untimed
        _dec(2, {"selected_ids": ["p0", "p1", "p2", "c0"]}),   # leans under pressure
    ]
    desc = compute_descriptive_summary(scenarios, decisions)
    assert desc.timed_split is not None
    assert desc.timed_split.untimed.proportion == 0.5
    assert desc.timed_split.timed.proportion == 0.75
    # New fields: a difference and a reliability tier are always populated.
    assert desc.timed_split.difference is not None
    assert abs(desc.timed_split.difference - 0.25) < 1e-9
    assert desc.timed_split.reliability in ("firm", "tentative", "too_thin")
    # CI endpoints are present when both proportions exist.
    assert desc.timed_split.diff_ci_low is not None
    assert desc.timed_split.diff_ci_high is not None
