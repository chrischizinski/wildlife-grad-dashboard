"""Pruning exists to stop weekly model files piling up in git, but it must
never delete the one model the pipeline actually loads."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from retrain_discipline_model import prune_artifacts  # noqa: E402


def make_models(tmp_path, ids):
    models = tmp_path / "models"
    models.mkdir()
    for model_id in ids:
        (models / f"discipline_model_{model_id}.pkl").write_bytes(b"x")
        (models / f"discipline_model_{model_id}.json").write_text("{}")
    return models


def names(models):
    return sorted(p.name for p in models.glob("*.pkl"))


def test_promoted_model_survives_even_when_oldest(tmp_path):
    ids = ["20260101_000000", "20260201_000000", "20260301_000000",
           "20260401_000000", "20260501_000000"]
    models = make_models(tmp_path, ids)
    promoted = "data/models/discipline/models/discipline_model_20260101_000000.pkl"

    prune_artifacts(tmp_path, promoted, keep_recent=2)

    assert names(models) == [
        "discipline_model_20260101_000000.pkl",  # promoted
        "discipline_model_20260401_000000.pkl",  # 2 newest
        "discipline_model_20260501_000000.pkl",
    ]


def test_metadata_json_removed_with_its_pickle(tmp_path):
    models = make_models(tmp_path, ["20260101_000000", "20260201_000000"])

    prune_artifacts(tmp_path, None, keep_recent=1)

    assert not (models / "discipline_model_20260101_000000.json").exists()
    assert (models / "discipline_model_20260201_000000.json").exists()


def test_missing_models_dir_is_a_noop(tmp_path):
    assert prune_artifacts(tmp_path, None, keep_recent=3) == []


def test_nothing_removed_when_within_keep_limit(tmp_path):
    models = make_models(tmp_path, ["20260101_000000", "20260201_000000"])
    assert prune_artifacts(tmp_path, None, keep_recent=3) == []
    assert len(names(models)) == 2
