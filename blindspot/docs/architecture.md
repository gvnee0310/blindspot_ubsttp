# Architecture

This document describes how BlindSpot is structured and the rationale behind
the major design decisions. For the high-level pitch, see [`README.md`](../README.md).
For status against the 10-week plan, see [`ROADMAP.md`](../ROADMAP.md).

## Three-tier overview

BlindSpot follows a conventional three-tier architecture:

1. **Client tier** — A single-page React + TypeScript application served by Vite.
   It owns the scenario-flow state machine, captures decisions, and renders the
   debrief dashboard.
2. **Service tier** — A FastAPI application. It exposes JSON endpoints for
   auth, sessions, decisions, and the debrief. Two internal services live
   behind the gateway: the **scenario engine** (which generates synthetic
   candidate profiles with controlled variation) and the **analysis service**
   (which runs Bayesian inference and produces the narrative debrief).
3. **Data tier** — PostgreSQL for persistent storage of users, sessions,
   scenarios, and decisions. Redis is provisioned in `docker-compose.yml` for
   future use as an aggregate-benchmark cache; the application does not yet
   read from it.

## The experimental-design contract

The central design contract of BlindSpot is that **every comparable decision
the user makes is structurally controlled**. This is what gives the resulting
statistics any analytical bite. Concretely:

- For each scenario, the `ProfileGenerator` selects a single qualification
  template and stamps it onto both candidates in a pair.
- The two candidates differ along **exactly one** demographic dimension
  (currently gender-coded names or ethnicity-coded names).
- Server payloads carry the privileged/counterpart labelling; client payloads
  do not. The frontend cannot tell which candidate is "supposed" to be
  favoured.

The `ScenarioEngine.evaluate_decision` static method consumes the manager's
choice and the server-side variant labels and emits a boolean — `True` if the
choice favoured the privileged variant, `False` if it favoured the counterpart,
`None` if the choice was symmetric. This is the only signal the analysis
service consumes.

## Bayesian analysis

For each session we compute a posterior over `p`, the manager's underlying
tendency to favour the privileged variant on a comparable-qualifications
decision:

```
p ~ Beta(α₀, β₀)
favoured_i ~ Bernoulli(p)   for i ∈ informative decisions
p | data ~ Beta(α₀ + #favoured, β₀ + #not_favoured)
```

The priors `(α₀, β₀)` are aggregated from per-scene entries in
`app/data/bias_research.py`. They are deliberately mild: the prior mean sits
near 0.55–0.6 (slightly tilted toward bias, matching published audit-study
findings), but a handful of decisions are enough to dominate the prior.

When BlindSpot needs richer models (hierarchical, per-scene-type, or
per-organisation random effects), the natural transition is to swap the
closed-form Beta–Bernoulli update for a PyMC model. The interface in
`services/analysis.py` is small and explicit so this swap is local.

## Auth model

Authentication is JWT-based with bcrypt-hashed passwords. Tokens are issued
on register/login, stored in `localStorage` on the client, and verified by the
`get_current_user` FastAPI dependency on every protected route. The auth
layer is intentionally minimal — it sits behind one dependency and is not
spread across the codebase.

For production deployment the recommended next steps are (a) move tokens to
HTTP-only cookies, (b) add refresh tokens, and (c) wire up OAuth (e.g.,
Google) so managers can sign in with their corporate identity provider.

## Data scope and ethics

All candidate profiles are generated programmatically by the
`ProfileGenerator`. No real applicant, employee, or HR data is ingested
anywhere in the codebase. This is an architectural property, not a policy
note: there is no ingestion endpoint to begin with.

When the project eventually integrates with applicant-tracking systems (e.g.,
Workday or Greenhouse), the recommended pattern is to receive anonymised
aggregate decision data — not individual records — and to use it only to
inform the `AggregateStat` table behind the cross-user benchmark feature.

## Module map

```
backend/app/
├── main.py                ← FastAPI app, middleware, lifespan
├── config.py              ← Settings via pydantic-settings
├── db.py                  ← SQLAlchemy engine & session factory
├── auth.py                ← JWT + bcrypt
├── models.py              ← ORM models
├── schemas.py             ← Request/response shapes
├── routers/               ← HTTP endpoints (auth, sessions, decisions, debrief)
├── services/
│   ├── profile_generator.py   ← Synthetic profile pairs / cohorts
│   ├── scenario_engine.py     ← Builds scenes; evaluates decisions
│   ├── analysis.py            ← Bayesian posterior computation
│   └── narrative.py           ← Debrief text + scene summaries
└── data/
    └── bias_research.py       ← Per-scene research citations + priors

frontend/src/
├── main.tsx               ← React root
├── App.tsx                ← Routes + auth guard
├── styles.css             ← Tailwind base
├── types/                 ← TypeScript mirrors of backend schemas
├── lib/api.ts             ← Fetch wrapper + endpoint client
├── components/            ← Button, Layout, ProgressBar, CandidateCard
├── pages/                 ← LoginPage, HomePage, SimulationPage, DebriefPage
└── scenes/                ← InboxTriage, TimedResume (+ tests)
```

## Future extension points

Items the architecture is shaped around but does not yet implement:

- **Aggregate benchmarking.** `AggregateStat` exists as a table. The analysis
  service should write summary rows on each completed session and read from
  Redis-cached percentiles when rendering the debrief.
- **Remaining scenes.** Performance Calibration, Promotion Ranking, and
  Justified Decision. Each follows the same pattern: a builder method on
  `ScenarioEngine`, an evaluator branch, and a React component in `scenes/`.
- **Personalised assistant.** A debrief-page chat surface that takes the
  posterior and scene summaries as context. The simplest hook is a new
  router that proxies to an LLM provider and grounds responses in the
  session's own data.
- **Admin views.** The `HR Admin` role from the use-case diagram needs its
  own routers and dashboard. The model layer already supports per-user
  scoping; the missing piece is org-level grouping.
