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
