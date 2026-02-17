"""
Unit tests for the wildlife job scraper.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pandas as pd
import pytest
from pydantic import ValidationError
from selenium.webdriver.common.by import By

from wildlife_job_scraper import (
    ScraperConfig,
    JobListing,
    WildlifeJobScraper
)


class TestScraperConfig:
    """Test the ScraperConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ScraperConfig()
        
        assert config.base_url == "https://jobs.rwfm.tamu.edu/search/"
        assert config.keywords == "(Master) OR (PhD) OR (Graduate)"
        assert config.page_size == 50
        assert config.headless is True
        assert config.timeout == 20
        
    def test_config_with_custom_values(self):
        """Test configuration with custom values."""
        config = ScraperConfig(
            base_url="https://example.com",
            keywords="custom keywords",
            page_size=25,
            headless=False
        )
        
        assert config.base_url == "https://example.com"
        assert config.keywords == "custom keywords"
        assert config.page_size == 25
        assert config.headless is False
        
    def test_output_directory_creation(self):
        """Test that output directory is created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_output"
            config = ScraperConfig(output_dir=output_path)
            
            assert output_path.exists()
            assert output_path.is_dir()


class TestJobListing:
    """Test the JobListing pydantic model."""
    
    def test_valid_job_listing(self):
        """Test creating a valid job listing."""
        job = JobListing(
            title="Graduate Research Assistant",
            organization="University of Texas",
            location="Austin, TX",
            salary="$25,000/year",
            starting_date="Fall 2024",
            published_date="2024-01-15",
            tags="Research, Wildlife"
        )
        
        assert job.title == "Graduate Research Assistant"
        assert job.organization == "University of Texas"
        assert job.location == "Austin, TX"
        
    def test_job_listing_with_defaults(self):
        """Test job listing with default values."""
        job = JobListing(title="Test Position")
        
        assert job.title == "Test Position"
        assert job.organization == "N/A"
        assert job.location == "N/A"
        assert job.salary == "N/A"
        
    def test_empty_title_validation(self):
        """Test that empty title raises validation error."""
        with pytest.raises(ValidationError):
            JobListing(title="")
            
        with pytest.raises(ValidationError):
            JobListing(title="   ")
            
    def test_title_whitespace_stripping(self):
        """Test that title whitespace is stripped."""
        job = JobListing(title="  Test Position  ")
        assert job.title == "Test Position"


class TestWildlifeJobScraper:
    """Test the main scraper class."""
    
    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield ScraperConfig(output_dir=Path(temp_dir))
    
    @pytest.fixture
    def scraper(self, config):
        """Create a scraper instance."""
        return WildlifeJobScraper(config)
    
    def test_scraper_initialization(self, scraper):
        """Test scraper initialization."""
        assert scraper.config is not None
        assert scraper.driver is None
        assert hasattr(scraper, 'logger')
        assert hasattr(scraper, 'ua')
        
    def test_human_pause_default_timing(self, scraper):
        """Test human pause with default timing."""
        with patch('time.sleep') as mock_sleep:
            scraper._human_pause()
            mock_sleep.assert_called_once()
            
            # Check that sleep was called with a value in expected range
            sleep_duration = mock_sleep.call_args[0][0]
            assert scraper.config.min_delay <= sleep_duration <= scraper.config.max_delay
            
    def test_human_pause_custom_timing(self, scraper):
        """Test human pause with custom timing."""
        with patch('time.sleep') as mock_sleep:
            scraper._human_pause(1.0, 2.0)
            mock_sleep.assert_called_once()
            
            sleep_duration = mock_sleep.call_args[0][0]
            assert 1.0 <= sleep_duration <= 2.0
            
    @patch('wildlife_job_scraper.webdriver.Chrome')
    @patch('wildlife_job_scraper.ChromeDriverManager')
    def test_setup_driver(self, mock_driver_manager, mock_chrome, scraper):
        """Test driver setup."""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        result = scraper.setup_driver()
        
        assert result == mock_driver
        mock_chrome.assert_called_once()
        mock_driver.execute_script.assert_called_once()
        
    def test_extract_job_data_valid(self, scraper):
        """Test extracting valid job data."""
        # Create mock job element
        mock_job_element = Mock()
        
        # Mock title element
        mock_title = Mock()
        mock_title.text = "Graduate Research Assistant"
        mock_job_element.find_element.side_effect = lambda by, value: {
            (By.TAG_NAME, "h6"): mock_title,
            (By.XPATH, ".//p"): Mock(text="University of Texas"),
            (By.XPATH, ".//div[contains(text(), 'Location')]/following-sibling::div"): Mock(text="Austin, TX"),
        }.get((by, value), Mock(text="N/A"))
        
        # Mock tags
        mock_job_element.find_elements.return_value = [
            Mock(text="Research"),
            Mock(text="Wildlife")
        ]
        
        result = scraper.extract_job_data(mock_job_element)
        
        assert result is not None
        assert result.title == "Graduate Research Assistant"
        assert result.organization == "University of Texas"
        assert result.location == "Austin, TX"
        assert "Research" in result.tags
        
    def test_extract_job_data_empty_title(self, scraper):
        """Test extracting job data with empty title."""
        mock_job_element = Mock()
        mock_title = Mock()
        mock_title.text = ""
        mock_job_element.find_element.return_value = mock_title
        
        result = scraper.extract_job_data(mock_job_element)
        
        assert result is None
        
    def test_extract_job_data_exception_handling(self, scraper):
        """Test job data extraction with exceptions."""
        mock_job_element = Mock()
        mock_job_element.find_element.side_effect = Exception("Element not found")
        
        result = scraper.extract_job_data(mock_job_element)
        
        assert result is None
        
    def test_extract_jobs_from_page(self, scraper):
        """Test extracting jobs from a page."""
        # Mock driver
        scraper.driver = Mock()
        
        # Create mock job elements
        mock_job1 = Mock()
        mock_job2 = Mock()
        scraper.driver.find_elements.return_value = [mock_job1, mock_job2]
        
        # Mock extract_job_data to return valid jobs
        valid_job = JobListing(title="Test Job")
        with patch.object(scraper, 'extract_job_data') as mock_extract:
            mock_extract.side_effect = [valid_job, None]  # One valid, one invalid
            
            result = scraper.extract_jobs_from_page()
            
            assert len(result) == 1
            assert result[0].title == "Test Job"
            
    def test_get_pagination_pages(self, scraper):
        """Test getting pagination page numbers."""
        scraper.driver = Mock()
        
        # Mock pagination links
        mock_link1 = Mock()
        mock_link1.get_attribute.return_value = "pageNumCtrl.value=2; submitListingForm(true);"
        mock_link2 = Mock()
        mock_link2.get_attribute.return_value = "pageNumCtrl.value=3; submitListingForm(true);"
        
        scraper.driver.find_elements.return_value = [mock_link1, mock_link2]
        
        result = scraper.get_pagination_pages()
        
        assert result == [2, 3]
        
    def test_get_pagination_pages_exception(self, scraper):
        """Test pagination with exception."""
        scraper.driver = Mock()
        scraper.driver.find_elements.side_effect = Exception("No pagination found")
        
        result = scraper.get_pagination_pages()
        
        assert result == []
        
    def test_save_jobs_json(self, scraper):
        """Test saving jobs to JSON file."""
        jobs = [
            JobListing(title="Job 1"),
            JobListing(title="Job 2")
        ]
        
        output_path = scraper.save_jobs_json(jobs, "test_jobs.json")
        
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            saved_data = json.load(f)
            
        assert len(saved_data) == 2
        assert saved_data[0]['title'] == "Job 1"
        assert saved_data[1]['title'] == "Job 2"
        
    def test_save_jobs_csv(self, scraper):
        """Test saving jobs to CSV file."""
        jobs = [
            JobListing(title="Job 1", organization="Org 1"),
            JobListing(title="Job 2", organization="Org 2")
        ]
        
        output_path = scraper.save_jobs_csv(jobs, "test_jobs.csv")
        
        assert output_path.exists()
        
        df = pd.read_csv(output_path)
        
        assert len(df) == 2
        assert df.iloc[0]['title'] == "Job 1"
        assert df.iloc[1]['title'] == "Job 2"
        
    @patch('wildlife_job_scraper.WildlifeJobScraper.setup_driver')
    def test_scrape_all_jobs_integration(self, mock_setup_driver, scraper):
        """Test the complete scraping workflow."""
        # Mock driver and its methods
        mock_driver = Mock()
        mock_setup_driver.return_value = mock_driver
        scraper.driver = mock_driver
        
        # Mock scraper methods
        with patch.object(scraper, 'set_page_size'), \
             patch.object(scraper, 'enter_search_keywords'), \
             patch.object(scraper, 'extract_jobs_from_page') as mock_extract, \
             patch.object(scraper, 'get_pagination_pages') as mock_pagination, \
             patch.object(scraper, 'navigate_to_page'):
            
            # Setup return values
            test_jobs = [JobListing(title="Test Job")]
            mock_extract.return_value = test_jobs
            mock_pagination.return_value = [1, 2]  # Two pages
            
            result = scraper.scrape_all_jobs()
            
            # Should have jobs from both pages
            assert len(result) == 2  # One job per page
            mock_driver.quit.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_job_listing_with_special_characters(self):
        """Test job listing with special characters."""
        job = JobListing(
            title="Spéciâl Chäracters & Symbols",
            organization="Université de Montréal",
            location="Montréal, QC"
        )
        
        assert job.title == "Spéciâl Chäracters & Symbols"
        assert job.organization == "Université de Montréal"
        
    def test_empty_job_list_save(self):
        """Test saving empty job list."""
        config = ScraperConfig()
        scraper = WildlifeJobScraper(config)
        
        # Should not raise an error
        scraper.save_jobs_json([])
        scraper.save_jobs_csv([])


if __name__ == "__main__":
    pytest.main([__file__])