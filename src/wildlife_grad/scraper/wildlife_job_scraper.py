"""
Wildlife Jobs Board Scraper

A comprehensive scraper for graduate assistantship opportunities from
the Texas A&M Wildlife and Fisheries job board.
"""

import json
import logging
import random
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from dotenv import load_dotenv
from fake_useragent import UserAgent
from pydantic import BaseModel, Field, field_validator
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# Load environment variables
load_dotenv()


@dataclass
class ScraperConfig:
    """Configuration for the wildlife job scraper."""

    base_url: str = "https://jobs.rwfm.tamu.edu/search/"
    keywords: str = "(Master) OR (PhD) OR (Graduate) OR (Assistantship) OR (Fellowship)"
    date_filter: str = (
        "Last7Days"  # Options: Anytime, Last30Days, Last14Days, Last7Days, Last48Hours
    )
    output_dir: Path = Path("data/raw")
    log_file: str = "scrape_jobs.log"
    page_size: int = 50
    min_delay: float = 2.0
    max_delay: float = 5.0
    timeout: int = 20
    headless: bool = True
    comprehensive_mode: bool = False  # Set to True for initial comprehensive scrape

    def __post_init__(self):
        """Create output directory if it doesn't exist."""
        self.output_dir.mkdir(exist_ok=True)

    def set_comprehensive_mode(self):
        """Set configuration for comprehensive scraping (all data)."""
        self.comprehensive_mode = True
        self.date_filter = "Anytime"
        print("Set to comprehensive mode: will scrape all available positions")

    def set_incremental_mode(self):
        """Set configuration for incremental scraping (last week only)."""
        self.comprehensive_mode = False
        self.date_filter = "Last7Days"
        print("Set to incremental mode: will scrape last 7 days only")


class JobListing(BaseModel):
    """Enhanced data model for a job listing with detailed content."""

    title: str = Field(..., min_length=1, description="Job title")
    organization: str = Field(default="N/A", description="Hiring organization")
    location: str = Field(default="N/A", description="Job location")
    salary: str = Field(default="N/A", description="Salary information")
    starting_date: str = Field(default="N/A", description="Position start date")
    published_date: str = Field(default="N/A", description="Job posting date")
    tags: str = Field(default="N/A", description="Job tags/categories")

    # Enhanced fields for detailed analysis
    url: str = Field(default="", description="Job posting URL")
    description: str = Field(default="", description="Full job description")
    requirements: str = Field(default="", description="Position requirements")
    project_details: str = Field(default="", description="Research project details")
    contact_info: str = Field(default="", description="Contact information")
    application_deadline: str = Field(default="N/A", description="Application deadline")

    # Classification fields
    is_graduate_position: bool = Field(
        default=False, description="True graduate assistantship"
    )
    grad_confidence: float = Field(default=0.0, description="Confidence score (0-1)")
    position_type: str = Field(
        default="Unknown", description="Professional/Graduate/Technician"
    )

    # Discipline classification
    discipline: str = Field(
        default="Unknown", description="Primary discipline category"
    )
    discipline_confidence: float = Field(
        default=0.0, description="Discipline classification confidence"
    )
    discipline_keywords: List[str] = Field(
        default_factory=list, description="Keywords that determined discipline"
    )

    # University classification
    is_big10_university: bool = Field(
        default=False, description="Position at Big 10 university"
    )
    university_name: str = Field(default="", description="Standardized university name")

    # Scraping metadata
    scraped_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp when job was scraped",
    )
    scrape_run_id: str = Field(
        default="", description="Unique identifier for this scraping session"
    )
    scraper_version: str = Field(default="2.0", description="Version of scraper used")

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v):
        """Ensure title is not empty or just whitespace."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()


class WildlifeJobScraper:
    """Main scraper class for wildlife job listings."""

    def __init__(self, config: ScraperConfig):
        """
        Initialize the scraper with configuration.

        Args:
            config (ScraperConfig): Scraper configuration object
        """
        self.config = config
        self.driver: Optional[webdriver.Chrome] = None
        self.ua = UserAgent()
        self.scrape_run_id: str = ""  # Will be set by main() function
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging for the scraper."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(self.config.log_file),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def _human_pause(
        self, min_seconds: Optional[float] = None, max_seconds: Optional[float] = None
    ) -> None:
        """
        Pause execution to simulate human behavior.

        Args:
            min_seconds: Minimum delay time
            max_seconds: Maximum delay time
        """
        min_delay = min_seconds or self.config.min_delay
        max_delay = max_seconds or self.config.max_delay
        delay = random.uniform(min_delay, max_delay)  # nosec B311
        time.sleep(delay)

    def setup_driver(self) -> webdriver.Chrome:
        """
        Setup and configure Chrome WebDriver with anti-detection measures.

        Returns:
            webdriver.Chrome: Configured Chrome WebDriver instance
        """
        options = Options()

        # Basic configuration
        if self.config.headless:
            options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # Anti-detection measures
        options.add_argument(f"user-agent={self.ua.random}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # Setup driver service
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        # Additional anti-detection
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        self.logger.info("Chrome WebDriver initialized successfully")
        return driver

    def _wait_for_element(self, locator: tuple, timeout: Optional[int] = None) -> Any:
        """
        Wait for an element to be present and return it.

        Args:
            locator: Tuple of (By type, selector)
            timeout: Optional timeout override

        Returns:
            WebElement: The found element
        """
        wait_time = timeout or self.config.timeout
        return WebDriverWait(self.driver, wait_time).until(
            EC.presence_of_element_located(locator)
        )

    def _scroll_to_element(self, element) -> None:
        """
        Scroll to center an element in the viewport.

        Args:
            element: WebElement to scroll to
        """
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", element
        )

    def set_date_filter(self) -> None:
        """Set the date filter for job postings."""
        try:
            # Map filter names to display text
            filter_map = {
                "Anytime": "Anytime",
                "Last30Days": "Last 30 days",
                "Last14Days": "Last 14 days",
                "Last7Days": "Last 7 days",
                "Last48Hours": "Last 48 hours",
            }

            filter_text = filter_map.get(self.config.date_filter, "Last 30 days")

            # Find and click the Posted dropdown button
            posted_button = self._wait_for_element((By.ID, "Posted-button"))
            self._scroll_to_element(posted_button)
            posted_button.click()
            self._human_pause()

            # Click the desired filter option
            filter_xpath = (
                f"//a[@class='dropdown-item' and contains(text(), '{filter_text}')]"
            )
            filter_option = self._wait_for_element((By.XPATH, filter_xpath))
            filter_option.click()

            self._human_pause()
            self.logger.info(f"Set date filter to: {filter_text}")

        except Exception as e:
            self.logger.error(f"Failed to set date filter: {e}")
            raise

    def set_page_size(self) -> None:
        """Set the results page size to maximum (50 items)."""
        try:
            # Scroll to bottom to find page size dropdown
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            self._human_pause()

            dropdown = self._wait_for_element((By.XPATH, "//select[@name='PageSize']"))
            self._scroll_to_element(dropdown)

            select = Select(dropdown)
            select.select_by_visible_text(f"Show {self.config.page_size}")

            self._human_pause()
            self.logger.info(f"Set page size to {self.config.page_size}")

        except Exception as e:
            self.logger.error(f"Failed to set page size: {e}")
            raise

    def enter_search_keywords(self, keywords: Optional[str] = None) -> None:
        """
        Enter search keywords in the search box.

        Args:
            keywords: Search keywords (uses config default if None)
        """
        try:
            search_terms = keywords or self.config.keywords

            search_box = self._wait_for_element((By.ID, "keywords"))
            self._scroll_to_element(search_box)

            search_box.clear()
            search_box.send_keys(search_terms)
            self._human_pause()

            search_box.send_keys(Keys.RETURN)
            self._human_pause()

            self.logger.info(f"Entered search keywords: {search_terms}")

        except Exception as e:
            self.logger.error(f"Failed to enter keywords: {e}")
            raise

    def extract_job_data(self, job_element) -> Optional[JobListing]:
        """
        Extract job data from a single job listing element.

        Args:
            job_element: WebElement containing job information

        Returns:
            Optional[JobListing]: Parsed job data or None if invalid
        """
        try:
            # Extract title (required field)
            title_elem = job_element.find_element(By.TAG_NAME, "h6")
            title = title_elem.text.strip()

            if not title:
                return None

            # Extract job URL for detailed scraping
            job_url = ""
            try:
                # Look for onclick attribute with job detail URL
                clickable_elements = job_element.find_elements(
                    By.XPATH, ".//*[@onclick]"
                )
                for element in clickable_elements:
                    onclick = element.get_attribute("onclick") or ""
                    if "view-job/?id=" in onclick:
                        # Extract job ID from onclick: window.open('/view-job/?id=106934', '_blank')
                        import re

                        match = re.search(r"view-job/\?id=(\d+)", onclick)
                        if match:
                            job_id = match.group(1)
                            job_url = (
                                f"https://jobs.rwfm.tamu.edu/view-job/?id={job_id}"
                            )
                            break

                if not job_url:
                    # Fallback to href attribute
                    job_url = job_element.get_attribute("href") or ""
                    if job_url and not job_url.startswith("http"):
                        base_domain = "https://jobs.rwfm.tamu.edu"
                        job_url = (
                            base_domain + job_url
                            if job_url.startswith("/")
                            else base_domain + "/" + job_url
                        )
            except (AttributeError, NoSuchElementException):
                self.logger.warning(f"Could not extract URL for job: {title}")

            # Extract optional fields with fallbacks
            def safe_extract(xpath: str, default: str = "N/A") -> str:
                try:
                    elem = job_element.find_element(By.XPATH, xpath)
                    return elem.text.strip() or default
                except (
                    NoSuchElementException,
                    AttributeError,
                    StaleElementReferenceException,
                ):
                    return default

            organization = safe_extract(".//p")
            location = safe_extract(
                ".//div[contains(text(), 'Location')]/following-sibling::div"
            )
            salary = safe_extract(
                ".//div[contains(text(), 'Salary')]/following-sibling::div"
            )
            starting_date = safe_extract(
                ".//div[contains(text(), 'Starting Date')]/following-sibling::div"
            )
            published_date = safe_extract(
                ".//div[contains(text(), 'Published')]/following-sibling::div"
            )

            # Extract tags
            try:
                tag_elements = job_element.find_elements(
                    By.CSS_SELECTOR, ".badge.bg-secondary"
                )
                tags = ", ".join(
                    tag.text.strip() for tag in tag_elements if tag.text.strip()
                )
                tags = tags or "N/A"
            except (
                NoSuchElementException,
                AttributeError,
                StaleElementReferenceException,
            ):
                tags = "N/A"

            return JobListing(
                title=title,
                organization=organization,
                location=location,
                salary=salary,
                starting_date=starting_date,
                published_date=published_date,
                tags=tags,
                url=job_url,
                scrape_run_id=self.scrape_run_id,
            )

        except Exception as e:
            self.logger.warning(f"Failed to extract job data: {e}")
            return None

    def extract_detailed_job_info(self, job: JobListing) -> JobListing:
        """
        Extract detailed information from individual job page.

        Args:
            job: JobListing with basic info and URL

        Returns:
            JobListing: Enhanced with detailed information
        """
        if not job.url:
            return job

        try:
            self.logger.info(f"Extracting details for: {job.title}")

            # Navigate to individual job page
            self.driver.get(job.url)
            self._human_pause(1.0, 2.0)  # Shorter delay for individual pages

            # Extract detailed description
            description = ""
            try:
                # Try multiple common selectors for job descriptions
                desc_selectors = [
                    "div.job-description",
                    "div.position-description",
                    "div[class*='description']",
                    "div.content",
                    "div.job-details",
                    ".card-body",
                    "main .container",
                ]

                for selector in desc_selectors:
                    try:
                        desc_element = self.driver.find_element(
                            By.CSS_SELECTOR, selector
                        )
                        description = desc_element.text.strip()
                        if (
                            description and len(description) > 100
                        ):  # Ensure we got substantial content
                            break
                    except (
                        NoSuchElementException,
                        AttributeError,
                        StaleElementReferenceException,
                        TimeoutException,
                    ):
                        continue

                if not description:
                    # Fallback: get all text from main content area
                    body_element = self.driver.find_element(By.TAG_NAME, "body")
                    description = body_element.text.strip()

            except Exception as e:
                self.logger.warning(
                    f"Could not extract description for {job.title}: {e}"
                )

            # Extract requirements section
            requirements = ""
            try:
                req_keywords = [
                    "requirements",
                    "qualifications",
                    "prerequisites",
                    "education",
                    "experience",
                    "skills",
                    "must have",
                ]

                for keyword in req_keywords:
                    try:
                        req_element = self.driver.find_element(
                            By.XPATH,
                            f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]",
                        )
                        # Get the parent container or following content
                        parent = req_element.find_element(By.XPATH, "./..")
                        requirements = parent.text.strip()
                        if requirements and len(requirements) > 50:
                            break
                    except (
                        NoSuchElementException,
                        AttributeError,
                        StaleElementReferenceException,
                        TimeoutException,
                    ):
                        continue

            except Exception as e:
                self.logger.warning(
                    f"Could not extract requirements for {job.title}: {e}"
                )

            # Extract project details (research-specific content)
            project_details = ""
            try:
                project_keywords = [
                    "research",
                    "project",
                    "thesis",
                    "dissertation",
                    "study",
                    "investigation",
                    "analysis",
                    "field work",
                ]

                desc_lower = description.lower()
                for keyword in project_keywords:
                    if keyword in desc_lower:
                        # Extract sentences containing research keywords
                        import re

                        sentences = re.split(r"[.!?]+", description)
                        project_sentences = [
                            s.strip() for s in sentences if keyword in s.lower()
                        ]
                        if project_sentences:
                            project_details = ". ".join(
                                project_sentences[:3]
                            )  # First 3 relevant sentences
                            break

            except Exception as e:
                self.logger.warning(
                    f"Could not extract project details for {job.title}: {e}"
                )

            # Extract contact information
            contact_info = ""
            try:
                contact_selectors = [
                    "*[contains(text(), '@')]",  # Email addresses
                    "*[contains(text(), 'contact')]",
                    "*[contains(text(), 'Contact')]",
                    ".contact-info",
                ]

                for selector in contact_selectors:
                    try:
                        contact_element = self.driver.find_element(
                            By.CSS_SELECTOR, selector
                        )
                        contact_info = contact_element.text.strip()
                        if contact_info and "@" in contact_info:
                            break
                    except (
                        NoSuchElementException,
                        AttributeError,
                        StaleElementReferenceException,
                        TimeoutException,
                    ):
                        continue

            except Exception as e:
                self.logger.warning(
                    f"Could not extract contact info for {job.title}: {e}"
                )

            # Extract application deadline
            deadline = job.application_deadline  # Keep existing value as default
            try:
                deadline_keywords = ["deadline", "due", "apply by", "closing date"]
                desc_lower = description.lower()

                for keyword in deadline_keywords:
                    if keyword in desc_lower:
                        # Try to extract date after keyword
                        import re

                        pattern = rf"{keyword}[:\s]*([^.]*(?:\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}}|[A-Za-z]+\s+\d{{1,2}},?\s*\d{{4}})[^.]*)"
                        match = re.search(pattern, description, re.IGNORECASE)
                        if match:
                            deadline = match.group(1).strip()
                            break

            except Exception as e:
                self.logger.warning(f"Could not extract deadline for {job.title}: {e}")

            # Update job with detailed information
            job.description = description
            job.requirements = requirements
            job.project_details = project_details
            job.contact_info = contact_info
            job.application_deadline = deadline

            return job

        except Exception as e:
            self.logger.error(f"Failed to extract detailed info for {job.title}: {e}")
            return job

    def classify_graduate_position(self, job: JobListing) -> JobListing:
        """
        Classify if a position is a true graduate assistantship.

        Args:
            job: JobListing with detailed information

        Returns:
            JobListing: Enhanced with classification data
        """
        try:
            # Combine all text for analysis
            full_text = f"{job.title} {job.description} {job.requirements} {job.project_details} {job.tags}".lower()

            # Graduate position indicators (positive signals) - ENHANCED
            graduate_indicators = [
                "graduate assistantship",
                "graduate assistant",
                "graduate student",
                "master's student",
                "ms student",
                "phd student",
                "doctoral student",
                "masters",
                "master's",
                "phd",
                "ph.d.",
                "doctorate",
                "doctoral",
                "assistantship",
                "fellowship",
                "graduate",
                "grad student",
                "thesis",
                "dissertation",
                "research assistant",
                "teaching assistant",
                "graduate research",
                "graduate teaching",
                "stipend",
                "tuition waiver",
                "advisor",
                "adviser",
                "mentorship",
                "research project",
                "academic year",
                "semester",
                "graduate program",
                "grad program",
            ]

            # Non-graduate indicators (negative signals) - WILDLIFE-SPECIFIC ENHANCED
            non_graduate_indicators = [
                # General professional roles
                "professional position",
                "full-time employee",
                "staff position",
                "technician",
                "tech",
                "coordinator",
                "manager",
                "director",
                "volunteer",
                "intern",
                "internship",
                "apprentice",
                # Wildlife/Natural Resource specific roles
                "biologist",
                "hydrologist",
                "scientist",
                "botanist",
                "ecologist",
                "conservationist",
                "park ranger",
                "crew leader",
                "crew member",
                "habitat specialist",
                "regional coordinator",
                "liaison",
                "educator",
                "specialist",
                "officer",
                "program officer",
                "programme officer",
                "project manager",
                "production manager",
                "seasonal",
                "human resource officer",
                "hr officer",
                # Academic non-assistantship roles
                "continuing education",
                "certification",
                "workshop",
                "training program",
                "degree program",
                "bachelor",
                "undergraduate",
                "post-doc",
                "postdoc",
                "visiting scholar",
                "faculty",
                "professor",
                "lecturer",
            ]

            # Research project indicators
            research_indicators = [
                "research",
                "study",
                "investigation",
                "analysis",
                "field work",
                "data collection",
                "sampling",
                "monitoring",
                "experiment",
                "publication",
                "conference",
                "methodology",
                "hypothesis",
            ]

            # Calculate scores with enhanced weighting
            grad_score = sum(
                1 for indicator in graduate_indicators if indicator in full_text
            )
            non_grad_score = sum(
                1 for indicator in non_graduate_indicators if indicator in full_text
            )
            research_score = sum(
                1 for indicator in research_indicators if indicator in full_text
            )

            # Check for key strong indicators
            key_graduate_terms = [
                "masters",
                "master's",
                "phd",
                "ph.d.",
                "assistantship",
                "fellowship",
            ]
            has_key_graduate = any(term in full_text for term in key_graduate_terms)

            key_professional_terms = [
                "biologist",
                "hydrologist",
                "scientist",
                "botanist",
                "technician",
                "park ranger",
                "specialist",
                "coordinator",
                "manager",
                "officer",
            ]
            has_key_professional = any(
                term in full_text for term in key_professional_terms
            )

            # Enhanced classification logic
            confidence = 0.0
            is_graduate = False
            position_type = "Unknown"

            # Priority 1: Strong key indicators override other signals
            if has_key_graduate and not has_key_professional:
                # Strong graduate keywords present, no conflicting professional terms
                position_type = "Graduate"
                confidence = min(0.95, 0.8 + (grad_score * 0.05))
                is_graduate = True

            elif has_key_professional and not has_key_graduate:
                # Strong professional keywords present, no graduate terms
                position_type = "Professional"
                confidence = min(0.9, 0.7 + (non_grad_score * 0.05))
                is_graduate = False

            elif non_grad_score >= 2:
                # Multiple non-graduate signals
                position_type = "Professional"
                confidence = min(0.9, non_grad_score * 0.3)
                is_graduate = False

            elif grad_score >= 2 and research_score >= 1:
                # Strong graduate + research signals
                total_positive = grad_score + (research_score * 0.5)
                position_type = "Graduate"
                confidence = min(0.95, total_positive * 0.2)
                is_graduate = True

            elif grad_score >= 1 and research_score >= 2:
                # Moderate graduate + strong research
                total_positive = grad_score + (research_score * 0.5)
                position_type = "Graduate"
                confidence = min(0.85, total_positive * 0.18)
                is_graduate = True

            elif any(
                term in full_text
                for term in ["technician", "tech", "volunteer", "intern"]
            ):
                # Explicit non-graduate roles
                position_type = "Technician"
                confidence = 0.8
                is_graduate = False

            elif grad_score >= 1:
                # Some graduate signals
                position_type = "Possible Graduate"
                confidence = min(0.6, grad_score * 0.25)
                is_graduate = grad_score > non_grad_score

            else:
                # Default classification
                position_type = "Unknown"
                confidence = 0.1
                is_graduate = False

            # Additional checks for edge cases
            if "student" in job.title.lower() and "research" in full_text:
                is_graduate = True
                confidence = max(confidence, 0.8)
                position_type = "Graduate"

            # Update job classification
            job.is_graduate_position = is_graduate
            job.grad_confidence = round(confidence, 3)
            job.position_type = position_type

            self.logger.info(
                f"Classified '{job.title}': {position_type} (confidence: {confidence:.3f})"
            )
            return job

        except Exception as e:
            self.logger.warning(f"Classification failed for {job.title}: {e}")
            job.is_graduate_position = False
            job.grad_confidence = 0.0
            job.position_type = "Unknown"
            return job

    def classify_discipline(self, job: JobListing) -> JobListing:
        """
        Classify the academic discipline of a position using detailed content analysis.

        Args:
            job: JobListing with detailed information

        Returns:
            JobListing: Enhanced with discipline classification
        """
        try:
            # Combine all text for analysis
            full_text = f"{job.title} {job.description} {job.requirements} {job.project_details} {job.tags}".lower()

            # Wildlife & Natural Resources discipline indicators
            wildlife_keywords = [
                # Wildlife management and ecology
                "wildlife",
                "wild animals",
                "animal ecology",
                "wildlife management",
                "wildlife conservation",
                "game species",
                "hunting",
                "wildlife habitat",
                "deer",
                "elk",
                "bear",
                "waterfowl",
                "bird",
                "avian",
                "ornithology",
                "mammal",
                "ungulate",
                "predator",
                "carnivore",
                "herbivore",
                "migration",
                "behavior",
                "animal behavior",
                "population dynamics",
                "wildlife disease",
                "wildlife health",
                "capture",
                "telemetry",
                # Habitat and ecosystem
                "habitat",
                "ecosystem",
                "biodiversity",
                "conservation biology",
                "landscape ecology",
                "habitat restoration",
                "wetland",
                "grassland",
                "forest ecology",
                "rangeland",
                "prairie",
                "savanna",
            ]

            # Fisheries & Aquatic Science indicators
            fisheries_keywords = [
                # Fish and aquatic life
                "fish",
                "fisheries",
                "aquatic",
                "marine",
                "freshwater",
                "stream",
                "river",
                "lake",
                "pond",
                "reservoir",
                "estuary",
                "coastal",
                "salmon",
                "trout",
                "bass",
                "catfish",
                "walleye",
                "pike",
                "aquaculture",
                "fish farming",
                "hatchery",
                "fish stocking",
                # Aquatic ecology
                "aquatic ecology",
                "stream ecology",
                "limnology",
                "hydrology",
                "water quality",
                "aquatic habitat",
                "fish habitat",
                "spawning",
                "fish population",
                "fish community",
                "ichthyology",
                "aquatic invertebrates",
                "plankton",
                "algae",
                "aquatic plants",
            ]

            # Natural Resource Management indicators
            natural_resources_keywords = [
                # General natural resources
                "natural resources",
                "resource management",
                "environmental management",
                "land management",
                "public lands",
                "national forest",
                "state park",
                "BLM",
                "bureau of land management",
                "forest service",
                "park service",
                # Forestry and land use
                "forestry",
                "forest management",
                "timber",
                "silviculture",
                "fire ecology",
                "prescribed fire",
                "wildfire",
                "fire management",
                "recreation",
                "outdoor recreation",
                "hunting",
                "fishing",
                "grazing",
                "livestock",
                "ranching",
                "agriculture",
                # Policy and human dimensions
                "environmental policy",
                "natural resource policy",
                "environmental law",
                "human dimensions",
                "stakeholder",
                "community engagement",
                "environmental education",
                "interpretation",
                "outreach",
            ]

            # Environmental Science (broader) indicators
            environmental_keywords = [
                # Environmental science
                "environmental science",
                "environmental studies",
                "ecology",
                "ecosystem services",
                "sustainability",
                "climate change",
                "environmental chemistry",
                "environmental toxicology",
                "environmental monitoring",
                "environmental assessment",
                # Conservation and restoration
                "conservation",
                "restoration",
                "endangered species",
                "threatened species",
                "species recovery",
                "habitat restoration",
                "ecosystem restoration",
                "invasive species",
                "native species",
                "biodiversity conservation",
                # Pollution and contamination
                "pollution",
                "contamination",
                "environmental remediation",
                "water pollution",
                "air quality",
                "soil contamination",
                "environmental health",
                "environmental impact",
            ]

            # Calculate discipline scores
            disciplines = {
                "Wildlife & Natural Resources": wildlife_keywords,
                "Fisheries & Aquatic Science": fisheries_keywords,
                "Natural Resource Management": natural_resources_keywords,
                "Environmental Science": environmental_keywords,
            }

            discipline_scores = {}
            discipline_matches = {}

            for discipline, keywords in disciplines.items():
                matches = []
                score = 0

                for keyword in keywords:
                    if keyword in full_text:
                        matches.append(keyword)
                        # Weight longer, more specific keywords higher
                        if len(keyword.split()) > 2:
                            score += 3  # Multi-word specific terms
                        elif len(keyword.split()) == 2:
                            score += 2  # Two-word terms
                        else:
                            score += 1  # Single words

                discipline_scores[discipline] = score
                discipline_matches[discipline] = matches

            # Find best discipline match
            if max(discipline_scores.values()) == 0:
                best_discipline = "Unknown"
                confidence = 0.0
                matched_keywords = []
            else:
                best_discipline = max(discipline_scores, key=discipline_scores.get)
                best_score = discipline_scores[best_discipline]
                total_possible = (
                    len(disciplines[best_discipline]) * 3
                )  # Max if all were 3-word terms
                confidence = min(
                    0.95, best_score / max(10, total_possible * 0.3)
                )  # Scale appropriately
                matched_keywords = discipline_matches[best_discipline]

            # Handle ties and overlapping disciplines
            sorted_disciplines = sorted(
                discipline_scores.items(), key=lambda x: x[1], reverse=True
            )
            if len(sorted_disciplines) >= 2:
                best_score = sorted_disciplines[0][1]
                second_score = sorted_disciplines[1][1]

                # If scores are very close, reduce confidence
                if second_score > 0 and best_score / second_score < 1.5:
                    confidence *= 0.8

                # Special handling for overlapping disciplines
                if (
                    best_discipline == "Environmental Science"
                    and second_score >= best_score * 0.7
                ):
                    # Environmental Science often overlaps - prefer more specific discipline
                    best_discipline = sorted_disciplines[1][0]
                    confidence = min(confidence, 0.8)
                    matched_keywords = discipline_matches[best_discipline]

            # Apply minimum confidence threshold
            if confidence < 0.15:
                best_discipline = "Unknown"
                confidence = 0.0
                matched_keywords = []

            # Update job with discipline classification
            job.discipline = best_discipline
            job.discipline_confidence = round(confidence, 3)
            job.discipline_keywords = matched_keywords[:5]  # Keep top 5 keywords

            self.logger.info(
                f"Discipline '{job.title}': {best_discipline} (confidence: {confidence:.3f})"
            )
            if matched_keywords:
                self.logger.debug(f"  Keywords: {', '.join(matched_keywords[:3])}")

            return job

        except Exception as e:
            self.logger.warning(
                f"Discipline classification failed for {job.title}: {e}"
            )
            job.discipline = "Unknown"
            job.discipline_confidence = 0.0
            job.discipline_keywords = []
            return job

    def classify_university(self, job: JobListing) -> JobListing:
        """
        Classify if a position is at a Big 10 university.

        Args:
            job: JobListing with organization information

        Returns:
            JobListing: Enhanced with university classification
        """
        try:
            # Big 10 universities (current conference members as of 2024)
            big10_universities = {
                # Original Big 10
                "university of illinois": "University of Illinois",
                "university of chicago": "University of Chicago",
                "university of michigan": "University of Michigan",
                "michigan state university": "Michigan State University",
                "university of minnesota": "University of Minnesota",
                "northwestern university": "Northwestern University",
                "ohio state university": "Ohio State University",
                "purdue university": "Purdue University",
                "university of wisconsin": "University of Wisconsin",
                "university of iowa": "University of Iowa",
                "indiana university": "Indiana University",
                "pennsylvania state university": "Pennsylvania State University",
                "penn state": "Pennsylvania State University",
                # Recent additions
                "university of maryland": "University of Maryland",
                "rutgers university": "Rutgers University",
                "university of nebraska": "University of Nebraska",
                "university of oregon": "University of Oregon",
                "university of washington": "University of Washington",
                "university of california": "University of California",  # UCLA, USC
                "usc": "University of Southern California",
                "ucla": "University of California, Los Angeles",
            }

            # Alternative name patterns for fuzzy matching
            alternative_patterns = {
                # Common abbreviations and variations
                "uiuc": "University of Illinois",
                "u of i": "University of Illinois",
                "illinois": "University of Illinois",
                "umich": "University of Michigan",
                "u of m": "University of Michigan",
                "michigan": "University of Michigan",
                "msu": "Michigan State University",
                "umn": "University of Minnesota",
                "minnesota": "University of Minnesota",
                "northwestern": "Northwestern University",
                "osu": "Ohio State University",
                "ohio state": "Ohio State University",
                "purdue": "Purdue University",
                "uw-madison": "University of Wisconsin",
                "wisconsin": "University of Wisconsin",
                "iowa": "University of Iowa",
                "iu": "Indiana University",
                "indiana": "Indiana University",
                "psu": "Pennsylvania State University",
                "umd": "University of Maryland",
                "maryland": "University of Maryland",
                "rutgers": "Rutgers University",
                "unl": "University of Nebraska",
                "nebraska": "University of Nebraska",
                "oregon": "University of Oregon",
                "uw-seattle": "University of Washington",
                "washington": "University of Washington",
            }

            # Combine organization name and description for analysis
            full_text = f"{job.organization} {job.description}".lower()

            # Clean up common organizational suffixes
            org_text = job.organization.lower()
            org_text = (
                org_text.replace("(state)", "")
                .replace("(federal)", "")
                .replace("(private)", "")
            )
            org_text = org_text.replace("university system", "university")
            org_text = org_text.strip()

            is_big10 = False
            university_name = ""

            # Check direct matches first
            for pattern, standard_name in big10_universities.items():
                if pattern in org_text:
                    is_big10 = True
                    university_name = standard_name
                    break

            # Check alternative patterns if no direct match
            if not is_big10:
                for pattern, standard_name in alternative_patterns.items():
                    if pattern in org_text:
                        is_big10 = True
                        university_name = standard_name
                        break

            # Special handling for ambiguous cases
            if "uw" in org_text:
                if "washington" in full_text or "seattle" in full_text:
                    is_big10 = True
                    university_name = "University of Washington"
                elif "wisconsin" in full_text or "madison" in full_text:
                    is_big10 = True
                    university_name = "University of Wisconsin"

            # Handle University of California system
            if "university of california" in org_text or "uc " in org_text:
                if any(
                    campus in full_text
                    for campus in [
                        "los angeles",
                        "ucla",
                        "berkeley",
                        "davis",
                        "san diego",
                        "irvine",
                    ]
                ):
                    is_big10 = True
                    university_name = "University of California"

            # Update job classification
            job.is_big10_university = is_big10
            job.university_name = university_name

            if is_big10:
                self.logger.info(
                    f"Big 10 university detected: {university_name} for '{job.title}'"
                )

            return job

        except Exception as e:
            self.logger.warning(
                f"University classification failed for {job.title}: {e}"
            )
            job.is_big10_university = False
            job.university_name = ""
            return job

    def extract_jobs_from_page(self) -> List[JobListing]:
        """
        Extract all job listings from the current page.

        Returns:
            List[JobListing]: List of valid job listings
        """
        jobs = []
        job_elements = self.driver.find_elements(By.CSS_SELECTOR, "a.list-group-item")

        for job_element in job_elements:
            job_data = self.extract_job_data(job_element)
            if job_data:
                jobs.append(job_data)

        self.logger.info(f"Extracted {len(jobs)} jobs from current page")
        return jobs

    def get_pagination_pages(self) -> List[int]:
        """
        Get list of available page numbers from pagination.

        Returns:
            List[int]: List of page numbers to scrape
        """
        try:
            # Use the working selector that finds onclick attributes with pageNumCtrl
            pagination_links = self.driver.find_elements(
                By.XPATH, "//a[contains(@onclick, 'pageNumCtrl.value=')]"
            )

            page_numbers = []
            max_page = 1

            for link in pagination_links:
                onclick_attr = link.get_attribute("onclick")
                if onclick_attr and "pageNumCtrl.value=" in onclick_attr:
                    try:
                        # Extract page number from onclick="pageNumCtrl.value=2; submitListingForm(true);"
                        page_num = int(
                            onclick_attr.split("pageNumCtrl.value=")[1]
                            .split(";")[0]
                            .strip()
                        )
                        page_numbers.append(page_num)
                        max_page = max(max_page, page_num)
                    except (ValueError, IndexError):
                        continue

            # If we found a "Last" page, generate all page numbers from 1 to max
            if page_numbers:
                # Generate complete page range from 1 to the highest page number found
                complete_pages = list(range(1, max_page + 1))
                self.logger.info(f"Found {max_page} total pages to scrape")
                return complete_pages
            else:
                # Fallback: try to detect total pages from results text
                try:
                    results_text = self.driver.find_element(
                        By.XPATH, "//*[contains(text(), 'of')]"
                    ).text
                    # Look for pattern like "(1 - 10 of 233)"
                    import re

                    match = re.search(r"of\s+(\d+)", results_text)
                    if match:
                        total_results = int(match.group(1))
                        pages_needed = (
                            total_results + self.config.page_size - 1
                        ) // self.config.page_size
                        self.logger.info(
                            f"Calculated {pages_needed} pages from {total_results} total results"
                        )
                        return list(range(1, pages_needed + 1))
                except (ValueError, AttributeError, IndexError):
                    pass

                self.logger.info("No pagination found, assuming single page")
                return [1]

        except Exception as e:
            self.logger.warning(f"Failed to get pagination info: {e}")
            return [1]  # Return page 1 as fallback

    def navigate_to_page(self, page_number: int) -> None:
        """
        Navigate to a specific page number.

        Args:
            page_number: Page number to navigate to
        """
        try:
            self.driver.execute_script(
                f"pageNumCtrl.value={page_number}; submitListingForm(true);"
            )

            # Wait for new results to load
            self._wait_for_element((By.CSS_SELECTOR, "a.list-group-item"))
            self._human_pause()

            self.logger.info(f"Navigated to page {page_number}")

        except Exception as e:
            self.logger.error(f"Failed to navigate to page {page_number}: {e}")
            raise

    def scrape_all_jobs(self) -> List[JobListing]:
        """
        Scrape job listings from all available pages with detailed content extraction.

        Returns:
            List[JobListing]: Complete list of enhanced job listings
        """
        try:
            self.driver = self.setup_driver()
            self.driver.get(self.config.base_url)

            # Setup initial page
            self.set_page_size()
            self.driver.execute_script("window.scrollTo(0, 0);")
            self.enter_search_keywords()

            # Apply date filter for weekly automation
            self.set_date_filter()

            # Extract jobs from first page
            all_jobs = self.extract_jobs_from_page()

            # Get pagination and scrape remaining pages
            page_numbers = self.get_pagination_pages()

            for page_num in page_numbers:
                if page_num == 1:  # Skip first page (already scraped)
                    continue

                self.navigate_to_page(page_num)
                page_jobs = self.extract_jobs_from_page()
                all_jobs.extend(page_jobs)

            self.logger.info(f"Initial extraction complete: {len(all_jobs)} jobs found")

            # Phase 2: Extract detailed information and classify positions
            enhanced_jobs = []
            for i, job in enumerate(all_jobs):
                self.logger.info(f"Processing job {i+1}/{len(all_jobs)}: {job.title}")

                try:
                    # Extract detailed information
                    enhanced_job = self.extract_detailed_job_info(job)

                    # Classify position type
                    classified_job = self.classify_graduate_position(enhanced_job)

                    # Classify discipline
                    disciplined_job = self.classify_discipline(classified_job)

                    # Classify university
                    final_job = self.classify_university(disciplined_job)

                    enhanced_jobs.append(final_job)

                    # Progress logging
                    if (i + 1) % 5 == 0:
                        grad_count = sum(
                            1 for j in enhanced_jobs if j.is_graduate_position
                        )
                        self.logger.info(
                            f"Progress: {i+1}/{len(all_jobs)} processed, {grad_count} graduate positions found"
                        )

                except Exception as e:
                    self.logger.error(f"Failed to process job {job.title}: {e}")
                    # Add job with basic info even if detailed extraction fails
                    enhanced_jobs.append(job)

            # Final summary
            total_jobs = len(enhanced_jobs)
            graduate_jobs = sum(1 for job in enhanced_jobs if job.is_graduate_position)
            high_confidence = sum(
                1 for job in enhanced_jobs if job.grad_confidence >= 0.8
            )

            self.logger.info("Scraping complete:")
            self.logger.info(f"  Total positions: {total_jobs}")
            self.logger.info(f"  Graduate assistantships: {graduate_jobs}")
            self.logger.info(f"  High confidence classifications: {high_confidence}")

            return enhanced_jobs

        except Exception as e:
            self.logger.error(f"Error during scraping: {e}")
            raise
        finally:
            if self.driver:
                self.driver.quit()

    def save_jobs_json(
        self, jobs: List[JobListing], filename: str = "graduate_assistantships.json"
    ) -> Path:
        """
        Save job listings to JSON file.

        Args:
            jobs: List of job listings to save
            filename: Output filename

        Returns:
            Path: Path to saved file
        """
        output_path = self.config.output_dir / filename

        # Convert to dictionaries for JSON serialization
        jobs_data = [job.dict() for job in jobs]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(jobs_data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Saved {len(jobs)} jobs to {output_path}")
        return output_path

    def save_jobs_csv(
        self, jobs: List[JobListing], filename: str = "graduate_assistantships.csv"
    ) -> Path:
        """
        Save job listings to CSV file.

        Args:
            jobs: List of job listings to save
            filename: Output filename

        Returns:
            Path: Path to saved file
        """
        output_path = self.config.output_dir / filename

        # Convert to DataFrame and save
        jobs_data = [job.dict() for job in jobs]
        df = pd.DataFrame(jobs_data)
        df.to_csv(output_path, index=False, encoding="utf-8")

        self.logger.info(f"Saved {len(jobs)} jobs to {output_path}")
        return output_path

    def save_graduate_positions_only(
        self, jobs: List[JobListing], min_confidence: float = 0.5
    ) -> tuple[Path, Path]:
        """
        Save only verified graduate assistantships to separate files.

        Args:
            jobs: All job listings
            min_confidence: Minimum confidence threshold for inclusion

        Returns:
            tuple[Path, Path]: Paths to graduate JSON and CSV files
        """
        # Filter to only graduate positions above confidence threshold
        graduate_jobs = [
            job
            for job in jobs
            if job.is_graduate_position and job.grad_confidence >= min_confidence
        ]

        self.logger.info(f"Filtering {len(jobs)} total positions:")
        self.logger.info(
            f"  Graduate positions (confidence >= {min_confidence}): {len(graduate_jobs)}"
        )

        # Save current graduate positions snapshot to processed directory.
        processed_dir = Path("data/processed")
        processed_dir.mkdir(exist_ok=True)
        json_path = processed_dir / "verified_graduate_assistantships.json"

        # Convert to dictionaries for JSON serialization
        jobs_data = [job.dict() for job in graduate_jobs]

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(jobs_data, f, indent=2, ensure_ascii=False)
        # Save CSV to processed directory
        csv_path = processed_dir / "verified_graduate_assistantships.csv"
        jobs_data = [job.dict() for job in graduate_jobs]
        df = pd.DataFrame(jobs_data)
        df.to_csv(csv_path, index=False, encoding="utf-8")

        # Also save classification report
        report: Dict[str, Any] = {
            "total_positions_scraped": len(jobs),
            "verified_graduate_assistantships": len(graduate_jobs),
            "confidence_threshold": min_confidence,
            "classification_breakdown": {},
            "high_confidence_positions": sum(
                1 for job in graduate_jobs if job.grad_confidence >= 0.8
            ),
        }

        # Count by position type
        for job in jobs:
            pos_type = job.position_type
            if pos_type not in report["classification_breakdown"]:
                report["classification_breakdown"][pos_type] = 0
            report["classification_breakdown"][pos_type] += 1

        report_path = processed_dir / "classification_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # Update cumulative historical graduate dataset so incremental weekly runs
        # preserve history over time instead of replacing it.
        self._update_historical_graduate_dataset(graduate_jobs)

        self.logger.info(f"Saved classification report to {report_path}")

        return json_path, csv_path

    def _update_historical_graduate_dataset(self, graduate_jobs: List[JobListing]) -> None:
        """Merge current run graduate jobs into cumulative historical file(s)."""
        historical_paths = [
            Path("data/raw/historical_positions.json"),
            Path("data/historical_positions.json"),
        ]

        now_iso = datetime.now(timezone.utc).isoformat()

        def load_rows(path: Path) -> List[Dict[str, Any]]:
            if not path.exists():
                return []
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data if isinstance(data, list) else []
            except Exception as e:
                self.logger.warning(f"Could not load historical data from {path}: {e}")
                return []

        existing_rows: List[Dict[str, Any]] = []
        for path in historical_paths:
            existing_rows.extend(load_rows(path))

        # Keep only graduate rows in history.
        existing_rows = [row for row in existing_rows if row.get("is_graduate_position", True)]

        def get_key(row: Dict[str, Any]) -> str:
            url = str(row.get("url") or "").strip().lower()
            if url:
                return f"url::{url}"
            title = str(row.get("title") or "").strip().lower()
            org = str(row.get("organization") or "").strip().lower()
            return f"title_org::{title}::{org}"

        merged: Dict[str, Dict[str, Any]] = {}
        for row in existing_rows:
            key = get_key(row)
            if key:
                merged[key] = row

        for job in graduate_jobs:
            new_row = job.dict()
            key = get_key(new_row)
            if not key:
                continue

            existing = merged.get(key)
            if existing:
                first_seen = existing.get("first_seen") or existing.get("scraped_at")
                combined = {**existing, **new_row}
                combined["first_seen"] = first_seen or new_row.get("scraped_at") or now_iso
                combined["last_updated"] = new_row.get("scraped_at") or now_iso
                merged[key] = combined
            else:
                combined = dict(new_row)
                combined["first_seen"] = combined.get("first_seen") or combined.get("scraped_at") or now_iso
                combined["last_updated"] = combined.get("last_updated") or combined.get("scraped_at") or now_iso
                merged[key] = combined

        merged_rows = list(merged.values())
        merged_rows.sort(
            key=lambda row: str(
                row.get("published_date")
                or row.get("first_seen")
                or row.get("scraped_at")
                or row.get("last_updated")
                or ""
            ),
            reverse=True,
        )

        for path in historical_paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(merged_rows, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Updated historical graduate dataset: {path} ({len(merged_rows)} rows)")


def main() -> None:
    """Main entry point for the enhanced scraper."""
    import sys

    try:
        # Generate unique run ID for this scraping session
        run_id = f"scrape_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

        config = ScraperConfig()

        # Check for command-line arguments to force comprehensive mode
        force_comprehensive = any(
            arg in ["--comprehensive", "--all-time", "--all"] for arg in sys.argv
        )

        if force_comprehensive:
            print("🔄 FORCING COMPREHENSIVE mode via command-line argument")
            print("Will scrape ALL graduate positions regardless of existing data")
            config.set_comprehensive_mode()
        else:
            # Detect if this is first run (comprehensive) or subsequent run (incremental)
            # Check if we have any existing data in the database or processed files
            has_existing_data = (
                Path("data/processed/verified_graduate_assistantships.json").exists()
                or Path("data/historical_positions.json").exists()
                or Path("data/enhanced_data.json").exists()
            )

            if has_existing_data:
                print(
                    "Existing data detected - running in INCREMENTAL mode (Last 7 days)"
                )
                config.set_incremental_mode()
            else:
                print(
                    "No existing data found - running in COMPREHENSIVE mode (All positions)"
                )
                config.set_comprehensive_mode()

        scraper = WildlifeJobScraper(config)
        scraper.scrape_run_id = run_id

        print("Starting enhanced wildlife job scraping with detailed analysis...")
        print(f"Scrape Run ID: {run_id}")
        print(
            f"Mode: {'COMPREHENSIVE' if config.comprehensive_mode else 'INCREMENTAL'}"
        )
        jobs = scraper.scrape_all_jobs()

        if jobs:
            # Save all jobs (for analysis/debugging)
            scraper.save_jobs_json(jobs, "all_positions_detailed.json")
            scraper.save_jobs_csv(jobs, "all_positions_detailed.csv")

            # Save only verified graduate assistantships
            grad_json, grad_csv = scraper.save_graduate_positions_only(
                jobs, min_confidence=0.5
            )

            # Print summary
            total_jobs = len(jobs)
            graduate_jobs = sum(1 for job in jobs if job.is_graduate_position)
            high_confidence = sum(1 for job in jobs if job.grad_confidence >= 0.8)

            print("\n=== SCRAPING COMPLETE ===")
            print(f"Total positions found: {total_jobs}")
            print(f"Graduate assistantships identified: {graduate_jobs}")
            print(f"High confidence classifications: {high_confidence}")
            print(f"Graduate positions saved to: {grad_json.name}")
            print("Classification report saved to: classification_report.json")

            # Show position type breakdown
            position_types: Dict[str, int] = {}
            for job in jobs:
                pos_type = job.position_type
                position_types[pos_type] = position_types.get(pos_type, 0) + 1

            print("\nPosition Type Breakdown:")
            for pos_type, count in sorted(
                position_types.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {pos_type}: {count}")

        else:
            print("No jobs found")

    except Exception as e:
        logging.error(f"Scraping failed: {e}")
        raise


if __name__ == "__main__":
    main()
