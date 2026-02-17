# Wildlife Graduate Assistantship Dashboard

A data pipeline and web dashboard for tracking U.S. wildlife and natural resources graduate assistantship postings.

The project combines:
- automated scraping from the TAMU wildlife jobs board,
- graduate-position classification and enrichment,
- analytics generation for trends, disciplines, salary, and geography,
- a static dashboard served from `web/` (including GitHub Pages deployment).

## What This Repository Does

1. Scrapes wildlife job postings and saves structured outputs.
2. Classifies likely graduate assistantships and disciplines.
3. Produces dashboard analytics JSON files.
4. Serves a browser dashboard from static assets.
5. Optionally supports Supabase upload workflows through environment-configured scripts.

## Repository Layout

```text
.
├── src/wildlife_grad/
│   ├── scraper/                     # Selenium scraper + job models
│   ├── analysis/                    # Classification + analytics helpers
│   └── utils/
├── scripts/                         # Pipeline and maintenance scripts
├── web/
│   ├── wildlife_dashboard.html      # Main dashboard entrypoint
│   ├── assets/js/                   # Frontend logic (dashboard-core, map-component)
│   ├── assets/css/                  # Dashboard styles
│   ├── data/                        # Dashboard-ready JSON
│   └── _archive/                    # Legacy dashboard assets/data
├── data/
│   ├── raw/                         # Raw scrape outputs
│   ├── processed/                   # Processed/classified outputs
│   ├── archive/                     # Timestamped backups
│   └── failed_uploads/              # Retry artifacts for failed uploads
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
└── .github/workflows/               # Scrape/update + Pages deployment
```

## Quick Start

### 1) Install dependencies

```bash
pip install -e .[dev]
```

If you only want runtime dependencies:

```bash
pip install -e .
```

### 2) Run a scrape

```bash
python -m src.wildlife_grad.scraper.wildlife_job_scraper
```

Optional: force a comprehensive scrape:

```bash
python -m src.wildlife_grad.scraper.wildlife_job_scraper --comprehensive
```

### 3) Generate dashboard analytics

```bash
python scripts/generate_dashboard_analytics.py
```

This updates analytics outputs (including `web/data/dashboard_analytics.json`).

### 4) Serve the dashboard locally

```bash
cd web
python -m http.server 8080
```

Open: `http://localhost:8080/wildlife_dashboard.html`

## Core Commands (Development)

```bash
# Lint and format
ruff check .
ruff format .

# Type checks
mypy src/

# Security scan
bandit -r src/ -x data,tests

# Tests
pytest -q
pytest tests/integration -q

# Pre-commit hooks
pre-commit run -a
```

## Data Outputs You Will Use Most

- `data/processed/verified_graduate_assistantships.json`: main filtered graduate positions
- `data/processed/classification_report.json`: classifier summary/diagnostics
- `web/data/dashboard_analytics.json`: dashboard KPIs/time-series aggregates
- `web/data/`: static files consumed by `web/wildlife_dashboard.html`

## Dashboard Notes

- Main dashboard file: `web/wildlife_dashboard.html`
- Frontend modules:
  - `web/assets/js/dashboard-core.js`
  - `web/assets/js/map-component.js`
- Styling:
  - `web/assets/css/enhanced-styles.css`

For GitHub Pages compatibility, data paths in frontend code should remain relative (no absolute `/web/...` or `/data/...` URLs).

## Automation (GitHub Actions)

- `scrape-and-update-dashboard.yml`
  - scheduled + manual + selected push triggers
  - runs scrape + analytics updates
  - copies generated data into `web/data/`
- `deploy-pages.yml`
  - builds from `web/`
  - deploys dashboard to GitHub Pages

## Environment Variables

Create a `.env` file (see `.env.example`) when using Supabase-connected scripts.

Common variables:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`

Do not commit secrets.

## Additional Docs

- `docs/architecture.md`
- `docs/GITHUB_SETUP.md`
- `AGENTS.md` (project-specific contributor/agent workflow rules)

## License

No license file is currently present in this repository. Add one before external distribution.
