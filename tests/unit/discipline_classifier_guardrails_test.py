"""Regression tests for discipline classification guardrails."""

import sys
from pathlib import Path

# Ensure src/ is importable when running tests from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from wildlife_grad.analysis.enhanced_analysis import DisciplineClassifier, JobPosition


def make_position(title: str, tags: str = "", description: str = "") -> JobPosition:
    return JobPosition(
        title=title,
        organization="Test Org",
        location="Test, State",
        salary="$25,000",
        starting_date="2026-08-01",
        published_date="2026-02-15",
        tags=tags,
        description=description,
    )


def test_fisheries_position_maps_to_fisheries_and_aquatic() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "PhD Graduate Research Assistantship in Fisheries Ecology",
        description="Fish passage and hatchery restoration work.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary == "Fisheries and Aquatic"


def test_entomology_position_maps_to_entomology() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "MS Assistantship in Insect Ecology",
        description="Pollinator communities, bees, and arthropod sampling.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary == "Entomology"


def test_human_dimensions_requires_social_context() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "MS Assistantship in Human Dimensions of Wildlife Conservation",
        description="Stakeholder survey and interview design.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary == "Human Dimensions"


def test_environmental_sciences_focuses_on_soil_and_water() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "MS in Watershed Biogeochemistry",
        description="Soil chemistry, hydrology, and water quality modeling.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary == "Environmental Sciences"


def test_forestry_and_habitat_maps_correctly() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "Graduate Assistantship in Forest Habitat Restoration",
        description="Forest stand structure, tree regeneration, and habitat management.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary == "Forestry and Habitat"


def test_agriculture_maps_from_cattle_and_ranching_terms() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "PhD Assistantship in Rangeland Cattle Systems",
        description="Livestock grazing, ranch management, and pasture productivity.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary == "Agriculture"


def test_humane_society_text_does_not_force_human_dimensions() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "Associate Veterinarian",
        description="Clinical care role at humane society.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary != "Human Dimensions"


def test_ambiguous_certificate_text_returns_other() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "Professional Certificate: Conservation Planning",
        description="Short professional certificate program.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary == "Other"


def test_archaeologist_role_returns_other() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "Archaeologist",
        description="Cultural resource survey and compliance work.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary == "Other"


def test_environmental_field_technician_returns_other() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "Environmental Field Technician",
        description="Rapid responder field sampling and incident support.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary == "Other"
