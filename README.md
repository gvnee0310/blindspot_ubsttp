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
│  Backend: FastAPI (Python 3.11)                               │
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


## Local development

### Backend

Requires Python 3.11+.

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



## License

MIT — see [`LICENSE`](LICENSE).
