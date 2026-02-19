"""Regression tests for discipline classification guardrails."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure src/ is importable when running tests from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from wildlife_grad.analysis.enhanced_analysis import (
    HAS_SKLEARN,
    DisciplineClassifier,
    JobPosition,
)


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


def test_ant_colony_maps_to_entomology() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "Graduate Research Assistant/Ant Colony Impacts on Ecosystems",
        description="Ant colony behavior and insect community dynamics.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary == "Entomology"


def test_manta_ray_bycatch_maps_to_fisheries_and_aquatic() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "M.S. Research Assistantship in Manta Ray Conservation and Bycatch Mitigation",
        description="Marine fisheries, bycatch reduction, and manta ray ecology.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary == "Fisheries and Aquatic"


def test_food_security_with_fisheries_context_maps_to_fisheries() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "Ph.D. Research Assistantship in Fisheries Conflict and Food Security",
        description="Fisheries governance and aquatic resource conflict.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary == "Fisheries and Aquatic"


def test_environmental_education_science_communication_maps_to_human_dimensions() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "Environmental Education and Science Communication Fellows - Masters Degree",
        description="Graduate training in environmental education and science communication.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary == "Human Dimensions"


def test_turtle_thesis_maps_to_wildlife() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "Masters Thesis opportunity working with the Rio Grande Cooter",
        description="Field ecology of freshwater turtle populations.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary == "Wildlife"


def test_climate_action_scholarship_maps_to_environmental_sciences() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "PhD Scholarship – Transforming Climate Action",
        description="Climate action and sustainability pathways in uncertain sea futures.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary == "Environmental Sciences"


def test_forest_soils_biogeochemistry_maps_to_environmental_sciences() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "PhD and MS Assistantships in Forest Soils and Biogeochemistry",
        description="Soil chemistry and forest biogeochemistry across environmental gradients.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary == "Environmental Sciences"


def test_ambiguous_title_uses_description_for_discipline_resolution() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "Graduate Research Opportunity",
        description="Insect community dynamics with ant colonies and arthropod monitoring.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary == "Entomology"


def test_strong_title_signal_outweighs_noisy_description() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "PhD Assistantship in Fisheries Ecology",
        description="Includes broad climate and stakeholder language in project context.",
    )

    primary, _secondary = clf.classify_position(pos)
    assert primary == "Fisheries and Aquatic"


def test_ml_refines_ambiguous_other_when_confident() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "Graduate Research Opportunity",
        description="Project details to be determined.",
    )

    with patch.object(clf, "ml_refine_enabled", True), patch.object(
        clf,
        "_ml_classify_with_confidence",
        return_value=("Environmental Sciences", "", 0.25),
    ):
        primary, _secondary = clf.classify_position(pos)

    assert primary == "Environmental Sciences"


def test_ml_does_not_override_non_other_with_low_confidence() -> None:
    clf = DisciplineClassifier()
    pos = make_position(
        "PhD Assistantship in Fisheries Ecology",
        description="Includes broad climate and stakeholder language in project context.",
    )

    with patch.object(clf, "ml_refine_enabled", True), patch.object(
        clf,
        "_ml_classify_with_confidence",
        return_value=("Human Dimensions", "", 0.13),
    ):
        primary, _secondary = clf.classify_position(pos)

    assert primary == "Fisheries and Aquatic"


@pytest.mark.skipif(not HAS_SKLEARN, reason="Secondary ML requires scikit-learn")
def test_secondary_ml_relables_other_when_training_signal_is_clear() -> None:
    clf = DisciplineClassifier()
    clf.secondary_ml_min_train = 4
    clf.secondary_ml_min_similarity = 0.05
    clf.secondary_ml_min_margin = 0.0

    positions = [
        make_position("PhD Assistantship in Fisheries Ecology", description="fish stream habitat"),
        make_position("MS in Trout Population Dynamics", description="aquatic fish ecology"),
        make_position("Graduate Fisheries Research", description="river fish passage"),
        make_position("PhD in Watershed Biogeochemistry", description="soil hydrology chemistry"),
        make_position("MS Climate and Carbon Cycling", description="environmental sustainability"),
        make_position("Graduate Soil Microbiology Project", description="water quality"),
        make_position(
            "Graduate Research Opportunity",
            description="trout migration and fish passage in river systems",
        ),
    ]
    primary_labels = [
        "Fisheries and Aquatic",
        "Fisheries and Aquatic",
        "Fisheries and Aquatic",
        "Environmental Sciences",
        "Environmental Sciences",
        "Environmental Sciences",
        "Other",
    ]
    secondary_labels = ["", "", "", "", "", "", ""]

    refined_primary, _refined_secondary = clf.refine_other_labels_with_secondary_ml(
        positions, primary_labels, secondary_labels
    )

    assert refined_primary[-1] == "Fisheries and Aquatic"


@pytest.mark.skipif(not HAS_SKLEARN, reason="Secondary ML requires scikit-learn")
def test_secondary_ml_confidence_gate_keeps_other_when_similarity_too_low() -> None:
    clf = DisciplineClassifier()
    clf.secondary_ml_min_train = 4
    clf.secondary_ml_min_similarity = 0.95
    clf.secondary_ml_min_margin = 0.1

    positions = [
        make_position("PhD Assistantship in Fisheries Ecology", description="fish stream habitat"),
        make_position("MS in Trout Population Dynamics", description="aquatic fish ecology"),
        make_position("Graduate Fisheries Research", description="river fish passage"),
        make_position("PhD in Watershed Biogeochemistry", description="soil hydrology chemistry"),
        make_position("MS Climate and Carbon Cycling", description="environmental sustainability"),
        make_position("Graduate Soil Microbiology Project", description="water quality"),
        make_position(
            "Graduate Research Opportunity",
            description="trout migration and fish passage in river systems",
        ),
    ]
    primary_labels = [
        "Fisheries and Aquatic",
        "Fisheries and Aquatic",
        "Fisheries and Aquatic",
        "Environmental Sciences",
        "Environmental Sciences",
        "Environmental Sciences",
        "Other",
    ]
    secondary_labels = ["", "", "", "", "", "", ""]

    refined_primary, _refined_secondary = clf.refine_other_labels_with_secondary_ml(
        positions, primary_labels, secondary_labels
    )

    assert refined_primary[-1] == "Other"


def test_promoted_model_relables_other_when_confident() -> None:
    clf = DisciplineClassifier()
    clf.promoted_model_enabled = True
    clf.promoted_model_min_confidence = 0.6
    clf.promoted_model_min_margin = 0.05

    positions = [
        make_position("PhD Assistantship in Fisheries Ecology", description="fish stream habitat"),
        make_position("Graduate Research Opportunity", description="unresolved discipline"),
    ]
    primary_labels = ["Fisheries and Aquatic", "Other"]
    secondary_labels = ["", ""]

    with patch.object(
        clf,
        "predict_with_promoted_model",
        return_value={
            "available": True,
            "model_id": "m1",
            "primary": "Wildlife",
            "secondary": "Fisheries and Aquatic",
            "confidence": 0.86,
            "margin": 0.22,
        },
    ):
        refined_primary, refined_secondary = clf.refine_other_labels_with_promoted_model(
            positions, primary_labels, secondary_labels
        )

    assert refined_primary[0] == "Fisheries and Aquatic"
    assert refined_primary[1] == "Wildlife"
    assert refined_secondary[1] == "Fisheries and Aquatic"


def test_promoted_model_keeps_other_when_confidence_too_low() -> None:
    clf = DisciplineClassifier()
    clf.promoted_model_enabled = True
    clf.promoted_model_min_confidence = 0.7
    clf.promoted_model_min_margin = 0.1

    positions = [
        make_position("Graduate Research Opportunity", description="unresolved discipline"),
    ]
    primary_labels = ["Other"]
    secondary_labels = [""]

    with patch.object(
        clf,
        "predict_with_promoted_model",
        return_value={
            "available": True,
            "model_id": "m1",
            "primary": "Wildlife",
            "secondary": "",
            "confidence": 0.61,
            "margin": 0.04,
        },
    ):
        refined_primary, _refined_secondary = clf.refine_other_labels_with_promoted_model(
            positions, primary_labels, secondary_labels
        )

    assert refined_primary[0] == "Other"
