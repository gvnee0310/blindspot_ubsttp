"""End-to-end smoke test: full 7-scene session through to the debrief."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    tmpdb = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmpdb.close()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmpdb.name}")
    from app import config

    config.get_settings.cache_clear()
    from app import db, main

    db.engine.dispose()
    db.engine = db.create_engine(  # type: ignore[attr-defined]
        f"sqlite:///{tmpdb.name}", connect_args={"check_same_thread": False}, future=True
    )
    db.SessionLocal.configure(bind=db.engine)
    db.init_db()

    yield TestClient(main.app)
    os.unlink(tmpdb.name)


def _make_choice(scenario: dict) -> dict:
    scene_type = scenario["scene_type"]
    candidates = scenario["payload"]["candidates"]
    if scene_type == "inbox_triage":
        n = scenario["payload"]["select_count"]
        return {"selected_ids": [c["id"] for c in candidates[:n]]}
    if scene_type == "performance_calibration":
        return {"ratings": {candidates[0]["id"]: 5, candidates[1]["id"]: 3}}
    if scene_type == "promotion_ranking":
        return {"ranking": [c["id"] for c in candidates]}
    return {}


def test_full_session_flow(client: TestClient):
    r = client.post(
        "/auth/register",
        json={"email": "t@example.com", "display_name": "T", "password": "password123"},
    )
    assert r.status_code == 201, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = client.post("/sessions/", json={"context": "hiring"}, headers=headers)
    assert r.status_code == 201, r.text
    session = r.json()
    scene_types = [sc["scene_type"] for sc in session["scenarios"]]
    assert len(scene_types) == 10
    assert sum(1 for sc in session["scenarios"] if sc["timed"]) == 2
    for sc in session["scenarios"]:
        assert sc["payload"].get("role"), "every scene must name the role"
    for sc in session["scenarios"]:
        # No labelling may leak to the client
        for key in ("privileged_ids", "counterpart_ids", "privileged_id",
                    "counterpart_id", "privileged_base_rate", "pairs"):
            assert key not in sc["payload"], f"{key} leaked"
        for key in ("merit_edge", "strong_ids", "weak_ids"):
            assert key not in sc["payload"], f"{key} leaked"

    for scenario in session["scenarios"]:
        body = {
            "scenario_id": scenario["id"],
            "choice": _make_choice(scenario),
            "elapsed_ms": 4200,
        }
        if scenario["scene_type"] == "promotion_ranking":
            body["justification"] = "Strongest delivery track record of the three."
        r = client.post("/decisions/", json=body, headers=headers)
        assert r.status_code == 201, r.text

    r = client.post(f"/sessions/{session['id']}/complete", headers=headers)
    assert r.status_code == 200

    r = client.get(f"/debrief/{session['id']}", headers=headers)
    assert r.status_code == 200, r.text
    debrief = r.json()

    assert "headline" in debrief
    assert len(debrief["narrative"]) >= 3
    assert len(debrief["scenes"]) == 10

    desc = debrief["descriptive"]
    assert desc["overall"]["total"] >= 2
    assert len(desc["by_dimension"]) >= 2           # plain-language group tallies
    assert desc["paired_ratings"] is not None
    rank_row = next(b for b in desc["by_scene"] if b["scene_type"] == "promotion_ranking")
    assert rank_row["expected_rate"] is not None    # asymmetric null surfaced

    bayes = debrief["bayesian"]
    assert 0.0 < bayes["posterior_mean"] < 1.0
    assert bayes["hdi_low"] < bayes["hdi_high"]
    assert bayes["n_observations"] >= 5
    assert len(bayes["samples"]) > 0

    # Post-session reveal unmasks the matched pairs
    assert len(debrief["reveal"]) >= 6
    sample = debrief["reveal"][0]
    assert {"scene_type", "headline", "privileged_names",
            "counterpart_names", "what_you_did"} <= set(sample.keys())
