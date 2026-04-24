import scripts.generate_dashboard_analytics as analytics_generator


def test_dashboard_generator_excludes_professional_engineer_programmer_role(monkeypatch):
    monkeypatch.setattr(
        analytics_generator,
        "write_discipline_confidence_queue",
        lambda _queue: None,
    )
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


def test_dashboard_generator_excludes_postgraduate_fellowship_without_degree_program(
    monkeypatch,
):
    monkeypatch.setattr(
        analytics_generator,
        "write_discipline_confidence_queue",
        lambda _queue: None,
    )
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
