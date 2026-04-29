import scripts.generate_dashboard_analytics as analytics_generator


def _disable_queue_write(monkeypatch):
    monkeypatch.setattr(
        analytics_generator,
        "write_discipline_confidence_queue",
        lambda _queue: None,
    )


def test_dashboard_generator_excludes_professional_engineer_programmer_role(monkeypatch):
    _disable_queue_write(monkeypatch)
    rows = [
        {
            "title": "Database Engineer/OPS Scientific/Engineering Programmer",
            "organization": "Florida Fish and Wildlife Conservation Commission (State)",
            "location": "100 8th Ave SE, St. Petersburg, FL 33701, USA (St. Petersburg, Florida)",
            "salary": "$25 per hour",
            "published_date": "03/20/2026",
            "tags": "N/A",
            "description": (
                "This position is for a database engineer with the Marine Mammal "
                "Section to support Florida marine mammal population research and "
                "monitoring."
            ),
            "is_graduate_position": True,
        },
        {
            "title": "M.S. Graduate Research Assistantship in Wildlife Ecology",
            "organization": "Example University",
            "location": "Lincoln, Nebraska",
            "salary": "$24,000 per year",
            "published_date": "03/20/2026",
            "tags": "Graduate Opportunities",
            "description": (
                "Student will enroll in an M.S. graduate program and receive a "
                "research assistantship with tuition waiver."
            ),
            "is_graduate_position": True,
        },
    ]

    sanitized = analytics_generator.sanitize_and_classify_positions(rows)

    assert [row["title"] for row in sanitized] == [
        "M.S. Graduate Research Assistantship in Wildlife Ecology"
    ]


def test_dashboard_generator_excludes_known_non_grad_leakage_rows(monkeypatch):
    _disable_queue_write(monkeypatch)
    rows = [
        {
            "title": "Naturalist Boat Captain",
            "organization": "Tideline Tours (Private)",
            "location": "Sunset Cay Marina (Folly Beach, South Carolina)",
            "salary": "starting at $23 per hour",
            "published_date": "02/19/2026",
            "tags": "N/A",
            "description": (
                "We are seeking part-time boat captains to lead eco-tours for the "
                "2026 season. Education Required: none."
            ),
            "is_graduate_position": True,
        },
        {
            "title": (
                "Aquaculture Experiential Opportunities for Undergraduate Students "
                "(AquEOUS) Fellowship"
            ),
            "organization": "University of Maine Aquaculture Research Institute",
            "location": "bristol, Maine",
            "salary": "starting at $15 per hour",
            "published_date": "02/06/2026",
            "tags": "Undergraduate Opportunities",
            "description": (
                "Applications are open for undergraduate students to gain summer "
                "aquaculture research experience."
            ),
            "is_graduate_position": True,
        },
        {
            "title": "2026 Summer Law Clerk",
            "organization": "Earthjustice (Private)",
            "location": "multiple | remote work allowed",
            "salary": "$1,320 per week",
            "published_date": "07/07/2025",
            "tags": "Graduate Opportunities",
            "description": "Summer law clerk role. Education Required: Masters.",
            "is_graduate_position": True,
        },
        {
            "title": "Research Associate Position in Soil Science and Microbiology",
            "organization": "Example Lab",
            "location": "Lincoln, Nebraska",
            "salary": "$40,000 to $50,000 per year",
            "published_date": "03/20/2026",
            "tags": "N/A",
            "description": "Professional research associate position.",
            "is_graduate_position": True,
        },
        {
            "title": "Board of Directors",
            "organization": "Wildlife Nonprofit",
            "location": "Remote",
            "salary": "",
            "published_date": "03/20/2026",
            "tags": "Graduate Opportunities",
            "description": "Volunteer board of directors service opportunity.",
            "is_graduate_position": True,
        },
        {
            "title": "M.S. Graduate Research Assistantship in Wildlife Ecology",
            "organization": "Example University",
            "location": "Lincoln, Nebraska",
            "salary": "$24,000 per year",
            "published_date": "03/20/2026",
            "tags": "Graduate Opportunities",
            "description": (
                "Student will enroll in an M.S. graduate program and receive a "
                "research assistantship with tuition waiver."
            ),
            "is_graduate_position": True,
        },
    ]

    sanitized = analytics_generator.sanitize_and_classify_positions(rows)

    assert [row["title"] for row in sanitized] == [
        "M.S. Graduate Research Assistantship in Wildlife Ecology"
    ]


def test_dashboard_generator_excludes_postgraduate_fellowship_without_degree_program(
    monkeypatch,
):
    _disable_queue_write(monkeypatch)
    rows = [
        {
            "title": "USDA-ARS Post Graduate Research Fellow in Agrigenomics",
            "organization": "Oak Ridge Associated Universities (ORAU)",
            "location": "Hilo, Hawaii",
            "salary": "Commensurate / Negotiable",
            "published_date": "03/20/2026",
            "tags": "Graduate Opportunities, Undergraduate Opportunities",
            "description": (
                "This project is for a research fellow at the post-grad or post-bac "
                "level that is interested in expanding research experience."
            ),
            "is_graduate_position": True,
        }
    ]

    assert analytics_generator.sanitize_and_classify_positions(rows) == []


def test_calculate_analytics_exposes_nominal_and_col_adjusted_salary_stats(
    monkeypatch,
):
    monkeypatch.setattr(
        analytics_generator,
        "calculate_snapshot_availability",
        lambda: {},
    )
    rows = [
        {
            "title": "MS Assistantship A",
            "discipline": "Wildlife",
            "salary": "$20,000 per year",
            "salary_lincoln_adjusted": 18000,
            "published_date": "2026-01-01",
        },
        {
            "title": "MS Assistantship B",
            "discipline": "Wildlife",
            "salary": "$30,000 per year",
            "salary_lincoln_adjusted": 25000,
            "published_date": "2026-02-01",
        },
    ]

    analytics = analytics_generator.calculate_analytics(rows)
    stats = analytics["top_disciplines"]["Wildlife"]

    assert stats["salary_stats"]["median"] == 25000
    assert stats["salary_stats_nominal"]["median"] == 25000
    assert stats["salary_stats_col_adjusted"]["median"] == 21500
    assert analytics["summary_stats"]["positions_with_col_adjusted"] == 2


def test_discipline_confidence_queue_orders_higher_confidence_first():
    class FakeClassifier:
        def predict_with_promoted_model(self, position):
            confidence = 0.9 if "High" in position.title else 0.7
            return {
                "available": True,
                "primary": "Wildlife",
                "secondary": "",
                "confidence": confidence,
                "margin": 0.2,
                "model_id": "fake",
            }

    rows = [
        {"title": "Low confidence Other", "discipline": "Other"},
        {"title": "High confidence Other", "discipline": "Other"},
    ]

    queue = analytics_generator.build_discipline_confidence_queue(
        rows,
        FakeClassifier(),
    )

    assert [row["title"] for row in queue] == [
        "High confidence Other",
        "Low confidence Other",
    ]
