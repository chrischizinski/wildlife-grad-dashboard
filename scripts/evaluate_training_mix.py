#!/usr/bin/env python3
"""
Does each kind of training label help the model predict HUMAN labels?

Compares training mixes by repeated stratified cross-validation over the
human-labeled rows only: each human row is predicted by a model that never saw
it. Mixes vary the weight of machine-seeded gold labels and of pseudo-labeled
postings (both come from the rules' own output).

Run: python scripts/evaluate_training_mix.py [--seeds 20]
Note: the spread across seeds reflects CV randomness only. With ~100 human
rows the sampling error of accuracy itself is about +/- 4.6 points, so read
differences between mixes as paired comparisons on the same rows.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold

sys.path.insert(0, str(Path(__file__).resolve().parent))
import retrain_discipline_model as R  # noqa: E402

warnings.filterwarnings("ignore")

MIXES = {
    "A current (machine 1.0, pseudo 0.35)": (1.0, 0.35),
    "B no pseudo (machine 1.0)": (1.0, 0.0),
    "C machine 0.35, no pseudo": (0.35, 0.0),
    "D human labels only": (0.0, 0.0),
    "E machine 1.0, pseudo 1.0": (1.0, 1.0),
}


def load(gold_path: Path, positions_path: Path):
    payload = json.loads(gold_path.read_text(encoding="utf-8"))
    positions = json.loads(positions_path.read_text(encoding="utf-8"))
    positions = positions["positions"] if isinstance(positions, dict) else positions
    texts, labels, keys = R.build_gold_examples(payload)
    texts, labels, keys, _ = R.filter_rare_gold_classes(texts, labels, keys, min_count=2)
    human_keys = R.human_gold_keys(payload)
    human = [i for i, k in enumerate(keys) if k in human_keys]
    machine = [i for i in range(len(keys)) if i not in set(human)]
    pseudo_texts, pseudo_labels = R.build_pseudo_examples(positions, keys, 300)
    return texts, labels, human, machine, pseudo_texts, pseudo_labels


def cv_once(data, seed: int, w_machine: float, w_pseudo: float):
    texts, labels, human, machine, pseudo_texts, pseudo_labels = data
    human_labels = np.array([labels[i] for i in human])
    folds = min(5, min(np.bincount(np.unique(human_labels, return_inverse=True)[1])))
    y_true, y_pred = [], []
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    for train_pos, test_pos in splitter.split(np.arange(len(human)), human_labels):
        train_h = [human[j] for j in train_pos]
        test_h = [human[j] for j in test_pos]
        use_machine = machine if w_machine > 0 else []
        use_pseudo = w_pseudo > 0
        train_texts = [texts[i] for i in use_machine + train_h]
        train_labels = [labels[i] for i in use_machine + train_h]
        weights = [w_machine] * len(use_machine) + [1.0] * len(train_h)
        if use_pseudo:
            train_texts += list(pseudo_texts)
            train_labels += list(pseudo_labels)
            weights += [w_pseudo] * len(pseudo_texts)
        vectorizer, model = R.fit_model(train_texts, train_labels, weights)
        y_pred += list(model.predict(vectorizer.transform([texts[i] for i in test_h])))
        y_true += [labels[i] for i in test_h]
    return (
        accuracy_score(y_true, y_pred),
        f1_score(y_true, y_pred, average="macro", zero_division=0),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--gold-file", type=Path,
                        default=Path("data/processed/discipline_labels_gold.json"))
    parser.add_argument("--positions-file", type=Path,
                        default=Path("web/data/dashboard_positions.json"))
    args = parser.parse_args()

    data = load(args.gold_file, args.positions_file)
    print(f"human {len(data[2])} | machine gold {len(data[3])} | pseudo {len(data[4])}")
    results = {}
    for name, (w_machine, w_pseudo) in MIXES.items():
        scores = np.array([cv_once(data, s, w_machine, w_pseudo) for s in range(args.seeds)])
        results[name] = scores
        print(f"{name:40} acc {scores[:, 0].mean():.3f} (sd {scores[:, 0].std(ddof=1):.3f}) | "
              f"macro-F1 {scores[:, 1].mean():.3f} (sd {scores[:, 1].std(ddof=1):.3f})")
    base = results["A current (machine 1.0, pseudo 0.35)"][:, 0]
    print("paired accuracy difference vs A (same seeds and rows):")
    for name, scores in results.items():
        if name.startswith("A"):
            continue
        diff = scores[:, 0] - base
        print(f"  {name[:1]}: {diff.mean():+.3f}  (better in {int((diff > 0).sum())}/{args.seeds} seeds)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
