from __future__ import annotations

from dataclasses import dataclass

from app.services.profile_generator import ProfileGenerator, VariantDimension

MERIT_FOLLOW_RATE = 0.75


@dataclass
class ScenePlan:
    scene_type: str
    timed: bool
    variant_dimension: VariantDimension
    server_payload: dict
    client_payload: dict


class ScenarioEngine:
    _CONTEXT_PLANS: dict[str, list[tuple[str, VariantDimension, bool]]] = {
        "hiring": [
            ("inbox_triage", "gender", False),
            ("promotion_ranking", "race", False),
            ("performance_calibration", "nationality", False),
            ("inbox_triage", "race", True),
            ("performance_calibration", "gender", False),
            ("promotion_ranking", "nationality", False),
            ("performance_calibration", "race", False),
            ("inbox_triage", "gender", True),
            ("promotion_ranking", "gender", False),
            ("performance_calibration", "race", False),
        ],
        "promotion": [
            ("promotion_ranking", "gender", False),
            ("performance_calibration", "race", False),
            ("promotion_ranking", "race", False),
            ("inbox_triage", "nationality", True),
            ("performance_calibration", "gender", False),
            ("promotion_ranking", "nationality", False),
            ("performance_calibration", "race", False),
            ("inbox_triage", "race", True),
            ("promotion_ranking", "race", False),
            ("performance_calibration", "nationality", False),
        ],
        "review": [
            ("performance_calibration", "gender", False),
            ("performance_calibration", "race", False),
            ("promotion_ranking", "gender", False),
            ("inbox_triage", "race", True),
            ("performance_calibration", "nationality", False),
            ("promotion_ranking", "race", False),
            ("performance_calibration", "gender", False),
            ("inbox_triage", "nationality", True),
            ("promotion_ranking", "nationality", False),
            ("performance_calibration", "race", False),
        ],
    }


    _FRAMING: dict[tuple[str, str], str] = {
        ("hiring", "inbox_triage"):
            "You're hiring a {role}. 12 applications, 4 interview slots. Pick your 4.",
        ("hiring", "promotion_ranking"):
            "Final round for the {role} opening. Rank the 3 finalists, then say why your #1 wins.",
        ("hiring", "performance_calibration"):
            "Two interviewers sent write-ups on the {role} shortlist. Score each write-up 1 to 5.",
        ("promotion", "promotion_ranking"):
            "One promotion slot on your {role} team. Rank the 3 candidates, then justify your #1.",
        ("promotion", "performance_calibration"):
            "Promotion-readiness check. Rate these two {role}s from 1 (not ready) to 5 (ready now).",
        ("promotion", "inbox_triage"):
            "Leadership programme nominations close in 60 seconds. Pick 4 of these 12 {role}s.",
        ("review", "performance_calibration"):
            "Mid-year review. Rate these two {role}s on their half-year, 1 to 5.",
        ("review", "promotion_ranking"):
            "Bonus pool. Stack-rank these three {role}s, and add a short note on your #1.",
        ("review", "inbox_triage"):
            "Excellence award. Nominations close in 60 seconds. Pick 4 of these 12 {role}s.",
    }

    TRIAGE_SELECT = 4
    TIMER_SECONDS = 60

    def __init__(self, *, seed: int | None = None) -> None:
        self._generator = ProfileGenerator(seed=seed)

    def build_scenes(self, *, context: str) -> list[ScenePlan]:
        spec = self._CONTEXT_PLANS.get(context)
        if spec is None:
            raise ValueError(f"Unknown simulation context: {context}")
        used_templates: set[int] = set()
        plans: list[ScenePlan] = []
        for scene_type, variant, timed in spec:
            if scene_type == "inbox_triage":
                plans.append(self._build_triage(context, variant, timed=timed))
            elif scene_type == "performance_calibration":
                plans.append(self._build_calibration(context, variant, used_templates))
            else:
                plans.append(self._build_ranking(context, variant, used_templates))
        return plans

    def _frame(self, context: str, scene_type: str, role: str) -> str:
        return self._FRAMING[(context, scene_type)].format(role=role)

    # ------------------------------------------------------------- builders

    def _build_triage(self, context: str, variant: VariantDimension, *, timed: bool) -> ScenePlan:
        cohort = self._generator.generate_role_cohort(variant_dimension=variant)
        role = cohort["role"]
        client_payload = {
            "role": role,
            "instruction": self._frame(context, "inbox_triage", role),
            "candidates": [c.public_dict() for c in cohort["candidates"]],
            "select_count": self.TRIAGE_SELECT,
            "timer_seconds": self.TIMER_SECONDS if timed else None,
        }
        pairs_meta = {}
        for c in cohort["pairs"]:
            pairs_meta.setdefault(c._pair_id, {})[c._variant_role] = {"id": c.id, "name": c.name}
        server_payload = {
            **client_payload,
            "privileged_ids": cohort["privileged_ids"],
            "counterpart_ids": cohort["counterpart_ids"],
            "strong_ids": cohort["strong_ids"],
            "weak_ids": cohort["weak_ids"],
            "pairs": [
                {"headline": role, "privileged": r.get("privileged"),
                 "counterpart": r.get("counterpart")}
                for r in pairs_meta.values()
            ],
        }
        return ScenePlan("inbox_triage", timed, variant, server_payload, client_payload)

    def _build_calibration(self, context: str, variant: VariantDimension,
                           used_templates: set[int]) -> ScenePlan:
        priv, cnt, tidx = self._generator.generate_pair(
            variant_dimension=variant, exclude_templates=used_templates)
        used_templates.add(tidx)

        # Conflict-trial design: 1/3 edge to majority-signal, 1/3 to
        # minority-signal, 1/3 equal.
        edge = self._generator._rng.choice(["privileged", "counterpart", None])
        if edge == "privileged":
            self._generator.apply_merit_edge(priv)
            base_rate = MERIT_FOLLOW_RATE
        elif edge == "counterpart":
            self._generator.apply_merit_edge(cnt)
            base_rate = 1.0 - MERIT_FOLLOW_RATE
        else:
            base_rate = 0.5

        role = priv.headline
        display = [priv.public_dict(), cnt.public_dict()]
        self._generator._rng.shuffle(display)
        client_payload = {
            "role": role,
            "instruction": self._frame(context, "performance_calibration", role),
            "candidates": display,
            "rating_scale": {"min": 1, "max": 5, "labels": [
                "Needs improvement", "Below expectations", "Meets expectations",
                "Exceeds expectations", "Exceptional"]},
        }
        server_payload = {
            **client_payload,
            "privileged_id": priv.id,
            "counterpart_id": cnt.id,
            "merit_edge": edge,
            "privileged_base_rate": base_rate,
            "pairs": [{"headline": role,
                       "privileged": {"id": priv.id, "name": priv.name},
                       "counterpart": {"id": cnt.id, "name": cnt.name},
                       "merit_edge": edge}],
        }
        return ScenePlan("performance_calibration", False, variant, server_payload, client_payload)

    def _build_ranking(self, context: str, variant: VariantDimension,
                       used_templates: set[int]) -> ScenePlan:
        privileged_count = self._generator._rng.choice([1, 2])
        triple, tidx = self._generator.generate_triple(
            variant_dimension=variant, privileged_count=privileged_count,
            exclude_templates=used_templates)
        used_templates.add(tidx)

        # Merit edge to one random member with probability 2/3.
        edge_holder = None
        if self._generator._rng.random() < 2 / 3:
            edge_holder = self._generator._rng.choice(triple)
            self._generator.apply_merit_edge(edge_holder)
        # follow the edge with MERIT_FOLLOW_RATE, else pick uniformly among the other two.
        if edge_holder is not None:
            e_a = 1 if edge_holder._variant_role == "privileged" else 0
            base_rate = (MERIT_FOLLOW_RATE * e_a
                         + (1 - MERIT_FOLLOW_RATE) * (privileged_count - e_a) / 2)
        else:
            base_rate = privileged_count / 3

        role = triple[0].headline
        client_payload = {
            "role": role,
            "instruction": self._frame(context, "promotion_ranking", role),
            "candidates": [c.public_dict() for c in triple],
            "requires_justification": True,
        }
        server_payload = {
            **client_payload,
            "privileged_ids": [c.id for c in triple if c._variant_role == "privileged"],
            "counterpart_ids": [c.id for c in triple if c._variant_role == "counterpart"],
            "privileged_base_rate": base_rate,
            "merit_edge": None if edge_holder is None else edge_holder._variant_role,
            "pairs": [{"headline": role,
                       "privileged": [{"id": c.id, "name": c.name}
                                       for c in triple if c._variant_role == "privileged"],
                       "counterpart": [{"id": c.id, "name": c.name}
                                        for c in triple if c._variant_role == "counterpart"],
                       "merit_edge": None if edge_holder is None else edge_holder._variant_role}],
        }
        return ScenePlan("promotion_ranking", False, variant, server_payload, client_payload)

    # --------------------------------------------------- display-level signal

    @staticmethod
    def evaluate_decision(*, scene_type: str, server_payload: dict, choice: dict) -> bool | None:
        if scene_type == "inbox_triage":
            selected: list[str] = choice.get("selected_ids", [])
            if not selected:
                return None
            priv = set(server_payload["privileged_ids"])
            cnt = set(server_payload["counterpart_ids"])
            k_p = sum(1 for s in selected if s in priv)
            k_c = sum(1 for s in selected if s in cnt)
            if k_p == k_c:
                return None
            return k_p > k_c
        if scene_type == "performance_calibration":
            ratings: dict[str, int] = choice.get("ratings", {})
            pr = ratings.get(server_payload["privileged_id"])
            cr = ratings.get(server_payload["counterpart_id"])
            if pr is None or cr is None or pr == cr:
                return None
            return pr > cr
        if scene_type == "promotion_ranking":
            ranking: list[str] = choice.get("ranking", [])
            if not ranking:
                return None
            top = ranking[0]
            if top in server_payload["privileged_ids"]:
                return True
            if top in server_payload["counterpart_ids"]:
                return False
            return None
        raise NotImplementedError(scene_type)
