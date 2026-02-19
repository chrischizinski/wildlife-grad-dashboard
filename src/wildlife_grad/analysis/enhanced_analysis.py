"""
Enhanced analysis module for wildlife job positions.

This module provides advanced analytical capabilities including:
- Smart discipline classification using NLP
- Cost of living adjustments to Lincoln, NE
- Historical data management and deduplication
- Geographic clustering and insights
"""

import json
import pickle
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# For NLP-based classification
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("Warning: scikit-learn not available. Using keyword-based classification.")


@dataclass
class JobPosition:
    """Enhanced job position data structure."""

    title: str
    organization: str
    location: str
    salary: str
    starting_date: str
    published_date: str
    tags: str
    description: str = ""  # Project description text
    discipline_primary: str = ""
    discipline_secondary: str = ""
    salary_lincoln_adjusted: float = 0.0
    cost_of_living_index: float = 1.0
    geographic_region: str = ""
    is_graduate_position: bool = False
    position_type: str = ""
    grad_confidence: float = 0.0
    first_seen: str = ""
    last_updated: str = ""
    scraped_at: str = ""  # When this position was scraped
    scrape_run_id: str = ""  # Unique identifier for the scrape run
    scraper_version: str = ""  # Version of the scraper used

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "organization": self.organization,
            "location": self.location,
            "salary": self.salary,
            "starting_date": self.starting_date,
            "published_date": self.published_date,
            "tags": self.tags,
            "description": self.description,
            "discipline_primary": self.discipline_primary,
            "discipline_secondary": self.discipline_secondary,
            "salary_lincoln_adjusted": self.salary_lincoln_adjusted,
            "cost_of_living_index": self.cost_of_living_index,
            "geographic_region": self.geographic_region,
            "is_graduate_position": self.is_graduate_position,
            "position_type": self.position_type,
            "grad_confidence": self.grad_confidence,
            "first_seen": self.first_seen,
            "last_updated": self.last_updated,
            "scraped_at": self.scraped_at,
            "scrape_run_id": self.scrape_run_id,
            "scraper_version": self.scraper_version,
        }


class GraduatePositionDetector:
    """Detect if a position is truly a graduate assistantship/fellowship."""

    def __init__(self):
        # Strong indicators for graduate positions
        self.grad_indicators = {
            "assistantship": [
                "graduate assistantship",
                "research assistantship",
                "teaching assistantship",
                "grad assistantship",
                "RA position",
                "TA position",
                "graduate assistant",
                "assistantship position",
            ],
            "fellowship": [
                "fellowship",
                "graduate fellowship",
                "research fellowship",
                "postgraduate fellowship",
                "PhD fellowship",
                "masters fellowship",
                "doctoral fellowship",
                "scholar program",
            ],
            "degree_pursuit": [
                "PhD position",
                "PhD opportunity",
                "masters position",
                "master's position",
                "doctoral position",
                "graduate degree",
                "pursuing PhD",
                "pursuing masters",
                "PhD student",
                "masters student",
                "graduate student",
                "thesis research",
                "dissertation research",
                "graduate program",
                "MS position",
                "MS opportunity",
            ],
            "funding_keywords": [
                "stipend",
                "tuition waiver",
                "graduate funding",
                "research funding",
                "thesis support",
                "dissertation support",
                "academic year",
                "semester funding",
            ],
        }

        # Strong indicators for NON-graduate positions (exclusions)
        self.exclusion_indicators = {
            "internship": [
                "internship",
                "intern position",
                "summer intern",
                "undergraduate intern",
                "intern opportunity",
                "temporary intern",
                "seasonal intern",
            ],
            "professional": [
                "full-time position",
                "permanent position",
                "career position",
                "staff position",
                "professional position",
                "biologist position",
                "manager position",
                "coordinator position",
                "specialist position",
                "analyst position",
                "technician position",
                "officer position",
                "director position",
                "supervisor position",
                "administrator position",
            ],
            "temporary_work": [
                "temporary position",
                "seasonal position",
                "contract position",
                "consultant",
                "part-time position",
                "hourly position",
                "field work only",
                "summer position only",
            ],
            "undergraduate": [
                "undergraduate position",
                "undergrad position",
                "undergraduate opportunity",
                "high school",
                "community college",
                "associate degree",
            ],
        }

        # Hard exclusions for roles that should not be treated as graduate positions
        # unless assistantship language is explicit.
        self.hard_exclusion_patterns = [
            r"\bpost[-\s]?doc(toral)?\b",
            r"\bveterinarian\b",
            r"\barchaeologist\b",
            r"\bassistant\s+professor\b",
            r"\bassociate\s+professor\b",
            r"\bprofessor\b",
            r"\bprincipal\s+investigator\b",
            r"\bvisiting\s+assistant\s+professor\b",
            r"\breu\b",
            r"\bintern(ship)?\b",
            r"\bfield\s+technician\b",
            r"\btechnician\b",
            r"\becologist\b",
            r"\benvironmental\s+specialist\b",
            r"\bspecialist\s*\(rapid\s+responder\)\b",
            r"\bfellowship\s+coordinator\b",
            r"\bresearch\s+assistant\s*/\s*associate\b",
            r"\bsenior\s+conservation\s+research\s+assistant\b",
            r"\bseasonal\s+research\s+assistant\b",
            r"\bsummer\s+fellowship\b",
            r"\b(laboratory|lab)\s+and\s+field\s+support\b",
            r"\bnoaa\b.*\bfellowship\b",
            r"\bconduct\s+your\s+own\s+research\s+project\b",
            r"\bwork\s+study\b",
            r"\bcontinuing\s+education\b",
            r"\bmaster'?s?\s+degrees?\s+for\s+.+\s+professionals?\b",
            r"\bstudent\s+contractor\b",
            r"\bbiologist\s+i{1,2}\b",
            r"\bprofessional\s+certificate\b",
            r"\bcertificate\s+program\b",
        ]
        self.explicit_assistantship_patterns = [
            r"\bgraduate\s+assistantship\b",
            r"\bresearch\s+assistantship\b",
            r"\bteaching\s+assistantship\b",
            r"\bgraduate\s+research\s+assistant(ship)?\b",
            r"\bph\.?d\.?\s+assistantship\b",
            r"\bms\b.*\bassistantship\b",
        ]
        self.explicit_graduate_patterns = [
            r"graduate\s+research\s+assistantship",
            r"graduate\s+research\s+assistant\b",
            r"(ms|m\.s\.|masters?)\s+(research\s+)?assistantship",
            r"(ms|m\.s\.|masters?)\s+research\s+assistant\b",
            r"(phd|ph\.d\.)\s+(research\s+)?assistantship",
            r"graduate\s+research\s+associate",
            r"doctoral\s+(student|candidate|research|assistantship)",
            r"(phd|ph\.d\.)\s+(student|candidate|position)",
            r"(ms|m\.s\.)\s+(student|candidate|position)",
            r"thesis\s+research",
            r"dissertation\s+research",
        ]

    def _analyze_text(self, text: str) -> Dict[str, object]:
        """Score graduate/non-graduate evidence for a text snippet."""
        text_content = text.lower()
        has_hard_exclusion = any(
            re.search(pattern, text_content, re.IGNORECASE)
            for pattern in self.hard_exclusion_patterns
        )
        has_explicit_assistantship = any(
            re.search(pattern, text_content, re.IGNORECASE)
            for pattern in self.explicit_assistantship_patterns
        )

        grad_score = 0
        exclusion_score = 0
        classification_type = "unknown"

        for category, keywords in self.grad_indicators.items():
            matches = sum(1 for keyword in keywords if keyword in text_content)
            if matches > 0:
                grad_score += matches * 2
                if category == "assistantship":
                    classification_type = "Graduate Assistantship"
                elif category == "fellowship":
                    classification_type = "Fellowship"
                elif category == "degree_pursuit" and classification_type == "unknown":
                    classification_type = "Graduate Position"

        for _category, keywords in self.exclusion_indicators.items():
            matches = sum(1 for keyword in keywords if keyword in text_content)
            if matches > 0:
                exclusion_score += matches * 3

        if any(term in text_content for term in ["phd", "doctoral", "doctorate"]):
            grad_score += 2
            if classification_type == "unknown":
                classification_type = "PhD Position"

        if any(term in text_content for term in ["masters", "master's", "ms degree", "ms position"]):
            grad_score += 2
            if classification_type == "unknown":
                classification_type = "Masters Position"

        total_score = grad_score - exclusion_score
        confidence = min(max(total_score / 10.0, 0.0), 1.0)
        has_explicit_pattern = any(
            re.search(pattern, text_content, re.IGNORECASE)
            for pattern in self.explicit_graduate_patterns
        )

        return {
            "has_hard_exclusion": has_hard_exclusion,
            "has_explicit_assistantship": has_explicit_assistantship,
            "has_explicit_pattern": has_explicit_pattern,
            "classification_type": classification_type,
            "grad_score": grad_score,
            "exclusion_score": exclusion_score,
            "total_score": total_score,
            "confidence": confidence,
        }

    def _label_for_decision(self, analysis: Dict[str, object], is_grad: bool) -> str:
        """Resolve final position type label from analysis evidence."""
        if not is_grad:
            return "Professional/Other"

        classification_type = str(analysis["classification_type"])
        if classification_type != "unknown":
            return classification_type
        if analysis["has_explicit_assistantship"]:
            return "Graduate Assistantship"
        return "Graduate Position"

    def _title_phase_decision(
        self, analysis: Dict[str, object]
    ) -> Optional[Tuple[bool, str, float]]:
        """
        Title-first decision.

        Returns None when title evidence is ambiguous and description fallback
        should be applied.
        """
        if analysis["has_hard_exclusion"] and not analysis["has_explicit_assistantship"]:
            return False, "Professional/Other", 0.1

        if analysis["has_explicit_pattern"] or analysis["has_explicit_assistantship"]:
            return True, self._label_for_decision(analysis, True), max(float(analysis["confidence"]), 0.85)

        if (
            float(analysis["confidence"]) >= 0.8
            and int(analysis["grad_score"]) >= 4
            and int(analysis["exclusion_score"]) == 0
        ):
            return True, self._label_for_decision(analysis, True), float(analysis["confidence"])

        if int(analysis["exclusion_score"]) >= 4 and int(analysis["grad_score"]) == 0:
            return False, "Professional/Other", min(float(analysis["confidence"]), 0.2)

        return None

    def is_graduate_position(self, position: "JobPosition") -> Tuple[bool, str, float]:
        """
        Determine if position is a graduate assistantship/fellowship.

        Returns:
            Tuple of (is_graduate, classification_type, confidence_score)
        """
        title_text = f"{position.title} {position.tags}"
        title_analysis = self._analyze_text(title_text)
        title_decision = self._title_phase_decision(title_analysis)
        if title_decision is not None:
            return title_decision

        full_text = (
            f"{position.title} {position.tags} {position.organization} {position.description}"
        )
        analysis = self._analyze_text(full_text)
        if analysis["has_hard_exclusion"] and not analysis["has_explicit_assistantship"]:
            return False, "Professional/Other", 0.1

        is_graduate = (
            float(analysis["confidence"]) >= 0.7
            or bool(analysis["has_explicit_pattern"])
            or (
                int(analysis["total_score"]) > 0
                and int(analysis["grad_score"]) >= 2
                and int(analysis["exclusion_score"]) < int(analysis["grad_score"]) * 2
            )
        )
        confidence = float(analysis["confidence"])
        if is_graduate and (
            analysis["has_explicit_pattern"] or analysis["has_explicit_assistantship"]
        ):
            confidence = max(confidence, 0.75)
        if not is_graduate:
            confidence = min(confidence, 0.3)

        return is_graduate, self._label_for_decision(analysis, is_graduate), confidence


class DisciplineClassifier:
    """Smart discipline classification using your specific categories."""

    def __init__(self):
        # Canonical taxonomy:
        # - Environmental Sciences (soil/water/abiotic focus)
        # - Fisheries and Aquatic (aquatic organisms/fishes)
        # - Wildlife (terrestrial organisms)
        # - Entomology (insects/arthropods)
        # - Forestry and Habitat (trees/habitat/forest systems)
        # - Agriculture (cattle/livestock/ag systems)
        # - Human Dimensions (people-focused)
        # - Other (fallback)
        self.discipline_keywords = {
            "Environmental Sciences": [
                "environmental science",
                "environmental sciences",
                "water quality",
                "water chemistry",
                "groundwater",
                "surface water",
                "hydrology",
                "watershed",
                "soil",
                "soil science",
                "soil chemistry",
                "biogeochemistry",
                "geochemistry",
                "contaminant",
                "pollution",
                "toxicology",
                "air quality",
                "climate",
                "climate change",
                "atmospheric",
                "remote sensing",
                "gis",
                "spatial analysis",
                "water security",
                "sustainability",
                "microbiology",
                "environmental microbiology",
                "carbon",
                "coastal",
                "tidal",
            ],
            "Fisheries and Aquatic": [
                "fisheries",
                "fish",
                "aquatic",
                "marine",
                "freshwater",
                "stream",
                "river",
                "lake",
                "estuary",
                "salmon",
                "trout",
                "bass",
                "sturgeon",
                "aquaculture",
                "hatchery",
                "spawning",
                "fish passage",
                "aquatic organism",
                "ichthyology",
                "marine science",
                "manta ray",
                "bycatch",
                "limnology",
                "algal bloom",
            ],
            "Wildlife": [
                "wildlife",
                "mammal",
                "bird",
                "avian",
                "terrestrial",
                "vertebrate",
                "fauna",
                "carnivore",
                "ungulate",
                "deer",
                "elk",
                "bear",
                "wolf",
                "bat",
                "reptile",
                "amphibian",
                "herpetology",
                "predator",
                "migration",
                "behavior",
                "wildlife management",
                "wildlife conservation",
                "endangered",
                "threatened",
                "wildlife ecology",
                "ornithology",
                "mammalogy",
                "waterfowl",
                "mallard",
                "duck",
                "mountain goat",
                "swine",
                "bobwhite",
                "natural resource sciences",
                "turtle",
                "cooter",
            ],
            "Entomology": [
                "entomology",
                "insect",
                "insects",
                "arthropod",
                "arthropods",
                "pollinator",
                "pollinators",
                "bee",
                "bees",
                "butterfly",
                "beetle",
                "mosquito",
                "tick",
                "lepidoptera",
                "coleoptera",
                "ant",
                "ants",
                "ant colony",
            ],
            "Forestry and Habitat": [
                "forestry",
                "forest",
                "silviculture",
                "timber",
                "tree",
                "trees",
                "woodland",
                "canopy",
                "understory",
                "forest stand",
                "forest management",
                "forest restoration",
                "rangeland",
                "habitat",
                "habitat restoration",
                "habitat management",
                "vegetation",
                "land management",
                "fuel treatment",
                "prescribed burn",
                "wildfire",
            ],
            "Agriculture": [
                "agriculture",
                "agricultural",
                "agronomy",
                "crop",
                "cropping",
                "livestock",
                "cattle",
                "beef",
                "dairy",
                "ranch",
                "ranching",
                "pasture",
                "grazing",
                "animal science",
                "husbandry",
                "range cattle",
            ],
            "Human Dimensions": [
                "human dimensions",
                "stakeholder",
                "attitude",
                "perception",
                "social science",
                "survey",
                "interview",
                "focus group",
                "questionnaire",
                "coexistence",
                "hunting",
                "recreation",
                "tourism",
                "economics",
                "policy",
                "governance",
                "sociology",
                "anthropology",
                "psychology",
                "human-wildlife conflict",
                "human behavior",
                "community engagement",
                "public participation",
                "environmental justice",
                "traditional knowledge",
                "cultural values",
                "stakeholder engagement",
                "environmental communication",
                "interpretation",
                "visitor studies",
                "recreation management",
                "public opinion",
                "environmental education",
                "science communication",
            ],
        }

        if HAS_SKLEARN:
            self.vectorizer = TfidfVectorizer(max_features=1000, stop_words="english")
            self.is_trained = False

        self.hard_non_grad_patterns = [
            r"\bveterinarian\b",
            r"\barchaeologist\b",
            r"\bpost[-\s]?doc(toral)?\b",
            r"\bassistant\s+professor\b",
            r"\bassociate\s+professor\b",
            r"\bprofessor\b",
            r"\bprincipal\s+investigator\b",
            r"\bvisiting\s+assistant\s+professor\b",
            r"\breu\b",
            r"\bintern(ship)?\b",
            r"\bfield\s+technician\b",
            r"\btechnician\b",
            r"\becologist\b",
            r"\benvironmental\s+specialist\b",
            r"\bspecialist\s*\(rapid\s+responder\)\b",
            r"\bbiologist\s+i{1,2}\b",
            r"\bprofessional\s+certificate\b",
            r"\bcertificate\s+program\b",
            r"\bstudent\s+contractor\b",
            r"\bconduct\s+your\s+own\s+research\s+project\b",
        ]
        self.explicit_assistantship_patterns = [
            r"\bgraduate\s+assistantship\b",
            r"\bresearch\s+assistantship\b",
            r"\bteaching\s+assistantship\b",
            r"\bgraduate\s+research\s+assistant(ship)?\b",
            r"\bph\.?d\.?\s+assistantship\b",
            r"\bms\b.*\bassistantship\b",
        ]
        self.biotic_disciplines = {
            "Fisheries and Aquatic",
            "Wildlife",
            "Entomology",
            "Forestry and Habitat",
            "Agriculture",
        }
        self.discipline_priority = [
            "Human Dimensions",
            "Entomology",
            "Fisheries and Aquatic",
            "Wildlife",
            "Forestry and Habitat",
            "Agriculture",
            "Environmental Sciences",
        ]
        self.ml_refine_enabled = HAS_SKLEARN
        self.ml_min_similarity = 0.12
        self.ml_override_similarity = 0.2
        self.secondary_ml_enabled = HAS_SKLEARN
        self.secondary_ml_min_train = 8
        self.secondary_ml_min_classes = 2
        self.secondary_ml_min_similarity = 0.3
        self.secondary_ml_min_margin = 0.1
        self.secondary_ml_secondary_min_similarity = 0.12
        self.promoted_model_enabled = HAS_SKLEARN
        self.promoted_model_min_confidence = 0.62
        self.promoted_model_min_margin = 0.08
        self.promoted_model_secondary_min_confidence = 0.35
        self.promoted_model_manifest_path = Path("data/models/discipline/manifest.json")
        self.promoted_model_id = ""
        self._promoted_model_checked = False
        self._promoted_model: Optional[Dict[str, Any]] = None

    def classify_position(self, position: JobPosition) -> Tuple[str, str]:
        """
        Classify a position into primary and secondary disciplines.

        Args:
            position: JobPosition object

        Returns:
            Tuple of (primary_discipline, secondary_discipline)
        """
        title_text = f"{position.title} {position.tags}".lower()
        # Combine title, tags, organization, and description for comprehensive analysis
        text_content = (
            f"{position.title} {position.tags} {position.organization} {position.description}".lower()
        )

        has_hard_non_grad = any(
            re.search(pattern, text_content, re.IGNORECASE)
            for pattern in self.hard_non_grad_patterns
        )
        has_explicit_assistantship = any(
            re.search(pattern, text_content, re.IGNORECASE)
            for pattern in self.explicit_assistantship_patterns
        )
        if has_hard_non_grad and not has_explicit_assistantship:
            return "Other", ""

        # Title-first: return only when title gives a confident taxonomy signal.
        title_primary, title_secondary, title_scores = self._keyword_classify_with_scores(title_text)
        if self._is_confident_title_match(title_scores):
            return title_primary, title_secondary

        # Fallback: use description/context when title is ambiguous.
        full_primary, full_secondary, full_scores = self._keyword_classify_with_scores(
            text_content
        )
        if not full_scores:
            return self._maybe_refine_with_ml("Other", "", {}, text_content)

        if title_scores:
            combined_scores = dict(full_scores)
            for discipline in title_scores:
                combined_scores[discipline] = combined_scores.get(discipline, 0) + 1
            primary, secondary = self._classify_from_scores(combined_scores)
            return self._maybe_refine_with_ml(
                primary, secondary, combined_scores, text_content
            )
        return self._maybe_refine_with_ml(
            full_primary, full_secondary, full_scores, text_content
        )

    def _is_confident_title_match(self, scores: Dict[str, int]) -> bool:
        """Determine whether title-only evidence is strong enough to finalize."""
        if not scores:
            return False
        ranked = self._rank_disciplines(scores)
        top_score = ranked[0][1]
        second_score = ranked[1][1] if len(ranked) > 1 else 0
        margin = top_score - second_score
        return top_score >= 4 or (top_score >= 3 and margin >= 2) or (top_score >= 2 and margin >= 2)

    def _keyword_classify(self, text: str) -> Tuple[str, str]:
        """Keyword-based classification fallback."""
        primary, secondary, _scores = self._keyword_classify_with_scores(text)
        return primary, secondary

    def _keyword_classify_with_scores(self, text: str) -> Tuple[str, str, Dict[str, int]]:
        """Keyword classifier that also returns discipline scores for confidence gates."""
        scores = {}
        strong_abiotic_terms = [
            "climate action",
            "climate change",
            "carbon",
            "biogeochemistry",
            "soil",
            "hydrology",
            "water security",
            "water quality",
            "environmental microbiology",
            "microbiology",
            "sustainability",
        ]
        has_strong_abiotic_signal = any(term in text for term in strong_abiotic_terms)

        for discipline, keywords in self.discipline_keywords.items():
            score = 0
            for keyword in keywords:
                if " " in keyword:
                    if keyword in text:
                        score += 2
                    continue
                if re.search(rf"\b{re.escape(keyword)}s?\b", text):
                    score += 1
            if score > 0:
                scores[discipline] = score

        # Environmental Sciences should not win when only weak abiotic signal is present
        # and biotic categories have stronger signal.
        if "Environmental Sciences" in scores:
            has_biotic_signal = any(scores.get(cat, 0) > 0 for cat in self.biotic_disciplines)
            if has_biotic_signal and not has_strong_abiotic_signal:
                scores["Environmental Sciences"] = 0

        # Climate/carbon/ocean-process postings can mention fisheries programs,
        # but remain abiotic/environmental in focus.
        if scores.get("Environmental Sciences", 0) > 0 and scores.get("Fisheries and Aquatic", 0) > 0:
            if any(
                term in text
                for term in ["climate action", "carbon cycle", "biogeochemical", "water security"]
            ):
                scores["Environmental Sciences"] += 2

        # Forest-focused postings with explicit soil/biogeochemistry terms are
        # Environmental Sciences (abiotic) rather than Forestry and Habitat.
        if scores.get("Environmental Sciences", 0) > 0 and scores.get("Forestry and Habitat", 0) > 0:
            if any(
                term in text
                for term in [
                    "soil",
                    "soil chemistry",
                    "biogeochemistry",
                    "hydrology",
                    "water quality",
                    "environmental microbiology",
                ]
            ):
                scores["Environmental Sciences"] += 2

        has_explicit_human_dimensions_signal = any(
            term in text
            for term in [
                "human dimensions",
                "stakeholder",
                "survey",
                "interview",
                "social science",
                "science communication",
                "environmental education",
            ]
        )
        # Avoid false Human Dimensions assignment from weak incidental matches.
        if (
            scores.get("Human Dimensions", 0) <= 2
            and not has_explicit_human_dimensions_signal
        ):
            has_non_human_signal = any(
                scores.get(cat, 0) > 0 for cat in scores if cat != "Human Dimensions"
            )
            if has_non_human_signal:
                scores["Human Dimensions"] = 0

        scores = {disc: score for disc, score in scores.items() if score > 0}
        if not scores:
            return "Other", "", {}

        primary, secondary = self._classify_from_scores(scores)
        return primary, secondary, scores

    def _rank_disciplines(self, scores: Dict[str, int]) -> List[Tuple[str, int]]:
        """Rank disciplines by score with deterministic priority tie-breaks."""
        priority_rank = {name: i for i, name in enumerate(self.discipline_priority[::-1], start=1)}
        return sorted(
            scores.items(),
            key=lambda x: (x[1], priority_rank.get(x[0], 0)),
            reverse=True,
        )

    def _classify_from_scores(self, scores: Dict[str, int]) -> Tuple[str, str]:
        """Select primary/secondary disciplines from already-scored categories."""
        if not scores:
            return "Other", ""
        sorted_disciplines = self._rank_disciplines(scores)
        primary = sorted_disciplines[0][0]
        secondary = (
            sorted_disciplines[1][0]
            if len(sorted_disciplines) > 1 and sorted_disciplines[1][1] > 0
            else ""
        )
        return primary, secondary

    def _is_ambiguous_scores(self, scores: Dict[str, int]) -> bool:
        """Return True when rule-based evidence is weak/tied and eligible for ML refinement."""
        if not scores:
            return True
        ranked = self._rank_disciplines(scores)
        top_score = ranked[0][1]
        second_score = ranked[1][1] if len(ranked) > 1 else 0
        return top_score <= 2 or (top_score - second_score) <= 1

    def _maybe_refine_with_ml(
        self,
        primary: str,
        secondary: str,
        scores: Dict[str, int],
        text: str,
    ) -> Tuple[str, str]:
        """Use ML only for ambiguous cases and only with sufficient confidence."""
        if not self.ml_refine_enabled or not self._is_ambiguous_scores(scores):
            return primary, secondary

        ml_primary, ml_secondary, ml_confidence = self._ml_classify_with_confidence(text)
        if ml_confidence < self.ml_min_similarity or ml_primary == "Other":
            return primary, secondary
        if primary == "Other":
            return ml_primary, ml_secondary
        if ml_primary != primary and ml_confidence < self.ml_override_similarity:
            return primary, secondary
        return ml_primary, ml_secondary

    def _ml_classify_with_confidence(self, text: str) -> Tuple[str, str, float]:
        """ML discipline classification returning top similarity confidence."""
        if not HAS_SKLEARN:
            return "Other", "", 0.0

        discipline_texts = []
        discipline_labels = []
        for discipline, keywords in self.discipline_keywords.items():
            discipline_texts.append(" ".join(keywords))
            discipline_labels.append(discipline)

        all_texts = discipline_texts + [text]
        tfidf_matrix = self.vectorizer.fit_transform(all_texts)
        job_vector = tfidf_matrix[-1]
        discipline_vectors = tfidf_matrix[:-1]
        similarities = cosine_similarity(job_vector, discipline_vectors).flatten()
        top_indices = np.argsort(similarities)[::-1][:2]

        top_similarity = float(similarities[top_indices[0]])
        primary_discipline = discipline_labels[top_indices[0]]
        secondary_discipline = (
            discipline_labels[top_indices[1]]
            if len(top_indices) > 1 and similarities[top_indices[1]] > 0.1
            else ""
        )

        if top_similarity < 0.05:
            kw_primary, kw_secondary, _scores = self._keyword_classify_with_scores(text)
            return kw_primary, kw_secondary, top_similarity

        return primary_discipline, secondary_discipline, top_similarity

    def _ml_classify(self, text: str) -> Tuple[str, str]:
        """Machine learning-based classification using TF-IDF and semantic similarity."""
        primary, secondary, _confidence = self._ml_classify_with_confidence(text)
        return primary, secondary

    @staticmethod
    def _position_text(position: JobPosition) -> str:
        """Build normalized free text used by discipline classification models."""
        return (
            f"{position.title} {position.tags} "
            f"{position.organization} {position.description}"
        ).lower()

    def _build_secondary_ml_artifacts(
        self, positions: List[JobPosition], primary_labels: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Train a lightweight second-pass model from first-pass non-Other labels."""
        if not HAS_SKLEARN:
            return None

        train_texts: List[str] = []
        train_labels: List[str] = []
        for position, label in zip(positions, primary_labels):
            normalized_label = str(label or "").strip() or "Other"
            if normalized_label == "Other":
                continue
            text = self._position_text(position)
            if not text.strip():
                continue
            train_texts.append(text)
            train_labels.append(normalized_label)

        if len(train_texts) < self.secondary_ml_min_train:
            return None

        unique_labels = sorted(set(train_labels))
        if len(unique_labels) < self.secondary_ml_min_classes:
            return None

        vectorizer = TfidfVectorizer(
            max_features=4000,
            stop_words="english",
            ngram_range=(1, 2),
        )
        train_matrix = vectorizer.fit_transform(train_texts)

        label_to_indices: Dict[str, List[int]] = defaultdict(list)
        for idx, label in enumerate(train_labels):
            label_to_indices[label].append(idx)

        centroid_labels: List[str] = []
        centroid_rows: List[np.ndarray] = []
        for label in sorted(label_to_indices):
            indices = label_to_indices[label]
            if not indices:
                continue
            centroid_labels.append(label)
            centroid_rows.append(np.asarray(train_matrix[indices].mean(axis=0)).ravel())

        if len(centroid_labels) < self.secondary_ml_min_classes:
            return None

        centroid_matrix = np.vstack(centroid_rows)
        return {
            "vectorizer": vectorizer,
            "centroid_labels": centroid_labels,
            "centroid_matrix": centroid_matrix,
        }

    def _secondary_ml_predict(
        self, artifacts: Dict[str, Any], position: JobPosition
    ) -> Tuple[str, str, float, float]:
        """Predict discipline with similarity and margin from second-pass model."""
        vectorizer = artifacts["vectorizer"]
        centroid_labels = artifacts["centroid_labels"]
        centroid_matrix = artifacts["centroid_matrix"]

        text = self._position_text(position)
        if not text.strip():
            return "Other", "", 0.0, 0.0

        vec = vectorizer.transform([text])
        similarities = cosine_similarity(vec, centroid_matrix).flatten()
        if similarities.size == 0:
            return "Other", "", 0.0, 0.0

        ranked_indices = np.argsort(similarities)[::-1]
        top_idx = int(ranked_indices[0])
        top_label = str(centroid_labels[top_idx])
        top_similarity = float(similarities[top_idx])

        second_similarity = 0.0
        secondary_label = ""
        if len(ranked_indices) > 1:
            second_idx = int(ranked_indices[1])
            second_similarity = float(similarities[second_idx])
            if second_similarity >= self.secondary_ml_secondary_min_similarity:
                secondary_label = str(centroid_labels[second_idx])

        margin = top_similarity - second_similarity
        return top_label, secondary_label, top_similarity, margin

    def refine_other_labels_with_secondary_ml(
        self,
        positions: List[JobPosition],
        primary_labels: List[str],
        secondary_labels: Optional[List[str]] = None,
    ) -> Tuple[List[str], List[str]]:
        """
        Second-pass discipline refinement.

        - Train on first-pass non-Other labels
        - Relabel only first-pass Other rows
        - Apply similarity + margin confidence gates
        """
        base_primary = [str(label or "").strip() or "Other" for label in primary_labels]
        if secondary_labels is None:
            base_secondary = ["" for _ in base_primary]
        else:
            base_secondary = [str(label or "").strip() for label in secondary_labels]

        if len(positions) != len(base_primary) or len(base_secondary) != len(base_primary):
            raise ValueError("Positions and label lists must be the same length")

        if not self.secondary_ml_enabled or not HAS_SKLEARN:
            return base_primary, base_secondary

        artifacts = self._build_secondary_ml_artifacts(positions, base_primary)
        if not artifacts:
            return base_primary, base_secondary

        refined_primary = list(base_primary)
        refined_secondary = list(base_secondary)
        for idx, (position, primary) in enumerate(zip(positions, refined_primary)):
            if primary != "Other":
                continue

            ml_primary, ml_secondary, similarity, margin = self._secondary_ml_predict(
                artifacts, position
            )
            if (
                similarity < self.secondary_ml_min_similarity
                or margin < self.secondary_ml_min_margin
                or ml_primary == "Other"
            ):
                continue

            refined_primary[idx] = ml_primary
            refined_secondary[idx] = (
                ml_secondary if ml_secondary and ml_secondary != ml_primary else ""
            )

        return refined_primary, refined_secondary

    def _load_promoted_model_if_needed(self) -> Optional[Dict[str, Any]]:
        """Load promoted discipline model artifact from manifest when available."""
        if self._promoted_model_checked:
            return self._promoted_model

        self._promoted_model_checked = True
        if not self.promoted_model_enabled or not HAS_SKLEARN:
            return None

        try:
            if not self.promoted_model_manifest_path.exists():
                return None

            with open(self.promoted_model_manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            promoted = manifest.get("promoted") or {}
            artifact_path_raw = promoted.get("artifact_path")
            if not artifact_path_raw:
                return None

            artifact_path = Path(str(artifact_path_raw))
            if not artifact_path.is_absolute():
                artifact_path = Path.cwd() / artifact_path
            if not artifact_path.exists():
                fallback = self.promoted_model_manifest_path.parent / Path(
                    str(artifact_path_raw)
                ).name
                if fallback.exists():
                    artifact_path = fallback
                else:
                    return None

            with open(artifact_path, "rb") as f:
                artifact = pickle.load(f)

            if not isinstance(artifact, dict):
                return None
            if "vectorizer" not in artifact or "classifier" not in artifact:
                return None

            self._promoted_model = artifact
            self.promoted_model_id = str(
                artifact.get("model_id") or promoted.get("model_id") or ""
            )
            return self._promoted_model
        except Exception:
            return None

    def predict_with_promoted_model(self, position: JobPosition) -> Dict[str, Any]:
        """Predict discipline from promoted model with confidence + margin diagnostics."""
        artifact = self._load_promoted_model_if_needed()
        if not artifact:
            return {
                "available": False,
                "model_id": "",
                "primary": "",
                "secondary": "",
                "confidence": 0.0,
                "margin": 0.0,
            }

        text = self._position_text(position)
        if not text.strip():
            return {
                "available": True,
                "model_id": self.promoted_model_id,
                "primary": "Other",
                "secondary": "",
                "confidence": 0.0,
                "margin": 0.0,
            }

        try:
            vectorizer = artifact["vectorizer"]
            classifier = artifact["classifier"]
            classes = list(
                artifact.get("classes")
                or getattr(classifier, "classes_", [])
            )
            if not classes:
                return {
                    "available": True,
                    "model_id": self.promoted_model_id,
                    "primary": "Other",
                    "secondary": "",
                    "confidence": 0.0,
                    "margin": 0.0,
                }

            vec = vectorizer.transform([text])
            if hasattr(classifier, "predict_proba"):
                probabilities = classifier.predict_proba(vec)[0]
            elif hasattr(classifier, "decision_function"):
                decision = classifier.decision_function(vec)
                if getattr(decision, "ndim", 1) > 1:
                    scores = decision[0]
                    exp_scores = np.exp(scores - np.max(scores))
                    probabilities = exp_scores / np.sum(exp_scores)
                elif len(classes) == 2:
                    score = float(decision[0])
                    p1 = 1.0 / (1.0 + np.exp(-score))
                    probabilities = np.array([1.0 - p1, p1], dtype=float)
                else:
                    probabilities = np.array([1.0], dtype=float)
            else:
                predicted = classifier.predict(vec)[0]
                return {
                    "available": True,
                    "model_id": self.promoted_model_id,
                    "primary": str(predicted),
                    "secondary": "",
                    "confidence": 0.0,
                    "margin": 0.0,
                }

            ranked = np.argsort(probabilities)[::-1]
            top_idx = int(ranked[0])
            top_label = str(classes[top_idx])
            top_conf = float(probabilities[top_idx])

            second_label = ""
            second_conf = 0.0
            if len(ranked) > 1:
                second_idx = int(ranked[1])
                second_label = str(classes[second_idx])
                second_conf = float(probabilities[second_idx])

            margin = top_conf - second_conf
            if second_conf < self.promoted_model_secondary_min_confidence:
                second_label = ""

            return {
                "available": True,
                "model_id": self.promoted_model_id,
                "primary": top_label,
                "secondary": second_label,
                "confidence": top_conf,
                "margin": margin,
            }
        except Exception:
            return {
                "available": False,
                "model_id": "",
                "primary": "",
                "secondary": "",
                "confidence": 0.0,
                "margin": 0.0,
            }

    def refine_other_labels_with_promoted_model(
        self,
        positions: List[JobPosition],
        primary_labels: List[str],
        secondary_labels: Optional[List[str]] = None,
    ) -> Tuple[List[str], List[str]]:
        """
        Third-pass discipline refinement from persisted promoted model.

        - Only refines rows still labeled Other
        - Requires minimum model confidence and class-margin thresholds
        """
        base_primary = [str(label or "").strip() or "Other" for label in primary_labels]
        if secondary_labels is None:
            base_secondary = ["" for _ in base_primary]
        else:
            base_secondary = [str(label or "").strip() for label in secondary_labels]

        if len(positions) != len(base_primary) or len(base_secondary) != len(base_primary):
            raise ValueError("Positions and label lists must be the same length")
        if not self.promoted_model_enabled:
            return base_primary, base_secondary

        refined_primary = list(base_primary)
        refined_secondary = list(base_secondary)
        for idx, (position, primary) in enumerate(zip(positions, refined_primary)):
            if primary != "Other":
                continue
            pred = self.predict_with_promoted_model(position)
            if not pred.get("available"):
                continue
            pred_primary = str(pred.get("primary") or "")
            pred_secondary = str(pred.get("secondary") or "")
            confidence = float(pred.get("confidence") or 0.0)
            margin = float(pred.get("margin") or 0.0)

            if not pred_primary or pred_primary == "Other":
                continue
            if confidence < self.promoted_model_min_confidence:
                continue
            if margin < self.promoted_model_min_margin:
                continue

            refined_primary[idx] = pred_primary
            refined_secondary[idx] = (
                pred_secondary if pred_secondary and pred_secondary != pred_primary else ""
            )

        return refined_primary, refined_secondary


class CostOfLivingAdjuster:
    """Adjust salaries to Lincoln, NE cost of living baseline."""

    def __init__(self):
        # Comprehensive cost of living indices relative to Lincoln, NE (baseline = 1.0)
        # Based on Bureau of Labor Statistics, C2ER, and academic salary surveys
        # Load cost of living indices from configuration file
        self.cost_indices = self._load_cost_indices()

        # State abbreviation mapping
        self.state_abbrevs = {
            "al": "alabama",
            "ak": "alaska",
            "az": "arizona",
            "ar": "arkansas",
            "ca": "california",
            "co": "colorado",
            "ct": "connecticut",
            "de": "delaware",
            "fl": "florida",
            "ga": "georgia",
            "hi": "hawaii",
            "id": "idaho",
            "il": "illinois",
            "in": "indiana",
            "ia": "iowa",
            "ks": "kansas",
            "ky": "kentucky",
            "la": "louisiana",
            "me": "maine",
            "md": "maryland",
            "ma": "massachusetts",
            "mi": "michigan",
            "mn": "minnesota",
            "ms": "mississippi",
            "mo": "missouri",
            "mt": "montana",
            "ne": "nebraska",
            "nv": "nevada",
            "nh": "new hampshire",
            "nj": "new jersey",
            "nm": "new mexico",
            "ny": "new york",
            "nc": "north carolina",
            "nd": "north dakota",
            "oh": "ohio",
            "ok": "oklahoma",
            "or": "oregon",
            "pa": "pennsylvania",
            "ri": "rhode island",
            "sc": "south carolina",
            "sd": "south dakota",
            "tn": "tennessee",
            "tx": "texas",
            "ut": "utah",
            "vt": "vermont",
            "va": "virginia",
            "wa": "washington",
            "wv": "west virginia",
            "wi": "wisconsin",
            "wy": "wyoming",
        }

    def _load_cost_indices(self) -> Dict[str, float]:
        """Load cost of living indices from JSON configuration."""
        try:
            # Try to locate the config file relative to this script or project root
            current_dir = Path(__file__).parent

            # Try multiple potential locations
            potential_paths = [
                current_dir.parent.parent.parent / "data" / "config" / "cost_of_living.json",  # src/wildlife_grad/analysis/ -> data/config
                Path("data/config/cost_of_living.json"),  # Relative to CWD
            ]

            for path in potential_paths:
                if path.exists():
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return data.get("cost_indices", {"lincoln": 1.0})

            print("Warning: Cost of living config not found. Using defaults.")
            return {"lincoln": 1.0}

        except Exception as e:
            print(f"Error loading cost of living config: {e}")
            return {"lincoln": 1.0}

    def get_cost_index(self, location: str) -> float:
        """
        Get cost of living index for a location using comprehensive parsing.

        Args:
            location: Location string from job posting

        Returns:
            Cost of living index (Lincoln, NE = 1.0)
        """
        if not location or location.lower() in ["n/a", "not specified", "various"]:
            return 1.0

        location_lower = location.lower().strip()

        # Extract useful information from parentheticals first
        paren_match = re.search(r"\(([^)]*)\)", location_lower)
        location_from_parens = paren_match.group(1) if paren_match else ""

        # Remove full addresses but preserve city/state info
        location_clean = re.sub(
            r"\b\d+[^,]*,?\s*", "", location_lower
        )  # Remove street addresses
        location_clean = re.sub(
            r"\b(university of|college of|state university)\b", "", location_clean
        )
        location_clean = location_clean.strip()

        # Priority 1: Check parenthetical content first (often contains city, state)
        if location_from_parens:
            for city, index in self.cost_indices.items():
                if city in location_from_parens and len(city) > 3:
                    return index

        # Priority 2: Check for exact city matches in cleaned location
        for city, index in self.cost_indices.items():
            if (
                city in location_clean and len(city) > 3
            ):  # Avoid short matches like 'al'
                return index

        # Priority 3: Check for state abbreviations in parenthetical content
        if location_from_parens:
            state_match = re.search(r"\b([a-z]{2})\b", location_from_parens)
            if state_match:
                abbrev = state_match.group(1)
                if abbrev in self.state_abbrevs:
                    state_name = self.state_abbrevs[abbrev]
                    if state_name in self.cost_indices:
                        return self.cost_indices[state_name]

        # Priority 4: Check for state abbreviations in cleaned location
        state_match = re.search(r"\b([a-z]{2})\b", location_clean)
        if state_match:
            abbrev = state_match.group(1)
            if abbrev in self.state_abbrevs:
                state_name = self.state_abbrevs[abbrev]
                if state_name in self.cost_indices:
                    return self.cost_indices[state_name]

        # Priority 5: Extract state names from common patterns
        # Check both parenthetical and cleaned content
        all_parts = []
        if location_from_parens:
            all_parts.extend(re.split(r"[,\s]+", location_from_parens))
        all_parts.extend(re.split(r"[,\s]+", location_clean))

        for part in all_parts:
            part = part.strip()
            if part in self.cost_indices:
                return self.cost_indices[part]
            # Check state abbreviations in parts
            if part in self.state_abbrevs:
                state_name = self.state_abbrevs[part]
                if state_name in self.cost_indices:
                    return self.cost_indices[state_name]

        # Priority 4: Partial matches for common patterns
        for key, index in self.cost_indices.items():
            if (
                len(key) > 4 and key in location_clean
            ):  # Longer keys for better matching
                return index

        # If no match found, this is a real gap in our data that should be addressed
        # Log this for future improvement rather than defaulting
        print(
            f"Warning: No cost of living data found for location: '{location}' (cleaned: '{location_clean}')"
        )

        # Return US average as best estimate (not Lincoln baseline)
        return 1.05  # Slightly above Lincoln as conservative estimate

    def adjust_salary(self, salary_str: str, location: str) -> Tuple[float, float]:
        """
        Adjust salary to Lincoln, NE equivalent.

        Args:
            salary_str: Salary string from job posting
            location: Location string

        Returns:
            Tuple of (adjusted_salary, cost_index)
        """
        cost_index = self.get_cost_index(location)

        # Extract numeric salary value
        salary_value = self._extract_salary_value(salary_str)

        if salary_value > 0:
            adjusted_salary = salary_value / cost_index
            return adjusted_salary, cost_index

        return 0.0, cost_index

    def _extract_salary_value(self, salary_str: str) -> float:
        """Extract numeric value from salary string with comprehensive parsing."""
        if not salary_str:
            return 0.0

        salary_lower = salary_str.lower()

        # Return 0 for explicitly non-numeric salaries
        if any(
            phrase in salary_lower
            for phrase in [
                "commensurate",
                "negotiable",
                "competitive",
                "none",
                "n/a",
                "depends on",
                "varies",
                "tbd",
                "to be determined",
            ]
        ):
            return 0.0

        # Find all monetary amounts in the string
        # Match patterns like $25,000, $25000, 25,000, 25000, 25.5k, etc.
        money_patterns = [
            r"\$?(\d{1,3}(?:,\d{3})+(?:\.\d+)?)",  # $25,000 or 25,000
            r"\$?(\d{4,6}(?:\.\d+)?)",  # $25000 or 25000
            r"(\d{1,3}(?:\.\d+)?)[kK]",  # 25k or 25.5k
            r"(\d{1,3}(?:,\d{3})*)\s*(?:per|/)?\s*(?:year|annual)",  # 25,000 per year
            r"(\d{1,3}(?:,\d{3})*)\s*(?:per|/)?\s*(?:month)",  # 2,500 per month
        ]

        amounts = []
        for pattern in money_patterns:
            matches = re.findall(pattern, salary_str, re.IGNORECASE)
            for match in matches:
                try:
                    # Clean and convert
                    clean_num = match.replace(",", "")

                    # Handle 'k' suffix
                    if "k" in salary_lower and clean_num in salary_str.lower():
                        value = float(clean_num) * 1000
                    else:
                        value = float(clean_num)

                    # Convert monthly to annual if detected
                    if "month" in salary_lower and value > 100:
                        value *= 12

                    # Only consider reasonable salary ranges
                    if 1000 <= value <= 200000:  # Reasonable academic salary range
                        amounts.append(value)

                except (ValueError, TypeError):
                    continue

        if not amounts:
            return 0.0

        # Handle salary ranges (take the lower value for conservative estimate)
        if len(amounts) >= 2:
            # Look for range indicators
            if any(word in salary_lower for word in ["to", "-", "between", "up to"]):
                return min(amounts)  # Conservative estimate

        # Return the most reasonable amount (prefer amounts > 10k for annual salaries)
        reasonable_amounts = [amt for amt in amounts if amt >= 10000]
        if reasonable_amounts:
            return max(reasonable_amounts)  # Likely the annual salary

        return max(amounts) if amounts else 0.0


class HistoricalDataManager:
    """Manage historical job data with deduplication."""

    def __init__(self, data_dir: Path = Path("data")):
        self.data_dir = data_dir
        self.historical_file = data_dir / "historical_positions.json"
        self.archive_dir = data_dir / "archive"
        self.archive_dir.mkdir(exist_ok=True)

    def load_historical_data(self) -> List[Dict]:
        """Load existing historical data."""
        if self.historical_file.exists():
            with open(self.historical_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Handle both old format (list) and new format (dict with positions key)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "positions" in data:
                    return data["positions"]
                else:
                    return []
        return []

    def generate_position_id(self, position: Dict) -> str:
        """Generate unique ID for position based on key fields."""
        # Use title + organization + location for uniqueness
        key_text = f"{position.get('title', '')}-{position.get('organization', '')}-{position.get('location', '')}"
        # Simple hash for ID
        return str(hash(key_text.lower().strip()))

    def merge_positions(self, new_positions: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        Merge new positions with historical data.

        Args:
            new_positions: List of new job positions

        Returns:
            Tuple of (updated_historical_data, merge_stats)
        """
        historical_data = self.load_historical_data()
        existing_ids = {
            pos.get("position_id") for pos in historical_data if pos.get("position_id")
        }

        new_count = 0
        updated_count = 0

        current_date = datetime.now().isoformat()

        for new_pos in new_positions:
            pos_id = self.generate_position_id(new_pos)
            new_pos["position_id"] = pos_id

            if pos_id in existing_ids:
                # Update existing position
                for i, hist_pos in enumerate(historical_data):
                    if hist_pos.get("position_id") == pos_id:
                        # Update last_updated, preserve first_seen
                        new_pos["first_seen"] = hist_pos.get("first_seen", current_date)
                        new_pos["last_updated"] = current_date
                        historical_data[i] = new_pos
                        updated_count += 1
                        break
            else:
                # Add new position
                new_pos["first_seen"] = current_date
                new_pos["last_updated"] = current_date
                historical_data.append(new_pos)
                new_count += 1
                existing_ids.add(pos_id)

        merge_stats = {
            "new_positions": new_count,
            "updated_positions": updated_count,
            "total_positions": len(historical_data),
            "merge_date": current_date,
        }

        return historical_data, merge_stats

    def save_historical_data(self, data: List[Dict], backup: bool = True) -> None:
        """Save historical data with optional backup."""
        if backup and self.historical_file.exists():
            # Create backup
            backup_file = (
                self.archive_dir
                / f"historical_positions_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(self.historical_file, "r") as src, open(backup_file, "w") as dst:
                dst.write(src.read())

        # Save updated data
        with open(self.historical_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class EnhancedAnalyzer:
    """Main enhanced analysis coordinator."""

    def __init__(self):
        self.grad_detector = GraduatePositionDetector()
        self.discipline_classifier = DisciplineClassifier()
        self.cost_adjuster = CostOfLivingAdjuster()
        self.historical_manager = HistoricalDataManager()

    def analyze_positions(self, positions_data: List[Dict]) -> Dict:
        """
        Perform comprehensive analysis on job positions.

        Args:
            positions_data: Raw job position data

        Returns:
            Enhanced analysis results
        """
        # Convert to enhanced position objects
        enhanced_positions = []

        for pos_data in positions_data:
            # Handle missing description field for backward compatibility
            if "description" not in pos_data:
                pos_data["description"] = ""

            # Create a cleaned position dict with only JobPosition fields
            cleaned_pos_data = {}
            job_position_fields = {
                "title",
                "organization",
                "location",
                "salary",
                "starting_date",
                "published_date",
                "tags",
                "description",
                "discipline_primary",
                "discipline_secondary",
                "salary_lincoln_adjusted",
                "cost_of_living_index",
                "geographic_region",
                "is_graduate_position",
                "position_type",
                "grad_confidence",
                "first_seen",
                "last_updated",
                "scraped_at",
                "scrape_run_id",
                "scraper_version",
            }

            for field in job_position_fields:
                if field in pos_data:
                    cleaned_pos_data[field] = pos_data[field]
                elif field == "description":
                    cleaned_pos_data[field] = ""
                elif field in [
                    "salary_lincoln_adjusted",
                    "cost_of_living_index",
                    "grad_confidence",
                ]:
                    cleaned_pos_data[field] = 0.0
                elif field in ["is_graduate_position"]:
                    cleaned_pos_data[field] = False
                else:
                    cleaned_pos_data[field] = ""

            # Ensure scrape metadata is captured
            if not cleaned_pos_data.get("scraped_at"):
                cleaned_pos_data["scraped_at"] = datetime.now().isoformat()
            if not cleaned_pos_data.get("scrape_run_id"):
                cleaned_pos_data[
                    "scrape_run_id"
                ] = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if not cleaned_pos_data.get("scraper_version"):
                cleaned_pos_data["scraper_version"] = "enhanced_analysis_v1.0"

            position = JobPosition(**cleaned_pos_data)

            # Detect if this is truly a graduate position
            (
                is_grad,
                position_type,
                confidence,
            ) = self.grad_detector.is_graduate_position(position)
            position.is_graduate_position = is_grad
            position.position_type = position_type
            position.grad_confidence = confidence

            # Only classify discipline for confirmed graduate positions
            if is_grad:
                primary, secondary = self.discipline_classifier.classify_position(
                    position
                )
                position.discipline_primary = primary
                position.discipline_secondary = secondary
            else:
                position.discipline_primary = "Non-Graduate"
                position.discipline_secondary = ""

            # Adjust salary for cost of living
            adjusted_salary, cost_index = self.cost_adjuster.adjust_salary(
                position.salary, position.location
            )
            position.salary_lincoln_adjusted = adjusted_salary
            position.cost_of_living_index = cost_index

            # Add geographic region
            position.geographic_region = self._determine_region(position.location)

            enhanced_positions.append(position)

        # Merge with historical data
        position_dicts = [pos.to_dict() for pos in enhanced_positions]
        historical_data, merge_stats = self.historical_manager.merge_positions(
            position_dicts
        )

        # Save updated historical data
        self.historical_manager.save_historical_data(historical_data)

        # Generate comprehensive analytics
        analytics = self._generate_analytics(historical_data, merge_stats)

        return analytics

    def _determine_region(self, location: str) -> str:
        """Determine geographic region from location string."""
        if not location:
            return "Unknown"

        location_lower = location.lower()

        # Regional mapping (simplified)
        regions = {
            "Northeast": [
                "maine",
                "new hampshire",
                "vermont",
                "massachusetts",
                "rhode island",
                "connecticut",
                "new york",
                "new jersey",
                "pennsylvania",
            ],
            "Southeast": [
                "delaware",
                "maryland",
                "virginia",
                "west virginia",
                "kentucky",
                "tennessee",
                "north carolina",
                "south carolina",
                "georgia",
                "florida",
                "alabama",
                "mississippi",
                "arkansas",
                "louisiana",
            ],
            "Midwest": [
                "ohio",
                "michigan",
                "indiana",
                "wisconsin",
                "illinois",
                "minnesota",
                "iowa",
                "missouri",
                "north dakota",
                "south dakota",
                "nebraska",
                "kansas",
            ],
            "Southwest": ["texas", "oklahoma", "new mexico", "arizona"],
            "West": [
                "montana",
                "wyoming",
                "colorado",
                "utah",
                "idaho",
                "washington",
                "oregon",
                "california",
                "nevada",
                "alaska",
                "hawaii",
            ],
            "Remote/Multiple": ["remote", "multiple", "various", "national"],
        }

        for region, states in regions.items():
            if any(state in location_lower for state in states):
                return region

        # Check for international
        if any(
            country in location_lower
            for country in ["canada", "mexico", "international"]
        ):
            return "International"

        return "Other"

    def _generate_analytics(
        self, historical_data: List[Dict], merge_stats: Dict
    ) -> Dict:
        """Generate comprehensive analytics from historical data."""
        total_positions = len(historical_data)

        # Filter to only graduate positions for discipline analysis
        grad_positions = [
            pos for pos in historical_data if pos.get("is_graduate_position", False)
        ]

        # Discipline analysis (graduate positions only)
        disciplines = Counter(
            pos.get("discipline_primary", "Other") for pos in grad_positions
        )

        # Position type analysis
        position_types = Counter(
            pos.get("position_type", "Unknown") for pos in historical_data
        )

        # Graduate position confidence analysis
        high_confidence_grad = len(
            [pos for pos in historical_data if pos.get("grad_confidence", 0) > 0.7]
        )

        # Geographic analysis (all positions)
        regions = Counter(
            pos.get("geographic_region", "Unknown") for pos in historical_data
        )

        # Salary analysis (Lincoln-adjusted, graduate positions only)
        salaries = [
            pos.get("salary_lincoln_adjusted", 0)
            for pos in grad_positions
            if pos.get("salary_lincoln_adjusted", 0) > 0
        ]

        salary_stats = {}
        if salaries:
            salary_stats = {
                "mean": np.mean(salaries)
                if HAS_SKLEARN
                else sum(salaries) / len(salaries),
                "median": np.median(salaries)
                if HAS_SKLEARN
                else sorted(salaries)[len(salaries) // 2],
                "min": min(salaries),
                "max": max(salaries),
                "count": len(salaries),
            }

        # Temporal analysis
        temporal_data = self._analyze_temporal_trends(historical_data)

        return {
            "total_positions": total_positions,
            "graduate_positions": len(grad_positions),
            "non_graduate_positions": total_positions - len(grad_positions),
            "high_confidence_graduate": high_confidence_grad,
            "merge_stats": merge_stats,
            "disciplines": dict(disciplines),
            "position_types": dict(position_types),
            "geographic_regions": dict(regions),
            "salary_analysis_lincoln_adjusted": salary_stats,
            "temporal_trends": temporal_data,
            "last_updated": datetime.now().isoformat(),
        }

    def _analyze_temporal_trends(self, historical_data: List[Dict]) -> Dict:
        """Analyze temporal trends in job postings."""
        # Group by published month/year
        monthly_counts: Dict[str, int] = defaultdict(int)

        for pos in historical_data:
            pub_date = pos.get("published_date", "")
            if pub_date:
                try:
                    # Parse date and extract year-month
                    if "/" in pub_date:  # MM/DD/YYYY format
                        month, day, year = pub_date.split("/")
                        year_month = f"{year}-{month.zfill(2)}"
                        monthly_counts[year_month] += 1
                except (ValueError, AttributeError, IndexError):
                    continue

        return dict(monthly_counts)


def main():
    """Main function to run enhanced analysis."""
    # Load current job data
    data_file = Path("data/processed/verified_graduate_assistantships.json")
    if not data_file.exists():
        print("No verified graduate assistantships data found. Run the scraper first.")
        return

    with open(data_file, "r", encoding="utf-8") as f:
        current_positions = json.load(f)

    # Run enhanced analysis
    analyzer = EnhancedAnalyzer()
    results = analyzer.analyze_positions(current_positions)

    # Save enhanced results
    output_file = Path("data/processed/enhanced_analysis.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Print summary
    print("Enhanced analysis complete!")
    print(f"Total positions analyzed: {results['total_positions']}")
    print(
        f"Graduate positions: {results['graduate_positions']} ({results['graduate_positions']/results['total_positions']*100:.1f}%)"
    )
    print(f"Non-graduate positions: {results['non_graduate_positions']}")
    print(f"High confidence graduate: {results['high_confidence_graduate']}")
    print(f"New positions: {results['merge_stats']['new_positions']}")
    print(f"Updated positions: {results['merge_stats']['updated_positions']}")
    print(
        f"Top disciplines (grad only): {dict(list(Counter(results['disciplines']).most_common(5)))}"
    )
    print(
        f"Position types: {dict(list(Counter(results['position_types']).most_common(5)))}"
    )
    print(
        f"Geographic distribution: {dict(list(Counter(results['geographic_regions']).most_common(5)))}"
    )

    if results["salary_analysis_lincoln_adjusted"]:
        sal_stats = results["salary_analysis_lincoln_adjusted"]
        print(
            f"Salary stats (grad positions, Lincoln-adjusted): Mean=${sal_stats['mean']:.0f}, Median=${sal_stats['median']:.0f}"
        )


if __name__ == "__main__":
    main()
