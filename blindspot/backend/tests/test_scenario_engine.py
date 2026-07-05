"""Tests for the v2 scenario engine — role-coherent, conflict-trial design."""

from app.services.scenario_engine import MERIT_FOLLOW_RATE, ScenarioEngine


def test_each_context_builds_ten_scenes_with_two_timed():
    engine = ScenarioEngine(seed=0)
    for context in ("hiring", "promotion", "review"):
        plans = engine.build_scenes(context=context)
        assert len(plans) == 10
        timed = [p for p in plans if p.timed]
        assert len(timed) == 2
        # Timed scenes are triage (a snap shortlist under the clock).
        assert all(t.scene_type == "inbox_triage" for t in timed)
        # And they are spread apart, not back to back.
        timed_idx = [i for i, p in enumerate(plans) if p.timed]
        assert timed_idx[1] - timed_idx[0] >= 2


def test_contexts_have_distinct_mixes_and_framing():
    engine = ScenarioEngine(seed=1)
    mixes, first_instructions = {}, {}
    for context in ("hiring", "promotion", "review"):
        plans = ScenarioEngine(seed=1).build_scenes(context=context)
        mixes[context] = tuple(p.scene_type for p in plans)
        first_instructions[context] = plans[0].client_payload["instruction"]
    assert len(set(mixes.values())) == 3, "contexts must differ in scene mix"
    assert len(set(first_instructions.values())) == 3, "framing must differ"


def test_triage_is_one_role_with_merit_tiers():
    engine = ScenarioEngine(seed=2)
    triage = next(p for p in engine.build_scenes(context="hiring")
                  if p.scene_type == "inbox_triage")
    cands = triage.server_payload["candidates"]
    assert len(cands) == 12
    assert len({c["headline"] for c in cands}) == 1, "all applicants share ONE role"
    assert triage.client_payload["role"] == cands[0]["headline"]
    assert len(triage.server_payload["strong_ids"]) == 2
    assert len(triage.server_payload["weak_ids"]) == 6
    assert len(triage.server_payload["privileged_ids"]) == 2
    assert len(triage.server_payload["counterpart_ids"]) == 2
    # Strong candidates must visibly outrank borderline ones on experience.
    by_id = {c["id"]: c for c in cands}
    strong_years = min(by_id[i]["years_experience"] for i in triage.server_payload["strong_ids"])
    borderline_years = max(by_id[i]["years_experience"]
                           for i in triage.server_payload["privileged_ids"])
    assert strong_years > borderline_years


def test_calibration_conflict_trials_set_base_rate():
    seen_bases = set()
    for seed in range(12):
        engine = ScenarioEngine(seed=seed)
        for p in engine.build_scenes(context="review"):
            if p.scene_type == "performance_calibration":
                edge = p.server_payload["merit_edge"]
                base = p.server_payload["privileged_base_rate"]
                if edge == "privileged":
                    assert base == MERIT_FOLLOW_RATE
                elif edge == "counterpart":
                    assert base == 1 - MERIT_FOLLOW_RATE
                else:
                    assert base == 0.5
                seen_bases.add(base)
    assert {0.25, 0.5, 0.75} <= seen_bases, "all three trial types must occur"


def test_ranking_base_rate_accounts_for_edge_and_composition():
    for seed in range(10):
        engine = ScenarioEngine(seed=seed)
        for p in engine.build_scenes(context="promotion"):
            if p.scene_type != "promotion_ranking":
                continue
            n_priv = len(p.server_payload["privileged_ids"])
            edge = p.server_payload["merit_edge"]
            base = p.server_payload["privileged_base_rate"]
            if edge is None:
                assert base == n_priv / 3
            else:
                e_a = 1 if edge == "privileged" else 0
                expected = MERIT_FOLLOW_RATE * e_a + (1 - MERIT_FOLLOW_RATE) * (n_priv - e_a) / 2
                assert abs(base - expected) < 1e-9


def test_client_payload_never_leaks_labels():
    engine = ScenarioEngine(seed=4)
    for plan in engine.build_scenes(context="hiring"):
        for key in ("privileged_ids", "counterpart_ids", "privileged_id",
                    "counterpart_id", "privileged_base_rate", "pairs",
                    "merit_edge", "strong_ids", "weak_ids"):
            assert key not in plan.client_payload, f"{key} leaked in {plan.scene_type}"


def test_evaluate_triage_counts_only_borderline_picks():
    server = {"privileged_ids": ["p1", "p2"], "counterpart_ids": ["c1", "c2"]}
    # Strong/weak picks are invisible to the signal; only borderline counts.
    assert ScenarioEngine.evaluate_decision(
        scene_type="inbox_triage", server_payload=server,
        choice={"selected_ids": ["s1", "s2", "p1", "p2"]}) is True
    assert ScenarioEngine.evaluate_decision(
        scene_type="inbox_triage", server_payload=server,
        choice={"selected_ids": ["s1", "s2", "p1", "c1"]}) is None
