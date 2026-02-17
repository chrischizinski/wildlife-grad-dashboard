"""
Enhanced analysis module for wildlife job positions.

This module provides advanced analytical capabilities including:
- Smart discipline classification using NLP
- Cost of living adjustments to Lincoln, NE
- Historical data management and deduplication
- Geographic clustering and insights
"""

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

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
                "research assistant",
                "teaching assistant",
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

    def is_graduate_position(self, position: "JobPosition") -> Tuple[bool, str, float]:
        """
        Determine if position is a graduate assistantship/fellowship.

        Returns:
            Tuple of (is_graduate, classification_type, confidence_score)
        """
        # Combine all text fields for analysis, including description
        text_content = f"{position.title} {position.tags} {position.organization} {position.description}".lower()

        # Calculate scores
        grad_score = 0
        exclusion_score = 0
        classification_type = "unknown"

        # Check for graduate indicators
        for category, keywords in self.grad_indicators.items():
            matches = sum(1 for keyword in keywords if keyword in text_content)
            if matches > 0:
                grad_score += matches * 2  # Weight graduate indicators heavily
                if category == "assistantship":
                    classification_type = "Graduate Assistantship"
                elif category == "fellowship":
                    classification_type = "Fellowship"
                elif category == "degree_pursuit" and classification_type == "unknown":
                    classification_type = "Graduate Position"

        # Check for exclusion indicators
        for category, keywords in self.exclusion_indicators.items():
            matches = sum(1 for keyword in keywords if keyword in text_content)
            if matches > 0:
                exclusion_score += matches * 3  # Weight exclusions very heavily

        # Additional context clues
        if any(
            term in text_content for term in ["PhD", "phd", "doctoral", "doctorate"]
        ):
            grad_score += 2
            if classification_type == "unknown":
                classification_type = "PhD Position"

        if any(
            term in text_content
            for term in ["masters", "master's", "ms degree", "ms position"]
        ):
            grad_score += 2
            if classification_type == "unknown":
                classification_type = "Masters Position"

        # Calculate confidence
        total_score = grad_score - exclusion_score
        confidence = min(max(total_score / 10.0, 0.0), 1.0)  # Normalize to 0-1

        # Enhanced decision logic - prioritize confidence and explicit patterns
        # Check for explicit graduate patterns that should always classify as graduate
        explicit_graduate_patterns = [
            r"graduate\s+research\s+assistantship",
            r"(ms|m\.s\.|masters?)\s+(research\s+)?assistantship",
            r"(phd|ph\.d\.)\s+(research\s+)?assistantship",
            r"graduate\s+research\s+associate",
            r"doctoral\s+(student|candidate|research|assistantship)",
            r"(phd|ph\.d\.)\s+(student|candidate|position)",
            r"(ms|m\.s\.)\s+(student|candidate|position)",
            r"thesis\s+research",
            r"dissertation\s+research",
        ]

        has_explicit_pattern = any(
            re.search(pattern, text_content, re.IGNORECASE)
            for pattern in explicit_graduate_patterns
        )

        # Decision logic: prioritize high confidence and explicit patterns
        is_graduate = (
            # High confidence threshold (covers most legitimate cases)
            confidence >= 0.7
            or
            # OR has explicit graduate language
            has_explicit_pattern
            or
            # OR traditional scoring with more lenient threshold
            (total_score > 0 and grad_score >= 2 and exclusion_score < grad_score * 2)
        )

        if not is_graduate and classification_type == "unknown":
            classification_type = "Professional/Other"

        return is_graduate, classification_type, confidence


class DisciplineClassifier:
    """Smart discipline classification using your specific categories."""

    def __init__(self):
        # Consolidated discipline categories - exactly 5 categories as requested
        # Consolidated to 6 main disciplines for clarity
        self.discipline_keywords = {
            "Fisheries": [
                # Core fisheries and aquatic terms
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
                "fishing",
                "aquaculture",
                "hatchery",
                "spawning",
                "fish population",
                "angling",
                "fisheries management",
                "fish conservation",
                "fish habitat",
                "fish ecology",
                "commercial fishing",
                "recreational fishing",
                "fish stock",
                "fishery science",
                "aquatic ecology",
                "fish biology",
                "ichthyology",
                "fisheries biology",
                "water quality",
                "aquatic systems",
                "fish communities",
                "fish assessment",
                "marine science",
                "oceanography",
                "coastal",
            ],
            "Wildlife": [
                # Wildlife, conservation, and natural resources
                "wildlife",
                "mammal",
                "bird",
                "avian",
                "carnivore",
                "ungulate",
                "deer",
                "elk",
                "bear",
                "wolf",
                "predator",
                "prey",
                "habitat",
                "migration",
                "behavior",
                "population dynamics",
                "demography",
                "survival",
                "mortality",
                "recruitment",
                "wildlife management",
                "wildlife conservation",
                "conservation biology",
                "endangered",
                "threatened",
                "recovery",
                "restoration",
                "protected areas",
                "reserve",
                "biodiversity",
                "extinction",
                "reintroduction",
                "captive breeding",
                "translocation",
                "corridor",
                "fragmentation",
                "species conservation",
                "habitat management",
                "wildlife ecology",
                "animal behavior",
                "ornithology",
                "mammalogy",
                "herpetology",
                "entomology",
                "taxonomy",
                "wildlife biology",
                # Include old categories that should map to wildlife/conservation
                "conservation",
                "species",
                "animal",
                "vertebrate",
                "fauna",
            ],
            "Human Dimensions": [
                # Social science and human aspects
                "human dimensions",
                "social",
                "stakeholder",
                "public",
                "attitude",
                "perception",
                "conflict",
                "coexistence",
                "hunting",
                "recreation",
                "tourism",
                "economics",
                "policy",
                "management",
                "governance",
                "participation",
                "sociology",
                "anthropology",
                "psychology",
                "human-wildlife conflict",
                "human behavior",
                "community engagement",
                "public participation",
                "social science",
                "environmental justice",
                "traditional knowledge",
                "cultural values",
                "stakeholder engagement",
                "environmental communication",
                "outreach",
                "education",
                "interpretation",
                "visitor studies",
                "recreation management",
                "survey",
                "interview",
                "focus group",
                "questionnaire",
                "public opinion",
            ],
            "Environmental Science": [
                # Broad environmental and ecological science
                "environmental science",
                "ecosystem",
                "ecological",
                "community",
                "food web",
                "trophic",
                "nutrient",
                "carbon",
                "nitrogen",
                "primary productivity",
                "succession",
                "disturbance",
                "climate change",
                "global warming",
                "phenology",
                "environmental",
                "ecology",
                "ecosystem services",
                "landscape ecology",
                "restoration ecology",
                "pollution",
                "contamination",
                "toxicology",
                "environmental chemistry",
                "environmental monitoring",
                "air quality",
                "soil science",
                "hydrology",
                "watershed",
                "wetlands",
                "forest ecology",
                "grassland ecology",
                "desert ecology",
                "alpine ecology",
                "urban ecology",
                "fire ecology",
                "invasive species",
                "plant ecology",
                "vegetation",
                "remote sensing",
                "gis",
                "spatial analysis",
                "modeling",
                "statistics",
                # Include quantitative and analytical terms
                "statistical",
                "biometrics",
                "population model",
                "occupancy",
                "abundance",
                "density",
                "mark-recapture",
                "distance sampling",
                "bayesian",
                "machine learning",
                # Include genetics and molecular work
                "genetics",
                "genomics",
                "dna",
                "molecular",
                "phylogeny",
                "population genetics",
                "landscape genetics",
                "conservation genetics",
                "adaptation",
                "gene flow",
                # Include ecotoxicology
                "ecotoxicology",
                "contaminant",
                "heavy metal",
                "pesticide",
                "bioaccumulation",
            ],
            "Forestry": [
                # Forestry and silviculture terms
                "forestry",
                "forest",
                "silviculture",
                "timber",
                "logging",
                "tree",
                "wood",
                "lumber",
                "forest management",
                "forest ecology",
                "forest fire",
                "wildfire",
                "prescribed burn",
                "forest health",
                "forest stand",
                "canopy",
                "understory",
                "regeneration",
                "plantation",
                "agroforestry",
                "urban forestry",
                "arborist",
                "dendrology",
                "forest carbon",
                "forest products",
                "sustainable forestry",
                "forest policy",
                "forest economics",
                "forest inventory",
                "forest restoration",
            ],
        }

        if HAS_SKLEARN:
            self.vectorizer = TfidfVectorizer(max_features=1000, stop_words="english")
            self.is_trained = False

    def classify_position(self, position: JobPosition) -> Tuple[str, str]:
        """
        Classify a position into primary and secondary disciplines.

        Args:
            position: JobPosition object

        Returns:
            Tuple of (primary_discipline, secondary_discipline)
        """
        # Combine title, tags, organization, and description for comprehensive analysis
        text_content = f"{position.title} {position.tags} {position.organization} {position.description}".lower()

        # Always use ML classification when available, regardless of text length
        if HAS_SKLEARN:
            return self._ml_classify(text_content)
        else:
            # Only use keyword classification when ML libraries are unavailable
            return self._keyword_classify(text_content)

    def _keyword_classify(self, text: str) -> Tuple[str, str]:
        """Keyword-based classification fallback."""
        scores = {}

        for discipline, keywords in self.discipline_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[discipline] = score

        if not scores:
            return "Other", ""

        # Sort by score and return top 2
        sorted_disciplines = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_disciplines[0][0]
        secondary = sorted_disciplines[1][0] if len(sorted_disciplines) > 1 else ""

        return primary, secondary

    def _ml_classify(self, text: str) -> Tuple[str, str]:
        """Machine learning-based classification using TF-IDF and semantic similarity."""

        # Create training corpus from discipline keywords
        discipline_texts = []
        discipline_labels = []

        for discipline, keywords in self.discipline_keywords.items():
            # Create representative text for each discipline
            discipline_text = " ".join(keywords)
            discipline_texts.append(discipline_text)
            discipline_labels.append(discipline)

        # Add the job text
        all_texts = discipline_texts + [text]

        # Vectorize using TF-IDF
        tfidf_matrix = self.vectorizer.fit_transform(all_texts)

        # Calculate cosine similarity between job text and each discipline
        job_vector = tfidf_matrix[-1]  # Last vector is the job text
        discipline_vectors = tfidf_matrix[:-1]  # All except the last

        similarities = cosine_similarity(job_vector, discipline_vectors).flatten()

        # Get top 2 disciplines by similarity
        top_indices = np.argsort(similarities)[::-1][:2]

        primary_discipline = discipline_labels[top_indices[0]]
        secondary_discipline = (
            discipline_labels[top_indices[1]]
            if len(top_indices) > 1 and similarities[top_indices[1]] > 0.1
            else ""
        )

        # Fallback to keyword-based only if similarity is very low
        if similarities[top_indices[0]] < 0.05:
            return self._keyword_classify(text)

        return primary_discipline, secondary_discipline


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
                    with open(path, 'r', encoding='utf-8') as f:
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
