#!/usr/bin/env python3
"""
Train and promote a persistent discipline model with validation gating.

This script supports continual refinement by combining:
- Human-verified gold labels (required for validation/promotions)
- Optional pseudo-labeled assistantships from stored postings

It promotes a new model only when validation metrics improve.
It also writes an uncertainty queue for manual review.
"""

from __future__ import annotations

import argparse
import csv
import json
import pickle
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.model_selection import StratifiedKFold, train_test_split

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

DISCIPLINE_MAPPING = {
    "Environmental Science": "Environmental Sciences",
    "Environmental Sciences": "Environmental Sciences",
    "Ecology": "Environmental Sciences",
    "Fisheries": "Fisheries and Aquatic",
    "Fisheries and Aquatic": "Fisheries and Aquatic",
    "Fisheries & Aquatic Science": "Fisheries and Aquatic",
    "Fisheries Management and Conservation": "Fisheries and Aquatic",
    "Marine Science": "Fisheries and Aquatic",
    "Wildlife": "Wildlife",
    "Wildlife Management and Conservation": "Wildlife",
    "Wildlife Management": "Wildlife",
    "Wildlife & Natural Resources": "Wildlife",
    "Conservation": "Wildlife",
    "Entomology": "Entomology",
    "Forestry": "Forestry and Habitat",
    "Forestry and Habitat": "Forestry and Habitat",
    "Natural Resource Management": "Forestry and Habitat",
    "Agriculture": "Agriculture",
    "Agricultural Science": "Agriculture",
    "Animal Science": "Agriculture",
    "Agronomy": "Agriculture",
    "Range Management": "Agriculture",
    "Human Dimensions": "Human Dimensions",
    "Other": "Other",
    "Unknown": "Other",
    "Non-Graduate": "Other",
}

CANONICAL_DISCIPLINES = [
    "Environmental Sciences",
    "Fisheries and Aquatic",
    "Wildlife",
    "Entomology",
    "Forestry and Habitat",
    "Agriculture",
    "Human Dimensions",
    "Other",
]
DISCIPLINE_SIGNAL_PATTERNS: Dict[str, List[str]] = {
    "Environmental Sciences": [
        r"\bsoil\b",
        r"\bhydrolog(y|ical)\b",
        r"\bbiogeochem",
        r"\bwater\s+(quality|chemistry|security)\b",
        r"\benvironmental\s+microbiology\b",
        r"\bclimate\b",
    ],
    "Fisheries and Aquatic": [
        r"\bfisher(y|ies)\b",
        r"\baquatic\b",
        r"\bmarine\b",
        r"\bstream\b",
        r"\btrout\b",
        r"\bmanta\b",
        r"\bbycatch\b",
    ],
    "Wildlife": [
        r"\bwildlife\b",
        r"\bavian\b",
        r"\bbat\b",
        r"\bduck\b",
        r"\bmallard\b",
        r"\bturtle\b",
        r"\bherpetolog",
        r"\bmovement\s+ecology\b",
    ],
    "Forestry and Habitat": [
        r"\bforestr(y|y)\b",
        r"\bforest\b",
        r"\bsilviculture\b",
        r"\bhabitat\b",
        r"\brestoration\b",
    ],
    "Entomology": [
        r"\bentomolog",
        r"\binsect(s)?\b",
        r"\barthropod(s)?\b",
        r"\bant(s)?\b",
        r"\bpollinator(s)?\b",
    ],
    "Agriculture": [
        r"\bagricultur",
        r"\blivestock\b",
        r"\bcattle\b",
        r"\branch(ing)?\b",
        r"\bpasture\b",
        r"\bgrazing\b",
    ],
    "Human Dimensions": [
        r"\bhuman\s+dimensions\b",
        r"\bstakeholder\b",
        r"\bsocial\s+science\b",
        r"\bsurvey\b",
        r"\binterview\b",
        r"\bscience\s+communication\b",
        r"\benvironmental\s+education\b",
    ],
}


def now_iso() -> str:
    return datetime.now().isoformat()


def normalize_discipline(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "Other"
    return DISCIPLINE_MAPPING.get(text, "Other")


def position_key(row: Dict[str, Any]) -> str:
    """Stable key for matching labels/positions across files."""
    url = str(row.get("url") or "").strip().lower()
    if url:
        return f"url::{url}"
    title = str(row.get("title") or "").strip().lower()
    org = str(row.get("organization") or "").strip().lower()
    loc = str(row.get("location") or "").strip().lower()
    pub = str(row.get("published_date") or "").strip().lower()
    if title and org:
        return f"title_org::{title}::{org}::{loc}::{pub}"
    return f"title::{title}::{pub}" if title else ""


def combined_text(row: Dict[str, Any]) -> str:
    parts = [
        str(row.get("title") or ""),
        str(row.get("tags") or ""),
        str(row.get("organization") or ""),
        str(row.get("description") or ""),
    ]
    return " ".join(parts).strip().lower()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Retrain/publish discipline model with validation gating."
    )
    parser.add_argument(
        "--gold-file",
        type=Path,
        default=Path("data/processed/discipline_labels_gold.json"),
    )
    parser.add_argument(
        "--positions-file",
        type=Path,
        default=Path("web/data/dashboard_positions.json"),
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("data/models/discipline"),
    )
    parser.add_argument(
        "--min-macro-f1-improvement",
        type=float,
        default=0.005,
    )
    parser.add_argument(
        "--min-accuracy-improvement",
        type=float,
        default=0.0,
    )
    parser.add_argument(
        "--pseudo-weight",
        type=float,
        default=0.35,
    )
    parser.add_argument(
        "--max-pseudo-per-class",
        type=int,
        default=300,
    )
    parser.add_argument(
        "--no-pseudo",
        action="store_true",
        help="Disable pseudo-labeled augmentation from stored postings.",
    )
    parser.add_argument(
        "--no-bootstrap",
        action="store_true",
        help="Disable bootstrap from data/ml_training_data.json when gold is empty.",
    )
    parser.add_argument(
        "--force-promote",
        action="store_true",
        help="Promote candidate regardless of metric deltas.",
    )
    parser.add_argument(
        "--auto-seed-from-positions",
        action="store_true",
        help=(
            "Seed gold labels from high-confidence/high-signal stored assistantships "
            "(conservative rules)."
        ),
    )
    parser.add_argument(
        "--auto-seed-max-per-class",
        type=int,
        default=3,
    )
    parser.add_argument(
        "--auto-seed-min-grad-confidence",
        type=float,
        default=0.85,
    )
    return parser.parse_args()


def ensure_gold_dataset(path: Path) -> Dict[str, Any]:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict) and isinstance(payload.get("labels"), list):
            return payload

    payload = {
        "version": 1,
        "updated_at": now_iso(),
        "labels": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return payload


def bootstrap_gold_from_training_data(payload: Dict[str, Any], gold_path: Path) -> int:
    """Seed gold labels from existing human-verified training data, if present."""
    training_path = Path("data/ml_training_data.json")
    if not training_path.exists():
        return 0

    with open(training_path, "r", encoding="utf-8") as f:
        training_data = json.load(f)
    positions = training_data.get("positions") if isinstance(training_data, dict) else []
    if not isinstance(positions, list):
        return 0

    existing_keys = {str(item.get("position_key") or "") for item in payload["labels"]}
    added = 0
    for row in positions:
        if not isinstance(row, dict):
            continue
        if not row.get("human_verified"):
            continue
        discipline = normalize_discipline(
            row.get("discipline")
            or row.get("discipline_primary")
            or row.get("discipline_secondary")
            or "Other"
        )
        key = position_key(row)
        if not key or key in existing_keys:
            continue

        payload["labels"].append(
            {
                "position_key": key,
                "title": str(row.get("title") or ""),
                "organization": str(row.get("organization") or ""),
                "url": str(row.get("url") or ""),
                "description": str(row.get("description") or ""),
                "discipline": discipline,
                "source": "bootstrap_ml_training_data",
                "reviewed_at": now_iso(),
            }
        )
        existing_keys.add(key)
        added += 1

    if added:
        payload["updated_at"] = now_iso()
        with open(gold_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    return added


def build_gold_examples(payload: Dict[str, Any]) -> Tuple[List[str], List[str], List[str]]:
    texts: List[str] = []
    labels: List[str] = []
    keys: List[str] = []

    for item in payload.get("labels", []):
        if not isinstance(item, dict):
            continue
        discipline = normalize_discipline(item.get("discipline"))
        text = combined_text(item)
        key = str(item.get("position_key") or "").strip()
        if not text or not key:
            continue
        texts.append(text)
        labels.append(discipline)
        keys.append(key)
    return texts, labels, keys


def has_strong_signal_for_discipline(text: str, discipline: str) -> bool:
    patterns = DISCIPLINE_SIGNAL_PATTERNS.get(discipline, [])
    if not patterns:
        return False
    matches = 0
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            matches += 1
    return matches >= 1


def seed_gold_from_positions(
    payload: Dict[str, Any],
    gold_path: Path,
    positions: List[Dict[str, Any]],
    max_per_class: int,
    min_grad_confidence: float,
) -> int:
    """
    Seed gold labels conservatively from current stored postings.

    Rules:
    - Exclude Other and promoted-model-only relabels
    - Require high grad confidence
    - Require explicit discipline signal in text
    - Skip disciplines with <2 available candidates (for stratified eval stability)
    """
    existing_keys = {str(item.get("position_key") or "") for item in payload["labels"]}

    buckets: Dict[str, List[Tuple[Dict[str, Any], str]]] = defaultdict(list)
    for row in positions:
        if not isinstance(row, dict):
            continue
        key = position_key(row)
        if not key or key in existing_keys:
            continue

        discipline = normalize_discipline(
            row.get("discipline_primary") or row.get("discipline") or "Other"
        )
        if discipline == "Other":
            continue
        if str(row.get("discipline_refinement_source") or "") == "promoted_model":
            continue

        grad_conf = float(row.get("grad_confidence") or 0.0)
        if grad_conf < min_grad_confidence:
            continue

        text = combined_text(row)
        if not text or not has_strong_signal_for_discipline(text, discipline):
            continue

        buckets[discipline].append((row, key))

    # Keep only disciplines with enough candidates to avoid class-count=1 fragility.
    allowed_disciplines = {
        disc for disc, items in buckets.items() if len(items) >= 2
    }
    if not allowed_disciplines:
        return 0

    added = 0
    for discipline in sorted(allowed_disciplines):
        ranked = sorted(
            buckets[discipline],
            key=lambda x: float(x[0].get("grad_confidence") or 0.0),
            reverse=True,
        )
        for row, key in ranked[: max_per_class]:
            payload["labels"].append(
                {
                    "position_key": key,
                    "title": str(row.get("title") or ""),
                    "organization": str(row.get("organization") or ""),
                    "url": str(row.get("url") or ""),
                    "description": str(row.get("description") or ""),
                    "discipline": discipline,
                    "source": "auto_seed_high_confidence_v1",
                    "reviewed_at": now_iso(),
                }
            )
            existing_keys.add(key)
            added += 1

    if added:
        payload["updated_at"] = now_iso()
        with open(gold_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    return added


def filter_rare_gold_classes(
    texts: Sequence[str],
    labels: Sequence[str],
    keys: Sequence[str],
    min_count: int = 2,
) -> Tuple[List[str], List[str], List[str], Dict[str, int]]:
    """Drop classes with too few examples for stratified evaluation."""
    counts = Counter(labels)
    keep_classes = {label for label, count in counts.items() if count >= min_count}
    dropped = {label: count for label, count in counts.items() if count < min_count}
    if not keep_classes:
        return [], [], [], dropped

    out_texts: List[str] = []
    out_labels: List[str] = []
    out_keys: List[str] = []
    for text, label, key in zip(texts, labels, keys):
        if label not in keep_classes:
            continue
        out_texts.append(text)
        out_labels.append(label)
        out_keys.append(key)
    return out_texts, out_labels, out_keys, dropped


def load_positions(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if isinstance(payload.get("positions"), list):
            return payload["positions"]
        if isinstance(payload.get("jobs"), list):
            return payload["jobs"]
    return []


def build_pseudo_examples(
    positions: List[Dict[str, Any]],
    excluded_keys: Sequence[str],
    max_per_class: int,
) -> Tuple[List[str], List[str]]:
    """Build pseudo-labeled examples from stored postings."""
    excluded = set(excluded_keys)
    per_class: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

    for row in positions:
        if not isinstance(row, dict):
            continue
        key = position_key(row)
        if not key or key in excluded:
            continue

        discipline = normalize_discipline(
            row.get("discipline_primary") or row.get("discipline") or "Other"
        )
        if discipline == "Other":
            continue

        grad_conf = float(row.get("grad_confidence") or 0.0)
        if grad_conf < 0.75:
            continue

        text = combined_text(row)
        if not text:
            continue

        bucket = per_class[discipline]
        if len(bucket) >= max_per_class:
            continue
        bucket.append((text, discipline))

    texts: List[str] = []
    labels: List[str] = []
    for discipline in CANONICAL_DISCIPLINES:
        if discipline not in per_class:
            continue
        for text, label in per_class[discipline]:
            texts.append(text)
            labels.append(label)
    return texts, labels


def build_model() -> Tuple[TfidfVectorizer, LogisticRegression]:
    vectorizer = TfidfVectorizer(
        max_features=6000,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
    )
    model = LogisticRegression(
        max_iter=4000,
        class_weight="balanced",
    )
    return vectorizer, model


def fit_model(
    train_texts: Sequence[str],
    train_labels: Sequence[str],
    sample_weight: Optional[Sequence[float]] = None,
) -> Tuple[TfidfVectorizer, LogisticRegression]:
    vectorizer, model = build_model()
    x_train = vectorizer.fit_transform(train_texts)
    if sample_weight is None:
        model.fit(x_train, train_labels)
    else:
        model.fit(x_train, train_labels, sample_weight=np.asarray(sample_weight))
    return vectorizer, model


def evaluate_predictions(
    true_labels: Sequence[str], predicted_labels: Sequence[str]
) -> Dict[str, float]:
    return {
        "accuracy": float(accuracy_score(true_labels, predicted_labels)),
        "macro_f1": float(f1_score(true_labels, predicted_labels, average="macro")),
        "weighted_f1": float(
            f1_score(true_labels, predicted_labels, average="weighted")
        ),
    }


def evaluate_holdout(
    gold_texts: Sequence[str],
    gold_labels: Sequence[str],
    pseudo_texts: Sequence[str],
    pseudo_labels: Sequence[str],
    pseudo_weight: float,
) -> Tuple[Dict[str, Any], TfidfVectorizer, LogisticRegression]:
    train_idx, val_idx = train_test_split(
        np.arange(len(gold_texts)),
        test_size=0.25,
        random_state=42,
        stratify=np.array(gold_labels),
    )
    train_idx = list(train_idx)
    val_idx = list(val_idx)

    train_texts = [gold_texts[i] for i in train_idx] + list(pseudo_texts)
    train_labels = [gold_labels[i] for i in train_idx] + list(pseudo_labels)
    weights = [1.0] * len(train_idx) + [pseudo_weight] * len(pseudo_texts)

    eval_vectorizer, eval_model = fit_model(train_texts, train_labels, weights)
    x_val = eval_vectorizer.transform([gold_texts[i] for i in val_idx])
    y_val = [gold_labels[i] for i in val_idx]
    y_pred = list(eval_model.predict(x_val))
    metrics = evaluate_predictions(y_val, y_pred)
    metrics["evaluation_mode"] = "holdout"
    metrics["validation_samples"] = len(y_val)

    final_texts = list(gold_texts) + list(pseudo_texts)
    final_labels = list(gold_labels) + list(pseudo_labels)
    final_weights = [1.0] * len(gold_texts) + [pseudo_weight] * len(pseudo_texts)
    final_vectorizer, final_model = fit_model(final_texts, final_labels, final_weights)
    return metrics, final_vectorizer, final_model


def evaluate_cross_validation(
    gold_texts: Sequence[str],
    gold_labels: Sequence[str],
    pseudo_texts: Sequence[str],
    pseudo_labels: Sequence[str],
    pseudo_weight: float,
) -> Tuple[Dict[str, Any], TfidfVectorizer, LogisticRegression]:
    labels = np.array(gold_labels)
    min_class_count = min(Counter(labels).values())
    folds = max(2, min(5, min_class_count))

    accuracy_scores: List[float] = []
    macro_scores: List[float] = []
    weighted_scores: List[float] = []
    skf = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
    indices = np.arange(len(gold_texts))
    for train_idx, val_idx in skf.split(indices, labels):
        train_texts = [gold_texts[i] for i in train_idx] + list(pseudo_texts)
        train_labels = [gold_labels[i] for i in train_idx] + list(pseudo_labels)
        weights = [1.0] * len(train_idx) + [pseudo_weight] * len(pseudo_texts)

        eval_vectorizer, eval_model = fit_model(train_texts, train_labels, weights)
        x_val = eval_vectorizer.transform([gold_texts[i] for i in val_idx])
        y_val = [gold_labels[i] for i in val_idx]
        y_pred = list(eval_model.predict(x_val))
        fold_metrics = evaluate_predictions(y_val, y_pred)
        accuracy_scores.append(fold_metrics["accuracy"])
        macro_scores.append(fold_metrics["macro_f1"])
        weighted_scores.append(fold_metrics["weighted_f1"])

    metrics = {
        "accuracy": float(np.mean(accuracy_scores)),
        "macro_f1": float(np.mean(macro_scores)),
        "weighted_f1": float(np.mean(weighted_scores)),
        "evaluation_mode": f"stratified_{folds}fold_cv",
        "validation_samples": len(gold_texts),
    }

    final_texts = list(gold_texts) + list(pseudo_texts)
    final_labels = list(gold_labels) + list(pseudo_labels)
    final_weights = [1.0] * len(gold_texts) + [pseudo_weight] * len(pseudo_texts)
    final_vectorizer, final_model = fit_model(final_texts, final_labels, final_weights)
    return metrics, final_vectorizer, final_model


def read_manifest(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"updated_at": None, "promoted": None, "history": []}
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        return {"updated_at": None, "promoted": None, "history": []}
    payload.setdefault("promoted", None)
    payload.setdefault("history", [])
    return payload


def promotion_decision(
    new_metrics: Dict[str, Any],
    old_metrics: Optional[Dict[str, Any]],
    min_macro_f1_improvement: float,
    min_accuracy_improvement: float,
    force_promote: bool,
) -> Tuple[bool, str]:
    if force_promote:
        return True, "force_promote"
    if not old_metrics:
        return True, "first_promoted_model"

    new_macro = float(new_metrics.get("macro_f1") or 0.0)
    old_macro = float(old_metrics.get("macro_f1") or 0.0)
    new_acc = float(new_metrics.get("accuracy") or 0.0)
    old_acc = float(old_metrics.get("accuracy") or 0.0)

    if new_macro > old_macro + min_macro_f1_improvement:
        return True, "macro_f1_improved"
    if (
        abs(new_macro - old_macro) <= min_macro_f1_improvement
        and new_acc > old_acc + min_accuracy_improvement
    ):
        return True, "accuracy_improved_with_stable_macro_f1"
    return False, "validation_not_improved"


def save_artifact(
    model_dir: Path,
    vectorizer: TfidfVectorizer,
    model: LogisticRegression,
    metrics: Dict[str, Any],
    training_summary: Dict[str, Any],
) -> Dict[str, Any]:
    model_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    models_dir = model_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = models_dir / f"discipline_model_{model_id}.pkl"
    metadata_path = models_dir / f"discipline_model_{model_id}.json"

    artifact = {
        "model_id": model_id,
        "trained_at": now_iso(),
        "vectorizer": vectorizer,
        "classifier": model,
        "classes": list(model.classes_),
        "metrics": metrics,
        "training_summary": training_summary,
    }
    with open(artifact_path, "wb") as f:
        pickle.dump(artifact, f)

    metadata = {
        "model_id": model_id,
        "trained_at": artifact["trained_at"],
        "artifact_path": str(artifact_path),
        "classes": list(model.classes_),
        "metrics": metrics,
        "training_summary": training_summary,
    }
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    return metadata


def update_manifest(
    manifest_path: Path,
    manifest: Dict[str, Any],
    metadata: Dict[str, Any],
    promote: bool,
    reason: str,
) -> Dict[str, Any]:
    event = {
        "timestamp": now_iso(),
        "status": "promoted" if promote else "candidate_rejected",
        "reason": reason,
        "model_id": metadata["model_id"],
        "artifact_path": metadata["artifact_path"],
        "metrics": metadata["metrics"],
    }
    history = manifest.get("history") if isinstance(manifest.get("history"), list) else []
    history.append(event)
    history = history[-100:]

    out = {
        "updated_at": now_iso(),
        "promoted": manifest.get("promoted"),
        "history": history,
    }
    if promote:
        out["promoted"] = {
            "model_id": metadata["model_id"],
            "artifact_path": metadata["artifact_path"],
            "metrics": metadata["metrics"],
            "training_summary": metadata["training_summary"],
            "promoted_at": now_iso(),
        }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    return out


def load_artifact(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    with open(path, "rb") as f:
        payload = pickle.load(f)
    return payload if isinstance(payload, dict) else None


def predict_from_artifact(artifact: Dict[str, Any], text: str) -> Dict[str, Any]:
    vectorizer = artifact["vectorizer"]
    classifier = artifact["classifier"]
    classes = list(artifact.get("classes") or getattr(classifier, "classes_", []))
    if not text.strip() or not classes:
        return {
            "primary": "Other",
            "secondary": "",
            "confidence": 0.0,
            "margin": 0.0,
        }

    vec = vectorizer.transform([text])
    probs = classifier.predict_proba(vec)[0]
    ranked = np.argsort(probs)[::-1]
    top_idx = int(ranked[0])
    primary = str(classes[top_idx])
    top_conf = float(probs[top_idx])
    secondary = ""
    second_conf = 0.0
    if len(ranked) > 1:
        second_idx = int(ranked[1])
        secondary = str(classes[second_idx])
        second_conf = float(probs[second_idx])
    return {
        "primary": primary,
        "secondary": secondary if second_conf >= 0.35 else "",
        "confidence": top_conf,
        "margin": top_conf - second_conf,
    }


def build_confidence_queue(
    rows: List[Dict[str, Any]], artifact: Optional[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    queue: List[Dict[str, Any]] = []
    model_available = artifact is not None
    for row in rows:
        final_disc = normalize_discipline(
            row.get("discipline_primary") or row.get("discipline") or "Other"
        )
        pred = (
            predict_from_artifact(artifact, combined_text(row))
            if model_available
            else {"primary": "Other", "secondary": "", "confidence": 0.0, "margin": 0.0}
        )
        reasons: List[str] = []
        if final_disc == "Other":
            reasons.append("final_other")
        if model_available:
            if final_disc == "Other":
                if (
                    pred["primary"] != "Other"
                    and pred["confidence"] >= 0.6
                    and pred["margin"] >= 0.08
                ):
                    reasons.append("suggested_relabel")
                else:
                    reasons.append("still_other_low_signal")
            elif (
                pred["primary"] != "Other"
                and pred["primary"] != final_disc
                and pred["confidence"] >= 0.7
                and pred["margin"] >= 0.1
            ):
                reasons.append("model_rule_disagreement")
        elif final_disc == "Other":
            reasons.append("no_promoted_model")

        if not reasons:
            continue

        severity = len(reasons) + (1 if "final_other" in reasons else 0)
        queue.append(
            {
                "severity": severity,
                "reasons": reasons,
                "position_key": position_key(row),
                "discipline_final": final_disc,
                "discipline_model_suggested": pred["primary"],
                "discipline_model_secondary": pred["secondary"],
                "model_confidence": round(float(pred["confidence"]), 4),
                "model_margin": round(float(pred["margin"]), 4),
                "title": str(row.get("title") or ""),
                "organization": str(row.get("organization") or ""),
                "location": str(row.get("location") or ""),
                "published_date": str(row.get("published_date") or ""),
                "url": str(row.get("url") or ""),
                "review_status": "",
                "reviewed_discipline": "",
                "review_notes": "",
                "reviewer": "",
            }
        )
    queue.sort(
        key=lambda item: (
            int(item.get("severity") or 0),
            -float(item.get("model_confidence") or 0.0),
            str(item.get("title") or ""),
        ),
        reverse=True,
    )
    return queue


def write_confidence_queue(queue: List[Dict[str, Any]]) -> None:
    json_path = Path("data/processed/discipline_confidence_queue.json")
    csv_path = Path("data/processed/discipline_confidence_queue.csv")
    web_json_path = Path("web/data/discipline_confidence_queue.json")

    payload = {"generated_at": now_iso(), "count": len(queue), "items": queue}
    for out_path in [json_path, web_json_path]:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    fieldnames = [
        "severity",
        "reasons",
        "position_key",
        "discipline_final",
        "discipline_model_suggested",
        "discipline_model_secondary",
        "model_confidence",
        "model_margin",
        "review_status",
        "reviewed_discipline",
        "review_notes",
        "reviewer",
        "title",
        "organization",
        "location",
        "published_date",
        "url",
    ]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in queue:
            out = dict(row)
            out["reasons"] = ";".join(row.get("reasons") or [])
            writer.writerow(out)


def main() -> int:
    args = parse_args()
    if not HAS_SKLEARN:
        print("scikit-learn is required for retraining.")
        return 1

    payload = ensure_gold_dataset(args.gold_file)
    if not args.no_bootstrap and not payload.get("labels"):
        added = bootstrap_gold_from_training_data(payload, args.gold_file)
        if added:
            print(f"Bootstrapped gold labels from training data: +{added}")

    positions = load_positions(args.positions_file)
    if args.auto_seed_from_positions:
        seeded = seed_gold_from_positions(
            payload=payload,
            gold_path=args.gold_file,
            positions=positions,
            max_per_class=args.auto_seed_max_per_class,
            min_grad_confidence=args.auto_seed_min_grad_confidence,
        )
        if seeded:
            print(f"Auto-seeded gold labels from positions: +{seeded}")

    gold_texts, gold_labels, gold_keys = build_gold_examples(payload)
    (
        gold_texts,
        gold_labels,
        gold_keys,
        dropped_rare_classes,
    ) = filter_rare_gold_classes(gold_texts, gold_labels, gold_keys, min_count=2)
    gold_counter = Counter(gold_labels)
    print(f"Gold labels: {len(gold_labels)} rows across {len(gold_counter)} classes")
    if dropped_rare_classes:
        print(f"Dropped rare classes from training set: {dropped_rare_classes}")
    pseudo_texts: List[str] = []
    pseudo_labels: List[str] = []
    if not args.no_pseudo:
        pseudo_texts, pseudo_labels = build_pseudo_examples(
            positions=positions,
            excluded_keys=gold_keys,
            max_per_class=args.max_pseudo_per_class,
        )
    pseudo_counter = Counter(pseudo_labels)
    print(f"Pseudo labels: {len(pseudo_labels)} rows across {len(pseudo_counter)} classes")

    model_dir = args.model_dir
    manifest_path = model_dir / "manifest.json"
    report_path = model_dir / "latest_training_report.json"
    manifest = read_manifest(manifest_path)
    old_metrics = (manifest.get("promoted") or {}).get("metrics")

    trainable = len(gold_labels) >= 8 and len(gold_counter) >= 2
    metrics: Dict[str, Any] = {
        "accuracy": 0.0,
        "macro_f1": 0.0,
        "weighted_f1": 0.0,
        "evaluation_mode": "not_trained",
        "validation_samples": 0,
    }
    candidate_metadata: Optional[Dict[str, Any]] = None
    promote = False
    reason = "insufficient_gold_labels"

    if trainable:
        min_class_count = min(gold_counter.values())
        if min_class_count >= 2 and len(gold_labels) >= 12:
            metrics, vectorizer, model = evaluate_holdout(
                gold_texts,
                gold_labels,
                pseudo_texts,
                pseudo_labels,
                args.pseudo_weight,
            )
        else:
            metrics, vectorizer, model = evaluate_cross_validation(
                gold_texts,
                gold_labels,
                pseudo_texts,
                pseudo_labels,
                args.pseudo_weight,
            )

        training_summary = {
            "gold_total": len(gold_labels),
            "gold_class_counts": dict(gold_counter),
            "pseudo_total": len(pseudo_labels),
            "pseudo_class_counts": dict(pseudo_counter),
            "pseudo_weight": args.pseudo_weight,
            "positions_file": str(args.positions_file),
        }
        candidate_metadata = save_artifact(
            model_dir=model_dir,
            vectorizer=vectorizer,
            model=model,
            metrics=metrics,
            training_summary=training_summary,
        )

        promote, reason = promotion_decision(
            new_metrics=metrics,
            old_metrics=old_metrics,
            min_macro_f1_improvement=args.min_macro_f1_improvement,
            min_accuracy_improvement=args.min_accuracy_improvement,
            force_promote=args.force_promote,
        )
        manifest = update_manifest(
            manifest_path=manifest_path,
            manifest=manifest,
            metadata=candidate_metadata,
            promote=promote,
            reason=reason,
        )
    else:
        print("Not enough gold labels to train. Need >= 8 and >= 2 classes.")

    selected_artifact = None
    promoted = manifest.get("promoted") or {}
    promoted_artifact_path = promoted.get("artifact_path")
    if promoted_artifact_path:
        selected_artifact = load_artifact(Path(str(promoted_artifact_path)))
    elif candidate_metadata:
        selected_artifact = load_artifact(Path(candidate_metadata["artifact_path"]))

    queue = build_confidence_queue(positions, selected_artifact)
    write_confidence_queue(queue)

    report = {
        "generated_at": now_iso(),
        "trained": bool(candidate_metadata),
        "promoted": promote,
        "promotion_reason": reason,
        "metrics": metrics,
        "previous_metrics": old_metrics,
        "candidate_model": candidate_metadata,
        "manifest_path": str(manifest_path),
        "gold_labels": len(gold_labels),
        "gold_class_counts": dict(gold_counter),
        "dropped_rare_gold_classes": dropped_rare_classes,
        "pseudo_labels": len(pseudo_labels),
        "pseudo_class_counts": dict(pseudo_counter),
        "confidence_queue_count": len(queue),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Validation metrics: {metrics}")
    print(f"Promotion decision: {promote} ({reason})")
    if candidate_metadata:
        print(f"Candidate model: {candidate_metadata['model_id']}")
    print(f"Confidence queue rows: {len(queue)}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
