"""Discipline rules encode the reviewer's definitions (blind validation,
2026-10-02): the organism or habitat system named in the title decides the
label, herpetology is Wildlife, and microbiology/toxicology are not
Environmental Sciences."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from wildlife_grad.analysis.enhanced_analysis import (  # noqa: E402
    DisciplineClassifier,
    JobPosition,
)

# Boilerplate as habitat-heavy as the 95th-percentile real posting (real
# Forestry and Habitat keyword scores: median 1, p90 4, p95 5, max 10).
HABITAT_NOISE = (
    "Graduate research assistantship. The project involves habitat restoration "
    "and habitat management across managed forest. "
)


def classify(title, description=HABITAT_NOISE):
    position = JobPosition(
        title=title,
        organization="State University",
        location="Texas",
        salary="",
        starting_date="",
        published_date="",
        tags="Graduate Opportunities",
        description=description,
    )
    return DisciplineClassifier().classify_position(position)[0]


@pytest.mark.parametrize(
    "title",
    [
        "M.S. Assistantship: Population trends of forest birds",
        "MS Graduate Research Assistant (Mexican Ducks and Managed Wetlands)",
        "PhD Position - Texas tortoise ecology and conservation",
        "M.S. Position - Using drones to study urban parrots",
        "MS Assistantship - Turtle Research in the Coastal Ecology Lab",
    ],
)
def test_organism_in_title_beats_habitat_words_in_description(title):
    assert classify(title) == "Wildlife"


def test_pollinator_habitat_restoration_stays_entomology():
    assert classify("Graduate student (M.S.) - Roadside pollinator habitat restoration") == "Entomology"


@pytest.mark.parametrize(
    "title",
    [
        "Ph.D/MS Positions: Coastal/Urban wetland ecology",
        "MS position - impacts of global change drivers on dryland plant communities",
    ],
)
def test_habitat_system_in_title_is_forestry_and_habitat(title):
    assert classify(title, description="Graduate position. Climate change research.") == "Forestry and Habitat"


@pytest.mark.parametrize(
    "title", ["Graduate Assistantship in Environmental Microbiology", "Doctoral Student in Environmental Toxicology"]
)
def test_microbiology_and_toxicology_are_not_environmental_sciences(title):
    assert classify(title, description="Graduate assistantship position.") != "Environmental Sciences"


def test_fixture_is_as_noisy_as_a_95th_percentile_posting():
    # Guards the calibration above: too quiet makes the tests trivially easy,
    # too loud makes the rule look broken on postings that do not exist.
    classifier = DisciplineClassifier()
    scores = classifier._keyword_classify_with_scores(HABITAT_NOISE.lower())[2]
    assert 4 <= scores.get("Forestry and Habitat", 0) <= 6
