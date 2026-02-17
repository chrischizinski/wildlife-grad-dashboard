# Repository Guidelines

## Project Structure & Module Organization
- Source: `src/wildlife_grad/` with packages `scraper/`, `analysis/`, `database/`, `utils/`.
- Web UI: `web/` (HTML, JS, CSS) and data JSON in `web/data/`.
- Scripts: `scripts/` (e.g., `generate_dashboard_analytics.py`, `populate_supabase.py`).
- Data: `data/` (`raw/`, `processed/`, `archive/`) plus verification backups.
- Tests: `tests/` with `unit/` and `integration/` suites.
- Config/SQL: `config/sql/` migrations and helpers. Docs in `docs/`.

## Build, Test, and Development Commands
- Install (dev): `pip install -e .[dev]` — adds pytest, ruff, pre-commit.
- Lint/format: `ruff check .` and `ruff format .` — style and auto-fixes.
- Types: `mypy src/` — relaxed typing per `pyproject.toml`.
- Security: `bandit -r src/ -x data,tests` — scan for common issues.
- Tests: `pytest -q` or `pytest tests/integration -q` — run unit/integration.
- Serve dashboard: `cd web && python -m http.server 8080` — open `web/wildlife_dashboard.html`.
- Generate analytics: `python scripts/generate_dashboard_analytics.py`.
- Supabase ops: `python scripts/populate_supabase.py` (see `docs/SUPABASE_SETUP.md`).

## Coding Style & Naming Conventions
- Python: PEP 8 via Ruff, line length 88. Functions/vars `snake_case`; classes `PascalCase`.
- JS/CSS: ES6 modules; BEM CSS (`.block__elem--mod`).
- Imports: group/sort (Ruff isort rules). Avoid wildcard imports.
- Keep modules under `src/wildlife_grad/`; functions short and testable.

## Testing Guidelines
- Framework: pytest. Name tests `test_*.py` or `*_test.py` under `tests/`.
- Layout: unit tests in `tests/unit/`; integration in `tests/integration/`.
- Aim to cover new logic; prefer fixtures over hard-coded paths.
- Run locally with `pytest -q` before pushing.

## Commit & Pull Request Guidelines
- Commits: imperative, concise subjects (e.g., "Add comprehensive scraping flag").
- Automated updates: "Automated job data update <timestamp>".
- PRs: include summary, rationale, linked issue (e.g., `Closes #123`), test results, and UI screenshots when relevant.
- CI/pre-commit must pass. Run `pre-commit install` once, then commit normally.

## Security & Configuration Tips
- Use `.env` (see `.env.example`); never commit secrets.
- Avoid large regenerated data in VCS; prefer scripts to reproduce.
- Supabase: apply SQL from `config/sql/` and keep keys in environment.

## Architecture Overview
- Data flow: scraper → analysis → web. See `docs/architecture.md` and `README.md` for details.

## Dashboard Rebuild Contract (must follow)

### Goal
Reconfigure `web/wildlife_dashboard.html` + related JS so the dashboard is coherent and robust for US assistantship market trends:
- counts over time
- disciplines over time
- salary (nominal + COL-adjusted)
- geography/regions
- clear data quality indicators

### Non-negotiables (definition of done)
1) The dashboard must render without errors when served locally:
   - `cd web && python -m http.server 8080`
   - open `http://localhost:8080/wildlife_dashboard.html`

2) The dashboard must render when hosted on GitHub Pages under a repo subpath:
   - data fetches must use relative paths that work under `/wildlife-grad-dashboard/`
   - no absolute `/web/...` or `/data/...` paths

3) Every KPI card and chart must have an explicit empty state:
   - If filtered dataset is empty: show a banner "No data for current filters"
   - KPI cards: show "—" and a short reason (e.g., "No rows after filters")
   - Salary KPIs: computed only on salary-parsed subset, clearly labeled

4) Data quality must be visible:
   - % postings with salary parsed
   - % postings with location parsed
   - last updated timestamp (from analytics output if available)

### Work method
- Make changes in small commits:
  1) Fix data loading / broken paths so the current dashboard loads
  2) Restructure layout (Overview / Disciplines / Compensation / Geography / Data Quality)
  3) Add empty-state guards and thresholds (e.g., suppress medians with N < 5)

- After each commit, run:
  - `python scripts/generate_dashboard_analytics.py` (if needed)
  - `cd web && python -m http.server 8080`
  - visually verify all tabs/cards load and filters do not produce blank components

