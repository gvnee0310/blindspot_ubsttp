# BlindSpot

> A decision simulation platform for unconscious bias reflection.
>
> *Making the invisible visible — one decision at a time.*

BlindSpot lets managers experience, measure, and reflect on their own
unconscious biases through realistic hiring, promotion, and performance-review
scenarios. Rather than analysing what a manager *says*, BlindSpot analyses
what a manager *does* when presented with carefully constructed candidate
profiles whose qualifications are held constant while demographic signals are
deliberately varied.

This repository is the proof-of-concept implementation prepared for the UBS
Tomorrow's Talent Program 2026.

---

## Architecture at a glance

```
┌───────────────────────────────────────────────────────────────┐
│  Frontend: React + TypeScript + TailwindCSS (Vite)            │
│  • Scenario flow state machine                                │
│  • Decision capture (cards, sliders, ranking)                 │
│  • Debrief dashboard (Recharts)                               │
└───────────────────────┬───────────────────────────────────────┘
                        │ HTTPS / JSON
┌───────────────────────▼───────────────────────────────────────┐
│  Backend: FastAPI (Python 3.12)                               │
│  • Profile generator (Faker + custom variant controller)      │
│  • Scenario engine                                            │
│  • Bayesian analysis (Beta–Bernoulli posterior updates)       │
│  • Narrative debrief generator                                │
└───────────────────────┬───────────────────────────────────────┘
                        │
┌───────────────────────▼───────────────────────────────────────┐
│  Data layer: PostgreSQL (dev: SQLite) + Redis                 │
└───────────────────────────────────────────────────────────────┘
```

For the full architectural rationale, see
[`docs/architecture.md`](docs/architecture.md).

---

## Quick start (Docker)

The fastest way to run the whole stack:

```bash
git clone <this-repo>
cd blindspot
cp .env.example .env
docker compose up --build
```

The frontend will be served at `http://localhost:5173` and the API at
`http://localhost:8000` (OpenAPI docs at `http://localhost:8000/docs`).

---

## Local development (without Docker)

### Backend

Requires Python 3.12+.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The dev server uses SQLite (`blindspot.db` in the backend folder). To use
PostgreSQL, set `DATABASE_URL` in your environment.

### Frontend

Requires Node 20+.

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies API calls to `http://localhost:8000`.

---

## Tests

```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm test
```

---

## Repository layout

```
blindspot/
├── README.md                  ← you are here
├── ROADMAP.md                 ← 10-week mentorship build plan
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py            ← FastAPI entry point
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── models.py          ← SQLAlchemy models
│   │   ├── schemas.py         ← Pydantic schemas
│   │   ├── auth.py            ← JWT auth
│   │   ├── routers/           ← HTTP endpoints
│   │   ├── services/          ← Core business logic
│   │   └── data/              ← Bias-research reference library
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── pages/             ← Top-level page components
│   │   ├── scenes/            ← Individual scene implementations
│   │   ├── components/        ← Reusable UI components
│   │   ├── lib/               ← API client, utilities
│   │   └── types/             ← TypeScript types
│   └── tests/
└── docs/
    └── architecture.md
```

---

## Status

This implementation covers **Weeks 1–6** of the 10-week mentorship roadmap.
See [`ROADMAP.md`](ROADMAP.md) for the full mapping.

**What works today:**

- End-to-end session flow (Start → 3 scenes → debrief → History)
- Synthetic candidate-profile generation with controlled demographic variation
- All three scene types from the roadmap (Inbox Triage, Performance Calibration,
  Promotion Ranking) fully implemented in both backend and frontend
- **Descriptive analytics** (NumPy / SciPy):
  - Counts, selection proportions, Wilson 95% confidence intervals
  - Paired t-test on Performance Calibration ratings
  - Per-scene bar chart with the 50% baseline marked
- **Bayesian inference** (PyMC):
  - Logistic-parameterised model fit by MCMC
  - Posterior mean, 95% HDI, P(p > 0.5), P(p > 0.6)
  - Sample-based density plot in the debrief dashboard
- Session history page
- Basic JWT auth

**What's left for Weeks 7–10:**

- Aggregate benchmark across users (Redis cache layer)
- Hierarchical PyMC model with per-scene-type random effects
- Admin dashboard for HR-level views
- Cloud deployment + async MCMC
- Final demo prep

---

## License

MIT — see [`LICENSE`](LICENSE).
