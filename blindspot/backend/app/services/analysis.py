"""Analysis service: descriptive statistics (NumPy/SciPy) + Bayesian inference (PyMC).

Statistical model (corrected)
-----------------------------
The estimand is a single bias parameter on the log-odds scale:

    theta ~ Normal(0, 1)                    # NEUTRAL prior, centred on p = 0.5
    p     = sigmoid(theta)                  # matched-pair choice probability

``p`` is the probability that, offered a qualification-matched pair, the
manager advances the candidate carrying the historically advantaged signal.

Observations enter through likelihoods that respect each scene's structure:

- **Inbox Triage** — the COUNT of advantaged picks among the manager's
  selections is modelled as Binomial(n_selected, p). This keeps balanced
  shortlists informative: picking 2-of-4 advantaged pulls the posterior
  TOWARD 0.5 instead of being discarded. (Approximation note: picks are
  sampled without replacement from a 6/6 pool, so trials are not perfectly
  independent; with 4 picks from 12 the Binomial approximation is mild and
  conservative.)

- **Performance Calibration** — "rated the advantaged candidate higher" is a
  Bernoulli(p) trial. Exact ties carry no directional information under this
  likelihood and are reported separately rather than silently dropped.

- **Promotion Ranking** — with k advantaged among 3 matched candidates, a
  bias-free manager tops an advantaged candidate with probability b = k/3,
  NOT 0.5. The likelihood is Bernoulli(q) with

      q = b·omega / (b·omega + (1 - b)),   omega = exp(theta)

  i.e. a Bradley–Terry-style choice with the bias acting as an odds
  multiplier. When b = 0.5 this reduces exactly to sigmoid(theta).

Why a NEUTRAL prior: this posterior is an assessment of an individual. A
prior tilted by population research would tell a manager with zero data that
they are probably biased — statistically defensible for a population, ethically
indefensible for a person. Research findings inform the narrative context, not
the individual prior.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import pymc as pm
from scipy import stats

from app.models import Decision, Scenario

_PYMC_DRAWS = 800
_PYMC_TUNE = 500
_PYMC_CHAINS = 2


# =============================================================================
# Observation extraction — raw decisions → model-ready observations
# =============================================================================


@dataclass
class Observations:
    """Structured observations for the model, grouped by likelihood type."""

    binom_k: list[int] = field(default_factory=list)   # triage: majority-signal picks
    binom_n: list[int] = field(default_factory=list)   # triage: total matched picks
    binom_timed: list[bool] = field(default_factory=list)
    binom_dim: list[str] = field(default_factory=list)
    bern_y: list[int] = field(default_factory=list)    # calibration / ranking outcomes
    bern_base: list[float] = field(default_factory=list)  # null base rate per Bernoulli
    bern_dim: list[str] = field(default_factory=list)
    bern_scene: list[str] = field(default_factory=list)
    n_ties: int = 0
    # Conflict trials: the merit edge sat on the minority-signal candidate
    # (base rate < 0.5), so picking the majority name means overriding merit.
    n_conflict: int = 0
    n_conflict_overrode_merit: int = 0

    @property
    def n_trials(self) -> int:
        return sum(self.binom_n) + len(self.bern_y)

    @property
    def n_favoured(self) -> int:
        return sum(self.binom_k) + sum(self.bern_y)


def extract_observations(
    scenarios: Sequence[Scenario], decisions: Sequence[Decision]
) -> Observations:
    obs = Observations()
    by_id = {d.scenario_id: d for d in decisions}
    for sc in scenarios:
        d = by_id.get(sc.id)
        if d is None:
            continue
        if sc.scene_type == "inbox_triage":
            selected: list[str] = d.choice.get("selected_ids", [])
            priv = set(sc.payload.get("privileged_ids", []))
            cnt = set(sc.payload.get("counterpart_ids", []))
            k = sum(1 for s in selected if s in priv)
            n = sum(1 for s in selected if s in priv or s in cnt)
            if n > 0:
                obs.binom_k.append(k)
                obs.binom_n.append(n)
                obs.binom_timed.append(bool(getattr(sc, "timed", False)))
                obs.binom_dim.append(sc.variant_dimension)
        elif sc.scene_type == "performance_calibration":
            ratings: dict[str, int] = d.choice.get("ratings", {})
            pr = ratings.get(sc.payload.get("privileged_id"))
            cr = ratings.get(sc.payload.get("counterpart_id"))
            if pr is None or cr is None:
                continue
            if pr == cr:
                obs.n_ties += 1
            else:
                y = 1 if pr > cr else 0
                base = float(sc.payload.get("privileged_base_rate", 0.5))
                obs.bern_y.append(y)
                obs.bern_base.append(base)
                obs.bern_dim.append(sc.variant_dimension)
                obs.bern_scene.append("performance_calibration")
                if base < 0.5:
                    obs.n_conflict += 1
                    obs.n_conflict_overrode_merit += y
        elif sc.scene_type == "promotion_ranking":
            ranking: list[str] = d.choice.get("ranking", [])
            if not ranking:
                continue
            priv_ids = sc.payload.get("privileged_ids", [])
            cnt_ids = sc.payload.get("counterpart_ids", [])
            base = sc.payload.get(
                "privileged_base_rate", len(priv_ids) / max(1, len(priv_ids) + len(cnt_ids))
            )
            top = ranking[0]
            y = 1 if top in priv_ids else (0 if top in cnt_ids else None)
            if y is not None:
                obs.bern_y.append(y)
                obs.bern_base.append(float(base))
                obs.bern_dim.append(sc.variant_dimension)
                obs.bern_scene.append("promotion_ranking")
                if float(base) < 0.5:
                    obs.n_conflict += 1
                    obs.n_conflict_overrode_merit += y
    return obs


# =============================================================================
# Descriptive analytics (Week 4)
# =============================================================================


@dataclass
class ProportionSummary:
    favoured: int
    total: int
    proportion: float | None
    ci_low: float | None
    ci_high: float | None

    @classmethod
    def from_counts(cls, favoured: int, total: int) -> "ProportionSummary":
        if total == 0:
            return cls(0, 0, None, None, None)
        low, high = _wilson_score_interval(favoured, total, confidence=0.95)
        return cls(favoured, total, favoured / total, low, high)


@dataclass
class SceneTypeBreakdown:
    scene_type: str
    n_decisions: int        # trials, not scenes
    n_favoured: int
    n_against: int
    n_ambiguous: int        # calibration ties
    proportion: ProportionSummary
    expected_rate: float | None = None  # null base rate, where it isn't 0.5


@dataclass
class PairedComparison:
    n_pairs: int
    mean_difference: float
    sd_difference: float | None
    t_statistic: float | None
    p_value: float | None
    ci_low: float | None
    ci_high: float | None


@dataclass
class TimedSplit:
    """Untimed vs timed comparison — cognitive load is known to amplify
    reliance on stereotype-based judgement, so a gap here is itself a finding.

    We report not just the two rates but the *difference* between them with a
    confidence interval, plus a plain-language reliability level that scales
    with sample size. This lets the UI always show the finding while being
    honest about how much to trust it, instead of hiding small samples.
    """

    untimed: ProportionSummary
    timed: ProportionSummary
    difference: float | None          # timed rate minus untimed rate
    diff_ci_low: float | None         # 95% CI on that difference
    diff_ci_high: float | None
    reliability: str                  # 'firm' | 'tentative' | 'too_thin'

    @classmethod
    def from_summaries(
        cls, untimed: ProportionSummary, timed: ProportionSummary
    ) -> "TimedSplit":
        diff = None
        lo = hi = None
        if untimed.proportion is not None and timed.proportion is not None:
            diff = timed.proportion - untimed.proportion
            # Standard error of a difference of two independent proportions.
            p1, n1 = untimed.proportion, untimed.total
            p2, n2 = timed.proportion, timed.total
            se = math.sqrt(
                (p1 * (1 - p1) / n1 if n1 else 0.0)
                + (p2 * (1 - p2) / n2 if n2 else 0.0)
            )
            margin = 1.96 * se
            lo, hi = diff - margin, diff + margin
        # Reliability tiers based on the smaller of the two samples.
        smaller = min(untimed.total, timed.total)
        if smaller >= 4:
            reliability = "firm"
        elif smaller >= 2:
            reliability = "tentative"
        else:
            reliability = "too_thin"
        return cls(untimed, timed, diff, lo, hi, reliability)


@dataclass
class DimensionBreakdown:
    """Plain-language per-dimension tallies for the debrief."""

    dimension: str          # 'gender' | 'race' | 'nationality'
    group_a: str            # plain label for the majority-signal group
    group_b: str            # plain label for the minority-signal group
    n_favoured_a: int
    n_trials: int


_DIM_LABELS = {
    "gender": ("men", "women"),
    "race": ("Chinese names", "Malay/Indian names"),
    "nationality": ("Western names", "local names"),
}


@dataclass
class DescriptiveSummary:
    overall: ProportionSummary          # pooled over base-rate-0.5 trials only
    by_scene: list[SceneTypeBreakdown]
    paired_ratings: PairedComparison | None = field(default=None)
    n_ties: int = 0
    timed_split: TimedSplit | None = field(default=None)
    by_dimension: list[DimensionBreakdown] = field(default_factory=list)
    n_conflict: int = 0
    n_conflict_overrode_merit: int = 0


def _wilson_score_interval(successes: int, n: int, *, confidence: float = 0.95) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    p_hat = successes / n
    denom = 1 + z**2 / n
    centre = (p_hat + z**2 / (2 * n)) / denom
    half = (z * np.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def compute_descriptive_summary(
    scenarios: Sequence[Scenario], decisions: Sequence[Decision]
) -> DescriptiveSummary:
    obs = extract_observations(scenarios, decisions)

    # Overall pooled proportion uses only trials whose null is 0.5 (triage
    # counts + calibration comparisons). Ranking has an asymmetric base rate,
    # so pooling it into a raw proportion would mislead; it gets its own row
    # with the expected rate displayed alongside.
    pair_fav = sum(obs.binom_k) + sum(
        y for y, b in zip(obs.bern_y, obs.bern_base, strict=True) if b == 0.5
    )
    pair_total = sum(obs.binom_n) + sum(1 for b in obs.bern_base if b == 0.5)
    overall = ProportionSummary.from_counts(pair_fav, pair_total)

    breakdowns: list[SceneTypeBreakdown] = []

    # Triage
    tri_fav, tri_n = sum(obs.binom_k), sum(obs.binom_n)
    if tri_n > 0:
        breakdowns.append(SceneTypeBreakdown(
            scene_type="inbox_triage",
            n_decisions=tri_n, n_favoured=tri_fav, n_against=tri_n - tri_fav,
            n_ambiguous=0,
            proportion=ProportionSummary.from_counts(tri_fav, tri_n),
            expected_rate=0.5,
        ))

    for scene_name, ambiguous in (("performance_calibration", obs.n_ties),
                                  ("promotion_ranking", 0)):
        ys = [y for y, s in zip(obs.bern_y, obs.bern_scene, strict=True) if s == scene_name]
        bs = [b for b, s in zip(obs.bern_base, obs.bern_scene, strict=True) if s == scene_name]
        if ys or ambiguous:
            fav = sum(ys)
            breakdowns.append(SceneTypeBreakdown(
                scene_type=scene_name,
                n_decisions=len(ys) + ambiguous, n_favoured=fav,
                n_against=len(ys) - fav, n_ambiguous=ambiguous,
                proportion=ProportionSummary.from_counts(fav, len(ys)),
                expected_rate=float(np.mean(bs)) if bs else None,
            ))

    paired = _compute_paired_ratings(scenarios, decisions)

    # Timed vs untimed comparison. We build it whenever any timed matched
    # decisions exist, and let the reliability tier (not a hard cutoff) signal
    # how much to trust it.
    timed_split = None
    ut_k = sum(k for k, t in zip(obs.binom_k, obs.binom_timed, strict=True) if not t)
    ut_n = sum(n for n, t in zip(obs.binom_n, obs.binom_timed, strict=True) if not t)
    ti_k = sum(k for k, t in zip(obs.binom_k, obs.binom_timed, strict=True) if t)
    ti_n = sum(n for n, t in zip(obs.binom_n, obs.binom_timed, strict=True) if t)
    if ti_n > 0:
        timed_split = TimedSplit.from_summaries(
            untimed=ProportionSummary.from_counts(ut_k, ut_n),
            timed=ProportionSummary.from_counts(ti_k, ti_n),
        )

    # Per-dimension plain-language tallies (all trials, any base rate).
    dim_fav: dict[str, int] = {}
    dim_n: dict[str, int] = {}
    for k, n, d in zip(obs.binom_k, obs.binom_n, obs.binom_dim, strict=True):
        dim_fav[d] = dim_fav.get(d, 0) + k
        dim_n[d] = dim_n.get(d, 0) + n
    for y, d in zip(obs.bern_y, obs.bern_dim, strict=True):
        dim_fav[d] = dim_fav.get(d, 0) + y
        dim_n[d] = dim_n.get(d, 0) + 1
    by_dimension = [
        DimensionBreakdown(
            dimension=d,
            group_a=_DIM_LABELS.get(d, (d, "other"))[0],
            group_b=_DIM_LABELS.get(d, (d, "other"))[1],
            n_favoured_a=dim_fav[d],
            n_trials=dim_n[d],
        )
        for d in sorted(dim_n)
    ]

    return DescriptiveSummary(overall=overall, by_scene=breakdowns,
                              paired_ratings=paired, n_ties=obs.n_ties,
                              timed_split=timed_split, by_dimension=by_dimension,
                              n_conflict=obs.n_conflict,
                              n_conflict_overrode_merit=obs.n_conflict_overrode_merit)


def _compute_paired_ratings(
    scenarios: Sequence[Scenario], decisions: Sequence[Decision]
) -> PairedComparison | None:
    pairs: list[tuple[int, int]] = []
    by_id = {sc.id: sc for sc in scenarios}
    for d in decisions:
        sc = by_id.get(d.scenario_id)
        if sc is None or sc.scene_type != "performance_calibration":
            continue
        ratings = d.choice.get("ratings", {})
        pr = ratings.get(sc.payload.get("privileged_id"))
        cr = ratings.get(sc.payload.get("counterpart_id"))
        if pr is not None and cr is not None:
            pairs.append((int(pr), int(cr)))
    if not pairs:
        return None

    arr = np.array(pairs, dtype=float)
    diffs = arr[:, 0] - arr[:, 1]
    mean_diff = float(diffs.mean())
    sd_diff = float(diffs.std(ddof=1)) if len(diffs) > 1 else None

    t_stat = p_val = ci_low = ci_high = None
    if sd_diff is not None and sd_diff > 0:
        res = stats.ttest_rel(arr[:, 0], arr[:, 1])
        t_stat, p_val = float(res.statistic), float(res.pvalue)
        se = sd_diff / np.sqrt(len(diffs))
        crit = stats.t.ppf(0.975, df=len(diffs) - 1)
        ci_low, ci_high = float(mean_diff - crit * se), float(mean_diff + crit * se)

    return PairedComparison(n_pairs=len(pairs), mean_difference=mean_diff,
                            sd_difference=sd_diff, t_statistic=t_stat,
                            p_value=p_val, ci_low=ci_low, ci_high=ci_high)


# =============================================================================
# Bayesian inference (Week 5)
# =============================================================================


# Region of Practical Equivalence: p within ±0.10 of 0.5 is treated as
# "practically balanced". The posterior mass inside this region is the model's
# formal route to concluding FAIRNESS — without it, a tool like this can only
# ever accumulate evidence of bias, never of balance.
ROPE_LOW = 0.40
ROPE_HIGH = 0.60


@dataclass
class BayesianPosterior:
    posterior_mean: float
    hdi_low: float
    hdi_high: float
    prob_p_above_half: float
    prob_p_above_60: float
    prob_p_below_40: float       # P(p < 0.40): meaningful lean toward the overlooked side
    prob_in_rope: float          # P(0.40 < p < 0.60): evidence of practical balance
    prior_prob_in_rope: float    # same mass under the prior — the comparison point
    rope_low: float
    rope_high: float
    n_observations: int
    n_favoured: int
    samples: list[float]


def compute_bayesian_posterior(
    scenarios: Sequence[Scenario],
    decisions: Sequence[Decision],
    *,
    draws: int = _PYMC_DRAWS,
    tune: int = _PYMC_TUNE,
    chains: int = _PYMC_CHAINS,
    sample_count_for_plot: int = 500,
) -> BayesianPosterior:
    obs = extract_observations(scenarios, decisions)

    binom_k = np.array(obs.binom_k, dtype=int)
    binom_n = np.array(obs.binom_n, dtype=int)
    bern_y = np.array(obs.bern_y, dtype=int)
    bern_b = np.array(obs.bern_base, dtype=float)

    with pm.Model():
        # Neutral prior: prior mean of p is exactly 0.5; sd=1 on the logit
        # scale keeps ~95% prior mass on p in roughly [0.12, 0.88].
        theta = pm.Normal("theta", mu=0.0, sigma=1.0)
        p = pm.Deterministic("p", pm.math.sigmoid(theta))

        if binom_k.size:
            pm.Binomial("y_triage", n=binom_n, p=p, observed=binom_k)

        if bern_y.size:
            # Base-rate correction as a logit offset: q = b·e^θ/(b·e^θ + 1−b)
            # is algebraically identical to sigmoid(θ + logit(b)), which is
            # numerically stabler and compiles cleanly.
            logit_b = np.log(bern_b / (1.0 - bern_b))
            q = pm.math.sigmoid(theta + logit_b)
            pm.Bernoulli("y_choice", p=q, observed=bern_y)

        idata = pm.sample(
            draws=draws, tune=tune, chains=chains, cores=1,
            target_accept=0.9, progressbar=False, random_seed=42,
            return_inferencedata=True,
        )

    p_samples = idata.posterior["p"].values.flatten()
    hdi_low, hdi_high = _hdi(p_samples, credible_mass=0.95)

    # Prior ROPE mass under theta ~ Normal(0, 1): p in (L, H) <=> theta in
    # (logit L, logit H). This is the baseline the posterior mass is compared
    # against — "did the data move belief toward balance?"
    prior_rope = float(
        stats.norm.cdf(np.log(ROPE_HIGH / (1 - ROPE_HIGH)))
        - stats.norm.cdf(np.log(ROPE_LOW / (1 - ROPE_LOW)))
    )

    rng = np.random.default_rng(0)
    plot = (rng.choice(p_samples, size=sample_count_for_plot, replace=False)
            if p_samples.size > sample_count_for_plot else p_samples)

    return BayesianPosterior(
        posterior_mean=float(p_samples.mean()),
        hdi_low=float(hdi_low), hdi_high=float(hdi_high),
        prob_p_above_half=float((p_samples > 0.5).mean()),
        prob_p_above_60=float((p_samples > 0.6).mean()),
        prob_p_below_40=float((p_samples < 0.4).mean()),
        prob_in_rope=float(((p_samples > ROPE_LOW) & (p_samples < ROPE_HIGH)).mean()),
        prior_prob_in_rope=prior_rope,
        rope_low=ROPE_LOW,
        rope_high=ROPE_HIGH,
        n_observations=obs.n_trials,
        n_favoured=obs.n_favoured,
        samples=[float(x) for x in plot],
    )


def _hdi(samples: np.ndarray, *, credible_mass: float = 0.95) -> tuple[float, float]:
    sorted_s = np.sort(samples)
    n = sorted_s.size
    if n == 0:
        return (float("nan"), float("nan"))
    width = int(np.floor(credible_mass * n))
    if width >= n:
        return (float(sorted_s[0]), float(sorted_s[-1]))
    widths = sorted_s[width:] - sorted_s[: n - width]
    i = int(np.argmin(widths))
    return (float(sorted_s[i]), float(sorted_s[i + width]))
