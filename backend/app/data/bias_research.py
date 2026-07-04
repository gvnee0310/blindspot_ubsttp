"""Reference library of published bias research.

Entries pair a (scene type, variant dimension) with a citation and summary
used in the debrief narrative for CONTEXT ONLY. Since the statistical
revision, this library plays no role in the individual inference — the
Bayesian model uses a neutral prior so that a manager with no data is not
told they are probably biased. Population-level findings inform the reader;
they do not prejudge the individual.

Direction conventions referenced here (male / Chinese-majority / Western-
expatriate as the historically advantaged signal) follow the audit-study
literature for professional hiring, including resume-audit research conducted
in Singapore's multi-ethnic labour market. They are pooling conventions, not
moral claims, and the analysis is symmetric in both directions.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchEntry:
    citation: str
    summary: str


RESEARCH_LIBRARY: dict[tuple[str, str], ResearchEntry] = {
    ("inbox_triage", "gender"): ResearchEntry(
        citation="Moss-Racusin et al. (2012), PNAS",
        summary=(
            "Identical applications were rated significantly more hireable when "
            "bearing a male name than a female name."
        ),
    ),
    ("inbox_triage", "race"): ResearchEntry(
        citation="Bertrand & Mullainathan (2004), AER; resume-audit studies in Singapore",
        summary=(
            "Resume-audit experiments — including studies run in Singapore's labour "
            "market — find lower callback rates for minority-named candidates than for "
            "majority-named candidates with identical qualifications."
        ),
    ),
    ("inbox_triage", "nationality"): ResearchEntry(
        citation="Expatriate-premium literature in multinational labour markets",
        summary=(
            "Studies of professional hiring in international hubs document systematic "
            "advantages for Western expatriate candidates in shortlisting and pay."
        ),
    ),
    ("performance_calibration", "gender"): ResearchEntry(
        citation="Correll et al. (2007), AJS; Heilman (2012)",
        summary=(
            "Performance evaluations show small but consistent effects favouring men "
            "over equivalently performing women, especially on subjective criteria."
        ),
    ),
    ("performance_calibration", "race"): ResearchEntry(
        citation="Resume- and evaluation-audit literature, incl. Singapore studies",
        summary=(
            "Evaluation experiments find minority-named employees receive lower "
            "subjective ratings for identical documented performance."
        ),
    ),
    ("performance_calibration", "nationality"): ResearchEntry(
        citation="Expatriate-premium literature",
        summary=(
            "Subjective performance criteria tend to favour expatriate profiles in "
            "multinational professional settings."
        ),
    ),
    ("promotion_ranking", "gender"): ResearchEntry(
        citation="Heilman (2012), Research in Organizational Behavior",
        summary=(
            "Promotion recommendations show consistent effects favouring men over "
            "equivalently qualified women."
        ),
    ),
    ("promotion_ranking", "race"): ResearchEntry(
        citation="Audit-study literature, incl. Singapore's labour market",
        summary=(
            "Advancement decisions replicate the callback gaps found in hiring audits: "
            "majority-named candidates are promoted at higher rates than matched "
            "minority-named candidates."
        ),
    ),
    ("promotion_ranking", "nationality"): ResearchEntry(
        citation="Expatriate-premium literature",
        summary=(
            "Leadership pipelines in international firms over-select expatriate "
            "profiles relative to equally qualified local candidates."
        ),
    ),
}

DEFAULT_RESEARCH = ResearchEntry(
    citation="Aggregated audit-study evidence",
    summary=(
        "Audit studies consistently find small-to-moderate effects of demographic "
        "signals on hiring and evaluation decisions when qualifications are held "
        "constant."
    ),
)


def lookup_research(scene_type: str, variant_dimension: str) -> ResearchEntry:
    return RESEARCH_LIBRARY.get((scene_type, variant_dimension), DEFAULT_RESEARCH)
