"""Regression tests for graduate-position false positives."""

from pathlib import Path
import sys

# Ensure src/ is importable when running tests from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from wildlife_grad.analysis.enhanced_analysis import GraduatePositionDetector, JobPosition


def make_position(title: str, tags: str = "Graduate Opportunities", description: str = "") -> JobPosition:
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


def test_veterinarian_is_not_graduate_even_with_grad_tag() -> None:
    detector = GraduatePositionDetector()
    pos = make_position("Associate Veterinarian", tags="Graduate Opportunities")

    is_grad, position_type, confidence = detector.is_graduate_position(pos)

    assert not is_grad
    assert position_type == "Professional/Other"
    assert confidence <= 0.3


def test_fish_passage_biologist_i_is_not_graduate() -> None:
    detector = GraduatePositionDetector()
    pos = make_position("Fish Passage Biologist I", tags="Graduate Opportunities")

    is_grad, position_type, confidence = detector.is_graduate_position(pos)

    assert not is_grad
    assert position_type == "Professional/Other"
    assert confidence <= 0.3


def test_environmental_specialist_is_not_graduate() -> None:
    detector = GraduatePositionDetector()
    pos = make_position(
        "Environmental Specialist (Rapid Responder)",
        tags="Graduate Opportunities",
    )

    is_grad, position_type, confidence = detector.is_graduate_position(pos)

    assert not is_grad
    assert position_type == "Professional/Other"
    assert confidence <= 0.3


def test_archaeologist_is_not_graduate() -> None:
    detector = GraduatePositionDetector()
    pos = make_position(
        "Archaeologist",
        tags="Graduate Opportunities",
        description="Field excavation and compliance role.",
    )

    is_grad, position_type, confidence = detector.is_graduate_position(pos)

    assert not is_grad
    assert position_type == "Professional/Other"
    assert confidence <= 0.3


def test_field_assistant_not_graduate_by_default() -> None:
    detector = GraduatePositionDetector()
    pos = make_position(
        "Field Assistant working with wild parrots and macaws in Tambopata PERU",
        tags="Undergraduate Opportunities",
    )

    is_grad, position_type, confidence = detector.is_graduate_position(pos)

    assert not is_grad
    assert position_type == "Professional/Other"
    assert confidence <= 0.3


def test_postdoc_is_not_graduate_position() -> None:
    detector = GraduatePositionDetector()
    pos = make_position(
        "Postdoctoral Research Associate in Wildlife Disease Ecology",
        tags="Graduate Opportunities",
        description="Postdoc position with independent research program.",
    )

    is_grad, position_type, confidence = detector.is_graduate_position(pos)

    assert not is_grad
    assert position_type == "Professional/Other"
    assert confidence <= 0.3


def test_postdoc_with_funding_language_still_not_graduate() -> None:
    detector = GraduatePositionDetector()
    pos = make_position(
        "USDA-ARS Postdoctoral Fellowship in Microbial Genomics",
        tags="Graduate Opportunities",
        description="Fully funded role with stipend and health insurance for PhD scientists.",
    )

    is_grad, position_type, confidence = detector.is_graduate_position(pos)

    assert not is_grad
    assert position_type == "Professional/Other"
    assert confidence <= 0.3


def test_student_contractor_is_not_graduate_by_default() -> None:
    detector = GraduatePositionDetector()
    pos = make_position(
        "Student Contractor - Habitat Monitoring",
        tags="Graduate Opportunities",
        description="Temporary contractor role for field support.",
    )

    is_grad, position_type, confidence = detector.is_graduate_position(pos)

    assert not is_grad
    assert position_type == "Professional/Other"
    assert confidence <= 0.3


def test_explicit_graduate_assistantship_still_passes() -> None:
    detector = GraduatePositionDetector()
    pos = make_position(
        "PhD Graduate Research Assistantship in Fisheries Ecology",
        tags="Graduate Opportunities",
        description="Funded graduate research assistantship with tuition waiver and stipend.",
    )

    is_grad, position_type, confidence = detector.is_graduate_position(pos)

    assert is_grad
    assert confidence >= 0.7 or "Graduate" in position_type or "PhD" in position_type


def test_fellowship_coordinator_not_grad() -> None:
    detector = GraduatePositionDetector()
    pos = make_position(
        "Environmental Education Fellowship Coordinator",
        tags="Graduate Opportunities",
        description="Coordinate fellows, scheduling, and outreach logistics.",
    )

    is_grad, position_type, confidence = detector.is_graduate_position(pos)

    assert not is_grad
    assert position_type == "Professional/Other"
    assert confidence <= 0.3


def test_research_assistant_associate_not_grad_without_assistantship_language() -> None:
    detector = GraduatePositionDetector()
    pos = make_position(
        "Research Assistant/Associate",
        tags="Graduate Opportunities",
        description="General research support role.",
    )

    is_grad, position_type, confidence = detector.is_graduate_position(pos)

    assert not is_grad
    assert position_type == "Professional/Other"
    assert confidence <= 0.3


def test_noaa_summer_fellowship_not_grad_without_assistantship_language() -> None:
    detector = GraduatePositionDetector()
    pos = make_position(
        "NOAA Surveillance for the Presence of Algal Toxins in Food Webs Summer Fellowship",
        tags="Graduate Opportunities",
        description="Summer fellowship laboratory and field support.",
    )

    is_grad, position_type, confidence = detector.is_graduate_position(pos)

    assert not is_grad
    assert position_type == "Professional/Other"
    assert confidence <= 0.3


def test_graduate_research_assistant_title_is_grad() -> None:
    detector = GraduatePositionDetector()
    pos = make_position(
        "Graduate Research Assistant--Bat Ecology and Conservation",
        tags="Graduate Opportunities",
        description="Graduate research assistant role with thesis research.",
    )

    is_grad, position_type, confidence = detector.is_graduate_position(pos)

    assert is_grad
    assert confidence >= 0.2 or "Graduate" in position_type


def test_work_study_positions_are_not_grad() -> None:
    detector = GraduatePositionDetector()
    pos = make_position(
        "Graduate Student Work Study Positions",
        tags="Graduate Opportunities",
        description="Work-study support positions for enrolled students.",
    )

    is_grad, position_type, confidence = detector.is_graduate_position(pos)

    assert not is_grad
    assert position_type == "Professional/Other"
    assert confidence <= 0.3


def test_continuing_education_masters_listing_is_not_grad() -> None:
    detector = GraduatePositionDetector()
    pos = make_position(
        "Continuing Education - Master's degrees for Natural Resources Professionals",
        tags="Graduate Opportunities",
        description="Professional continuing education degree pathways.",
    )

    is_grad, position_type, confidence = detector.is_graduate_position(pos)

    assert not is_grad
    assert position_type == "Professional/Other"
    assert confidence <= 0.3


def test_conduct_your_own_research_project_listing_is_not_grad() -> None:
    detector = GraduatePositionDetector()
    pos = make_position(
        "Conduct Your Own Research Project in the Field - South Africa",
        tags="Graduate Opportunities, Undergraduate Opportunities",
        description="Independent project experience listing.",
    )

    is_grad, position_type, confidence = detector.is_graduate_position(pos)

    assert not is_grad
    assert position_type == "Professional/Other"
    assert confidence <= 0.3


def test_ambiguous_title_uses_description_to_detect_graduate_position() -> None:
    detector = GraduatePositionDetector()
    pos = make_position(
        "Scholarship Opportunity",
        tags="Graduate Opportunities",
        description=(
            "Funded PhD graduate research assistantship with tuition waiver, "
            "stipend, and dissertation research support."
        ),
    )

    is_grad, position_type, confidence = detector.is_graduate_position(pos)

    assert is_grad
    assert confidence >= 0.7
    assert position_type in {"Graduate Assistantship", "PhD Position", "Graduate Position"}


def test_title_hard_exclusion_blocks_grad_even_if_description_mentions_grad_terms() -> None:
    detector = GraduatePositionDetector()
    pos = make_position(
        "Environmental Field Technician",
        tags="Graduate Opportunities",
        description="Includes tuition waiver and stipend language in generic posting text.",
    )

    is_grad, position_type, confidence = detector.is_graduate_position(pos)

    assert not is_grad
    assert position_type == "Professional/Other"
    assert confidence <= 0.3
