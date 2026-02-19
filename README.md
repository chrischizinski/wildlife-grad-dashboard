# Wildlife Graduate Assistantship Dashboard

[![Scrape and Update](https://github.com/chrischizinski/wildlife-grad-dashboard/actions/workflows/scrape-and-update-dashboard.yml/badge.svg)](https://github.com/chrischizinski/wildlife-grad-dashboard/actions/workflows/scrape-and-update-dashboard.yml) [![Deploy Pages](https://github.com/chrischizinski/wildlife-grad-dashboard/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/chrischizinski/wildlife-grad-dashboard/actions/workflows/deploy-pages.yml) [![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live-brightgreen?logo=github)](https://chrischizinski.github.io/wildlife-grad-dashboard/) [![Last Commit](https://img.shields.io/github/last-commit/chrischizinski/wildlife-grad-dashboard)](https://github.com/chrischizinski/wildlife-grad-dashboard/commits/main) [![Issues](https://img.shields.io/github/issues/chrischizinski/wildlife-grad-dashboard)](https://github.com/chrischizinski/wildlife-grad-dashboard/issues) [![Pull Requests](https://img.shields.io/github/issues-pr/chrischizinski/wildlife-grad-dashboard)](https://github.com/chrischizinski/wildlife-grad-dashboard/pulls)

Live dashboard: [https://chrischizinski.github.io/wildlife-grad-dashboard/](https://chrischizinski.github.io/wildlife-grad-dashboard/)

## Project Summary
This project tracks U.S. wildlife and natural resources graduate assistantship postings and turns raw listings into a public-facing trends dashboard.

The system is designed to answer practical questions for students and advisors:
- How many assistantships are being posted over time?
- Which disciplines are most active?
- What salary ranges are being reported?
- Where are opportunities concentrated geographically?
- How complete/clean is the underlying data?

## What The Project Includes
- A scraper (`src/wildlife_grad/scraper/`) for TAMU wildlife job board listings.
- Analysis/classification modules (`src/wildlife_grad/analysis/`) for graduate relevance and discipline tagging.
- Data pipeline scripts (`scripts/`) to refresh and transform outputs.
- A static web dashboard (`web/wildlife_dashboard.html`) with JS/CSS assets and JSON-driven charts.
- GitHub Actions workflows for scheduled data refresh and GitHub Pages deploy.

## Current Status (as of February 17, 2026)
This status is based on the latest local analytics artifacts in this repository.

- Analytics last generated: `2026-02-15 05:19:25` (`web/data/dashboard_analytics.json`)
- Dataset represented in analytics: `229` positions
- Postings with salary parsed: `138`
- Current graduate-assistantship file size: `22` records (`data/processed/verified_graduate_assistantships.json`)
- Automation workflows present:
  - `.github/workflows/scrape-and-update-dashboard.yml`
  - `.github/workflows/deploy-pages.yml`

## Project Maturity
- Core scraping and dashboard pipeline exists and is operational.
- Data products are versioned into `data/`, `dashboard/data/`, and `web/data/`.
- CI/CD automation is present for refresh + deploy.
- Dashboard redesign/rebuild work is currently in progress (see `AGENTS.md` dashboard contract).

## Active Focus Areas
- Improve dashboard coherence across overview, discipline, compensation, geography, and data quality sections.
- Harden empty-state handling for all KPI cards and charts.
- Keep GitHub Pages path behavior robust (relative data fetches).
- Continue improving salary/location parse coverage and transparency.

## Repository Map
```text
src/wildlife_grad/        Python package (scraper + analysis)
scripts/                  Data pipeline and maintenance scripts
web/                      Dashboard frontend (HTML/CSS/JS + web/data)
data/                     Raw, processed, archived, and fallback artifacts
dashboard/data/           Analytics outputs used by dashboard build flow
docs/                     Supplemental architecture/setup notes
```

## Running The Dashboard Locally
```bash
cd web
python -m http.server 8080
# then open http://localhost:8080/wildlife_dashboard.html
```

## Continual Discipline Model Refinement
The discipline classifier now supports a versioned promoted model plus an
uncertainty review queue.
Detailed step-by-step guide: `docs/DISCIPLINE_REVIEW_LOOP.md`.

```bash
# 1) Rebuild analytics + refresh confidence queue
python scripts/generate_dashboard_analytics.py

# 2) Retrain candidate model and promote only if validation improves
python scripts/retrain_discipline_model.py

# 3) Seed conservative starter gold labels from stored assistantships, then retrain
python scripts/retrain_discipline_model.py --auto-seed-from-positions

# 4) After editing discipline_confidence_queue.csv with review decisions,
#    import them into the gold label store
python scripts/import_discipline_queue_reviews.py
```

Artifacts:
- Gold labels: `data/processed/discipline_labels_gold.json`
- Model manifest: `data/models/discipline/manifest.json`
- Training report: `data/models/discipline/latest_training_report.json`
- Confidence queue: `data/processed/discipline_confidence_queue.json`

Review CSV conventions (`data/processed/discipline_confidence_queue.csv`):
- Add `review_status` with one of: `accept_model`, `keep_final`, `override`, `skip`
- For `override`, also set `reviewed_discipline`
- Optional: `review_notes`, `reviewer`

## Notes
- This README is intentionally project/status oriented.
- Operational command details are maintained in repo docs and script help output.
