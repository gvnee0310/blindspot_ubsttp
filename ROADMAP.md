# Roadmap

Maps the proposal's 10-week plan to concrete deliverables in this repository.

| Weeks | Milestone                                            | Status   |
|-------|------------------------------------------------------|----------|
| 1     | Project skeleton + reading                           | Done     |
| 2     | Scenario design (3 scenes) + data schema             | Done     |
| 3     | Simulation UI + decision capture                     | Done     |
| 4     | Persistence + descriptive analytics (NumPy/SciPy)    | Done     |
| 5     | Bayesian analysis module (PyMC)                      | Done     |
| 6     | Debrief dashboard (descriptive + Bayesian)           | Done     |
| 7–8   | Aggregate benchmark, hierarchical model, polish      | Pending  |
| 9     | Scalability (Redis cache, cloud deploy)              | Pending  |
| 10    | Final demo + writeup                                 | Pending  |

---

## Week 1 — Project skeleton ✓

- Frontend (React + Vite + TS + Tailwind) and backend (FastAPI) project structure
- Login → Home → Simulation → Debrief → History page skeleton
- Main simulation flow defined as a React state machine
- Database entities: `User`, `SimulationSession`, `Scenario`, `Decision`, `AggregateStat`
- Bayesian target metric chosen: `p`, the manager's probability of favouring the
  privileged variant on a comparable-qualifications decision

## Week 2 — Scenario design + data schema ✓

- **Three scenes**, each implemented end-to-end:
  - **Inbox Triage** — select 4 of 12 candidates
  - **Performance Calibration** — rate 2 team members on a 1–5 scale
  - **Promotion Ranking** — rank 3 candidates and type a justification
- Matched candidate profiles with deliberate demographic variation
  (`profile_generator.py`); qualifications are template-paired across each
  candidate pair so the only variation is the demographic signal
- Data schema:
  - Backend Pydantic models (`schemas.py`) and SQLAlchemy models (`models.py`)
  - TypeScript interfaces mirroring them (`frontend/src/types/index.ts`)

## Week 3 — Simulation UI + decision capture ✓

- Start simulation flow with context selection (hiring / promotion / review)
- Per-scene React components capturing all three decision shapes:
  - Multi-select shortlist (Inbox Triage)
  - Numeric ratings with explicit Likert anchors (Performance Calibration)
  - Drag-style ranking + free-text justification (Promotion Ranking)
- Decisions POSTed to `/decisions/` and persisted

## Week 4 — Persistence + descriptive analytics ✓

`backend/app/services/analysis.py` — `compute_descriptive_summary` and friends.

- Saves completed sessions; session history endpoint (`GET /sessions/`) and page
- NumPy/SciPy backed:
  - Counts of favoured / not-favoured / ambiguous decisions
  - Selection proportions per scene type
  - **Wilson score 95% confidence intervals** (better than normal-approx for small samples)
  - **Paired t-test** for Performance Calibration ratings (privileged vs counterpart) with CI
- Output exposed via the debrief endpoint and rendered as a dedicated section
  on the dashboard with a per-scene bar chart

## Week 5 — Bayesian analysis module ✓

`compute_bayesian_posterior` in `analysis.py`.

- Real PyMC model (not a closed-form shortcut):
  ```
  theta ~ Normal(mu_prior, sigma_prior)   # mu_prior calibrated from research
  p     = sigmoid(theta)
  y_i   ~ Bernoulli(p)                    # observed favoured/not-favoured
  ```
- Posterior summarised by:
  - **Posterior mean** of `p`
  - **95% highest-density interval** (HDI)
  - **Probability of direction**: P(p > 0.5) and P(p > 0.6)
  - Sample-based density for plotting
- Parameterisation chosen on the **log-odds scale** so the model is the natural
  starting point for the hierarchical / covariate extensions planned for
  Weeks 7–8

## Week 6 — Debrief dashboard ✓

`frontend/src/pages/DebriefPage.tsx` — three blocks:

1. **Narrative** — multi-paragraph reflective story-style framing of the results
2. **Descriptive** — overall rate + Wilson CI, per-scene bar chart with the 50%
   baseline marked, paired-comparison table for the calibration scene
3. **Bayesian** — four headline stats (posterior mean, HDI, P(p>0.5),
   P(p>0.6)) and the posterior density plot with the HDI shaded and the
   no-preference baseline at 0.5

The two analytical blocks are explicitly labelled (NumPy/SciPy vs PyMC) so
reviewers can see the statistical pipeline behind the page.

---

## What's still ahead

### Weeks 7–8 — Aggregate benchmark + hierarchical model

- Populate the `AggregateStat` table on completed sessions (k-anonymity threshold
  before any row contributes to a public benchmark)
- Render the manager's posterior mean against the platform-wide percentile
- Promote the single-level PyMC model to a hierarchical structure: per-scene-type
  random effects, optional cohort/org-level grouping
- Cache aggregate statistics in Redis (the `redis` Python client is already in
  `requirements.txt`; the service stub is the only missing piece)

### Week 9 — Scalability

- Move PyMC sampling onto an async task queue so the debrief endpoint is not
  blocked by MCMC. The current setup samples synchronously in ~1–3 seconds once
  the pytensor backend is JIT-compiled — fine for a demo, not for many users
- Move the JWT secret and CORS origins to a real secret manager
- Cloud deploy the Docker Compose stack (Fly.io, Render, or Cloud Run)

### Week 10 — Final demo + writeup

- Demo script
- A short writeup walking a non-technical reader from "what the platform does"
  through "what the Bayesian numbers mean" and ending at "what we'd build next"

---

## Architectural notes worth flagging at the mentor session

1. **Why PyMC and not the closed-form Beta–Bernoulli posterior.** Mathematically
   the two give the same answer for this single-parameter case. We use PyMC
   anyway because (a) the roadmap is about *learning* PyMC, (b) the log-odds
   parameterisation extends cleanly to covariates (`scene_type`, `timed`,
   `cohort_size`) which the hierarchical Week 7–8 model needs, and (c) MCMC
   samples give a richer description for the plot than the analytic density.

2. **Wilson CI vs normal-approx.** The roadmap mentions "confidence intervals if
   relevant". Sample sizes per session are tiny (often n = 3 informative
   decisions), and the normal-approximation interval is unreliable below
   n ≈ 30. Wilson is the standard small-sample alternative.

3. **Paired t-test on calibration ratings.** The Performance Calibration scene
   is the only one that produces an ordered numeric pair (privileged rating,
   counterpart rating). The natural test for "did the manager rate the
   privileged candidate higher" is a paired t on the differences, with a CI.

4. **Synthetic data only.** Every candidate profile is generated programmatically
   by `ProfileGenerator`. No ingestion path exists for real HR data. This is an
   architectural property, not a policy note.

---

## Statistical revision (pre-demo review)

A pre-presentation review found and fixed four statistical defects:

1. **Confounded triage cohorts.** Templates were drawn independently per
   candidate, so one demographic group could randomly receive stronger
   resumes. Fixed: `generate_matched_cohort` enforces that every template
   appears exactly once per role — groups are identical by construction.

2. **Tie/balanced-outcome exclusion.** Balanced shortlists and identical
   ratings were coded `None` and dropped, biasing the posterior away from 0.5.
   Fixed: triage is now modelled as Binomial *counts* (2-of-4 is evidence of
   fairness); calibration ties are reported explicitly.

3. **Wrong null for Promotion Ranking.** With 2 advantaged among 3 candidates
   the bias-free top-pick rate is 2/3, not 1/2. Fixed: Bradley–Terry-style
   likelihood q = b·ω/(b·ω + 1−b) with the base rate b carried per scene.

4. **Research-tilted prior for individual inference.** The prior mean sat
   near 0.55–0.6, telling a manager with zero data they were probably biased.
   Fixed: neutral Normal(0,1) prior on the logit (prior mean of p = 0.5);
   research citations remain in the narrative as context only.

Design revisions in the same pass: paraphrase variants so matched pairs are
not verbatim copies; distinct surnames; 7-scene sessions (~12 trials, 10–12
minutes) with one 60-second timed round; post-session **reveal** showing every
matched pair and what the manager did with it.

---

## Fairness & Singapore-context revision (final pre-demo pass)

**Can the tool conclude fairness, not just bias?** Yes — this pass added a
ROPE (Region of Practical Equivalence) analysis: P(0.40 < p < 0.60) is the
posterior probability the manager is *practically balanced*, reported against
its prior value (~31%) so the narrative can say "the evidence moved toward
balance". The narrative now has three verdicts — lean (either direction, ≥90%
probability of direction), practical balance (ROPE mass ≥50% and grown), or
the honest default: "not enough evidence". A regression test guarantees that
perfectly balanced play GROWS the ROPE mass. The debrief chart shades the
balance region in green, and the Reveal section no longer front-loads
"gotcha" rows — balanced outcomes are shown in natural order.

**Singapore multi-ethnic candidate pool.** Names now span Chinese, Malay,
Indian, and Western-expatriate pools (six per gender per group), and the
simulation tests three dimensions: gender, race (Chinese-majority vs
Malay/Indian names, per resume-audit findings in Singapore's labour market),
and nationality (Western expatriate vs local — the documented "expatriate
premium"). Validity rule enforced in code and tests: within any matched pair,
EXACTLY ONE signal varies — race pairs hold gender constant, gender pairs hold
ethnicity constant, nationality pairs hold gender constant. Direction
conventions are documented in `profile_generator.py` and are pooling labels,
not moral claims; the analysis is symmetric in both directions.

**Numerical fix.** The base-rate-corrected choice likelihood was reformulated
as a logit offset — q = sigmoid(θ + logit(b)) — which is algebraically
identical to the Bradley–Terry form but numerically stabler under PyMC.
