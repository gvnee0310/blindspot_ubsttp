from __future__ import annotations

from collections.abc import Sequence

from app.models import Decision, Scenario


def build_reveal(scenarios: Sequence[Scenario], decisions: Sequence[Decision]) -> list[dict]:
    by_id = {d.scenario_id: d for d in decisions}
    items: list[dict] = []

    for sc in scenarios:
        d = by_id.get(sc.id)
        if d is None:
            continue

        if sc.scene_type == "inbox_triage":
            selected = set(d.choice.get("selected_ids", []))
            for pair in sc.payload.get("pairs", []):
                priv, cnt = pair.get("privileged"), pair.get("counterpart")
                if not priv or not cnt:
                    continue
                p_in, c_in = priv["id"] in selected, cnt["id"] in selected
                if p_in and c_in:
                    action = "You shortlisted both."
                elif p_in:
                    action = f"You shortlisted {priv['name']} but not {cnt['name']}."
                elif c_in:
                    action = f"You shortlisted {cnt['name']} but not {priv['name']}."
                else:
                    action = "You shortlisted neither."
                items.append({
                    "scene_type": "inbox_triage",
                    "headline": pair.get("headline", ""),
                    "privileged_names": [priv["name"]],
                    "counterpart_names": [cnt["name"]],
                    "what_you_did": action,
                })

        elif sc.scene_type == "performance_calibration":
            ratings = d.choice.get("ratings", {})
            for pair in sc.payload.get("pairs", []):
                priv, cnt = pair.get("privileged"), pair.get("counterpart")
                if not priv or not cnt:
                    continue
                pr, cr = ratings.get(priv["id"]), ratings.get(cnt["id"])
                if pr is None or cr is None:
                    action = "Ratings incomplete."
                elif pr == cr:
                    action = f"You rated both {pr}/5, exactly the same."
                else:
                    hi, lo = (priv, cnt) if pr > cr else (cnt, priv)
                    action = (
                        f"You rated {hi['name']} {max(pr, cr)}/5 and "
                        f"{lo['name']} {min(pr, cr)}/5."
                    )
                edge = pair.get("merit_edge")
                if edge == "counterpart":
                    action += f" ({cnt['name']} had the stronger record.)"
                elif edge == "privileged":
                    action += f" ({priv['name']} had the stronger record.)"
                items.append({
                    "scene_type": "performance_calibration",
                    "headline": pair.get("headline", ""),
                    "privileged_names": [priv["name"]],
                    "counterpart_names": [cnt["name"]],
                    "what_you_did": action,
                })

        elif sc.scene_type == "promotion_ranking":
            ranking = d.choice.get("ranking", [])
            for pair in sc.payload.get("pairs", []):
                privs = pair.get("privileged", [])
                cnts = pair.get("counterpart", [])
                all_c = {c["id"]: c["name"] for c in privs + cnts}
                top_name = all_c.get(ranking[0]) if ranking else None
                action = (
                    f"You ranked {top_name} first out of three equally qualified candidates."
                    if top_name else "No ranking submitted."
                )
                edge = pair.get("merit_edge")
                if edge == "counterpart":
                    action += " (One of the others actually had the stronger record.)"
                items.append({
                    "scene_type": "promotion_ranking",
                    "headline": pair.get("headline", ""),
                    "privileged_names": [c["name"] for c in privs],
                    "counterpart_names": [c["name"] for c in cnts],
                    "what_you_did": action,
                })

    return items
