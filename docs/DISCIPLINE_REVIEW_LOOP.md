# Discipline Review Loop

This document explains the new continuous discipline-label improvement loop:

1. Generate analytics and confidence queue.
2. Review flagged rows in CSV.
3. Import review decisions into gold labels.
4. Retrain candidate model.
5. Promote only if validation improves.

All commands below assume you are in the repo root.

## Files In The Loop

- Confidence queue CSV: `data/processed/discipline_confidence_queue.csv`
- Confidence queue JSON: `data/processed/discipline_confidence_queue.json`
- Gold labels store: `data/processed/discipline_labels_gold.json`
- Model manifest: `data/models/discipline/manifest.json`
- Training report: `data/models/discipline/latest_training_report.json`

## Step 1: Generate Queue

```bash
python3 scripts/generate_dashboard_analytics.py
```

This refreshes dashboard data and writes the discipline confidence queue.

## Step 2: Review Queue CSV

Open:

`data/processed/discipline_confidence_queue.csv`

For each row, set:

- `review_status`: one of `accept_model`, `keep_final`, `override`, `skip`
- `reviewed_discipline`: required only when `review_status=override`
- `review_notes`: optional
- `reviewer`: optional

How to choose:

- `accept_model`: use model suggestion (`discipline_model_suggested`)
- `keep_final`: keep current pipeline label (`discipline_final`)
- `override`: use your manual value in `reviewed_discipline`
- `skip`: leave unresolved for now

Do not edit `position_key`; it is used for stable matching.

## Step 3: Import Reviews Into Gold Labels

```bash
python3 scripts/import_discipline_queue_reviews.py
```

Optional dry run:

```bash
python3 scripts/import_discipline_queue_reviews.py --dry-run
```

Result:

- Gold labels are created/updated in `data/processed/discipline_labels_gold.json`.

## Step 4: Retrain Candidate Model

```bash
python3 scripts/retrain_discipline_model.py --auto-seed-from-positions
```

Notes:

- `--auto-seed-from-positions` adds conservative high-confidence seeds.
- Retraining writes candidate artifacts to `data/models/discipline/models/`.
- Promotion is gated by validation metrics.

## Step 5: Check Promotion Outcome

Check:

- `data/models/discipline/latest_training_report.json`
- `data/models/discipline/manifest.json`

If promoted:

- `manifest.json` -> `promoted` points to the active model.
- Future analytics runs use the promoted model for additional refinement.

If not promoted:

- The current promoted model remains active.
- Continue reviewing queue rows and import more labels.

## Operational Cadence

- After each scrape/update run:
1. Regenerate analytics.
2. Review queue CSV.
3. Import reviews.
4. Retrain.
5. Confirm report/manifest.

## CI Automation

`/.github/workflows/scrape-and-update-dashboard.yml` now runs:

1. `scripts/generate_dashboard_analytics.py`
2. `scripts/retrain_discipline_model.py --auto-seed-from-positions`
3. `scripts/generate_dashboard_analytics.py` again (to apply any newly promoted model)

Manual review/import is still a human step.

## Troubleshooting

- "insufficient_gold_labels":
  - Add more reviewed rows via queue import.
  - Need enough labels and multiple classes for validation.

- Queue is too noisy:
  - Keep only high-severity items first.
  - Use `skip` on low-value rows.

- Model does not promote:
  - Check `latest_training_report.json` metrics vs prior promoted metrics.
  - Import more high-quality reviewed labels before retraining again.
