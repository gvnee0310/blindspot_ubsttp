"""Tests for the matched-pair profile generator.

Within any pair, EXACTLY ONE signal varies.
Race pairs hold gender constant; gender pairs hold ethnicity constant;
nationality pairs hold gender constant.
"""

from app.services.profile_generator import SG_NAME_POOLS, ProfileGenerator


def _pool(eth, g):
    return set(SG_NAME_POOLS[(eth, g)])


CHINESE = _pool("chinese", "male") | _pool("chinese", "female")
MALAY = _pool("malay", "male") | _pool("malay", "female")
INDIAN = _pool("indian", "male") | _pool("indian", "female")
WESTERN = _pool("western", "male") | _pool("western", "female")
MALE = {n for (e, g), pool in SG_NAME_POOLS.items() if g == "male" for n in pool}
FEMALE = {n for (e, g), pool in SG_NAME_POOLS.items() if g == "female" for n in pool}


def _ethnicity_of(name: str) -> str:
    for eth, pool in (("chinese", CHINESE), ("malay", MALAY),
                      ("indian", INDIAN), ("western", WESTERN)):
        if name in pool:
            return eth
    raise AssertionError(f"Unknown name {name}")


def test_pair_matched_qualifications_different_wording():
    gen = ProfileGenerator(seed=42)
    priv, cnt, _ = gen.generate_pair(variant_dimension="gender")
    assert priv.headline == cnt.headline
    assert priv.years_experience == cnt.years_experience
    assert priv.education == cnt.education
    assert sorted(priv.skills) == sorted(cnt.skills)
    assert priv.highlights != cnt.highlights
    assert priv._pair_id == cnt._pair_id


def test_gender_pair_holds_ethnicity_constant():
    gen = ProfileGenerator(seed=1)
    for _ in range(10):
        priv, cnt, _ = gen.generate_pair(variant_dimension="gender")
        assert priv.name in MALE and cnt.name in FEMALE
        assert _ethnicity_of(priv.name) == _ethnicity_of(cnt.name)


def test_race_pair_holds_gender_constant():
    gen = ProfileGenerator(seed=2)
    for _ in range(10):
        priv, cnt, _ = gen.generate_pair(variant_dimension="race")
        assert priv.name in CHINESE
        assert cnt.name in (MALAY | INDIAN)
        same_gender = (priv.name in MALE) == (cnt.name in MALE)
        assert same_gender, "race pair must not also vary gender"


def test_nationality_pair_holds_gender_constant():
    gen = ProfileGenerator(seed=3)
    for _ in range(10):
        priv, cnt, _ = gen.generate_pair(variant_dimension="nationality")
        assert priv.name in WESTERN
        assert cnt.name in (CHINESE | MALAY | INDIAN)
        assert (priv.name in MALE) == (cnt.name in MALE)


def test_matched_cohort_enforces_pairing_and_unique_names():
    gen = ProfileGenerator(seed=7)
    cohort = gen.generate_matched_cohort(n_pairs=6, variant_dimension="race")
    assert len(cohort) == 12
    names = [c.name for c in cohort]
    assert len(names) == len(set(names))
    by_pair: dict[int, list] = {}
    for c in cohort:
        by_pair.setdefault(c._pair_id, []).append(c)
    assert len(by_pair) == 6
    for members in by_pair.values():
        assert {m._variant_role for m in members} == {"privileged", "counterpart"}
        a, b = members
        assert a.headline == b.headline
        assert a.years_experience == b.years_experience


def test_triple_single_template_and_constant_non_target_signals():
    gen = ProfileGenerator(seed=9)
    triple, _ = gen.generate_triple(variant_dimension="race", privileged_count=2)
    assert len({c.headline for c in triple}) == 1
    assert len({tuple(c.highlights) for c in triple}) == 3
    genders = {("m" if c.name in MALE else "f") for c in triple}
    assert len(genders) == 1, "ranking triple must hold gender constant"


def test_public_dict_strips_internal_fields():
    gen = ProfileGenerator(seed=0)
    priv, _, _ = gen.generate_pair(variant_dimension="gender")
    public = priv.public_dict()
    assert "_variant_role" not in public
    assert "_pair_id" not in public


def test_role_cohort_has_diverse_education_but_equal_within_pairs():
    """Each of the 12 applicants should bring varied schools, but the matched
    borderline pairs must share education (only the name differs)."""
    from app.services.profile_generator import ProfileGenerator
    gen = ProfileGenerator(seed=11)
    cohort = gen.generate_role_cohort(variant_dimension="race")
    edus = [c.education for c in cohort["candidates"]]
    # At least 4 distinct schools among 12 applicants.
    assert len(set(edus)) >= 4, f"education not diverse: {set(edus)}"
    # Within each matched pair, education and years are identical.
    by_pair: dict[int, list] = {}
    for c in cohort["pairs"]:
        by_pair.setdefault(c._pair_id, []).append(c)
    for members in by_pair.values():
        a, b = members
        assert a.education == b.education
        assert a.years_experience == b.years_experience
        # Company line must match too.
        assert a.highlights[-1] == b.highlights[-1]
