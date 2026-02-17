"""
Tests for enhanced analysis functionality.
"""

import json
import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from scripts.enhanced_analysis import (
    DisciplineClassifier,
    CostOfLivingAdjuster, 
    HistoricalDataManager,
    JobPosition,
    EnhancedAnalyzer
)


class TestDisciplineClassifier:
    """Test discipline classification functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = DisciplineClassifier()
    
    def test_wildlife_ecology_classification(self):
        """Test classification of wildlife ecology position."""
        position = JobPosition(
            title="PhD Research Assistantship - Wildlife Ecology and Behavior",
            organization="University of Test",
            location="Test, TX",
            salary="$25,000",
            starting_date="2025-08-01",
            published_date="06/20/2025",
            tags="Graduate Opportunities"
        )
        
        primary, secondary = self.classifier.classify_position(position)
        assert primary == "Wildlife Ecology"
    
    def test_fisheries_classification(self):
        """Test classification of fisheries position."""
        position = JobPosition(
            title="Masters in Fisheries Science - Salmon Ecology",
            organization="Fish University",
            location="Alaska",
            salary="$30,000",
            starting_date="2025-09-01", 
            published_date="06/20/2025",
            tags="Graduate Opportunities"
        )
        
        primary, secondary = self.classifier.classify_position(position)
        assert primary == "Fisheries Science"
    
    def test_unknown_classification(self):
        """Test classification of unknown/other position."""
        position = JobPosition(
            title="Administrative Assistant",
            organization="Some Company",
            location="Somewhere",
            salary="$20,000",
            starting_date="2025-08-01",
            published_date="06/20/2025", 
            tags="N/A"
        )
        
        primary, secondary = self.classifier.classify_position(position)
        assert primary == "Other"


class TestCostOfLivingAdjuster:
    """Test cost of living adjustment functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.adjuster = CostOfLivingAdjuster()
    
    def test_nebraska_baseline(self):
        """Test that Nebraska (Lincoln) has baseline cost index of 1.0."""
        index = self.adjuster.get_cost_index("Lincoln, Nebraska")
        assert index == 1.0
    
    def test_california_high_cost(self):
        """Test that California has higher cost index."""
        index = self.adjuster.get_cost_index("Los Angeles, California")
        assert index > 1.0
    
    def test_salary_adjustment(self):
        """Test salary adjustment calculation."""
        adjusted, cost_index = self.adjuster.adjust_salary("$50,000", "California")
        
        # California should have higher cost, so adjusted salary should be lower
        assert adjusted < 50000
        assert cost_index > 1.0
    
    def test_no_salary_adjustment(self):
        """Test handling of non-numeric salaries.""" 
        adjusted, cost_index = self.adjuster.adjust_salary("Commensurate", "Texas")
        
        assert adjusted == 0.0
        assert cost_index == 0.95  # Texas index
    
    def test_extract_salary_value(self):
        """Test salary value extraction."""
        # Test various salary formats
        assert self.adjuster._extract_salary_value("$25,000 per year") == 25000.0
        assert self.adjuster._extract_salary_value("starting at $30,000") == 30000.0
        assert self.adjuster._extract_salary_value("$20,000 to $25,000") == 20000.0
        assert self.adjuster._extract_salary_value("Commensurate") == 0.0


class TestHistoricalDataManager:
    """Test historical data management functionality."""
    
    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = HistoricalDataManager(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_generate_position_id(self):
        """Test position ID generation."""
        position1 = {
            'title': 'Test Position',
            'organization': 'Test University', 
            'location': 'Test, TX'
        }
        position2 = {
            'title': 'Test Position',
            'organization': 'Test University',
            'location': 'Test, TX'
        }
        position3 = {
            'title': 'Different Position',
            'organization': 'Test University',
            'location': 'Test, TX'
        }
        
        id1 = self.manager.generate_position_id(position1)
        id2 = self.manager.generate_position_id(position2) 
        id3 = self.manager.generate_position_id(position3)
        
        # Same positions should have same ID
        assert id1 == id2
        # Different positions should have different IDs
        assert id1 != id3
    
    def test_merge_new_positions(self):
        """Test merging new positions into empty historical data."""
        new_positions = [
            {
                'title': 'Wildlife Researcher',
                'organization': 'State University',
                'location': 'City, State',
                'salary': '$25,000',
                'starting_date': '2025-08-01',
                'published_date': '06/20/2025',
                'tags': 'Graduate'
            }
        ]
        
        historical_data, stats = self.manager.merge_positions(new_positions)
        
        assert len(historical_data) == 1
        assert stats['new_positions'] == 1
        assert stats['updated_positions'] == 0
        assert 'position_id' in historical_data[0]
        assert 'first_seen' in historical_data[0]
        assert 'last_updated' in historical_data[0]
    
    def test_merge_duplicate_positions(self):
        """Test merging duplicate positions updates existing ones."""
        # First, add a position
        initial_positions = [
            {
                'title': 'Wildlife Researcher',
                'organization': 'State University', 
                'location': 'City, State',
                'salary': '$25,000',
                'starting_date': '2025-08-01',
                'published_date': '06/20/2025',
                'tags': 'Graduate'
            }
        ]
        
        historical_data, _ = self.manager.merge_positions(initial_positions)
        self.manager.save_historical_data(historical_data, backup=False)
        
        # Now try to merge the same position again (with slight variation)
        updated_positions = [
            {
                'title': 'Wildlife Researcher',
                'organization': 'State University',
                'location': 'City, State', 
                'salary': '$26,000',  # Updated salary
                'starting_date': '2025-08-01',
                'published_date': '06/20/2025',
                'tags': 'Graduate'
            }
        ]
        
        historical_data, stats = self.manager.merge_positions(updated_positions)
        
        assert len(historical_data) == 1  # Still only one position
        assert stats['new_positions'] == 0
        assert stats['updated_positions'] == 1
        assert historical_data[0]['salary'] == '$26,000'  # Updated value


class TestEnhancedAnalyzer:
    """Test the main enhanced analyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Mock the historical manager to use temp directory
        with patch('scripts.enhanced_analysis.HistoricalDataManager') as mock_mgr:
            mock_mgr.return_value = HistoricalDataManager(self.temp_dir)
            self.analyzer = EnhancedAnalyzer()
            self.analyzer.historical_manager = HistoricalDataManager(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_analyze_positions(self):
        """Test complete position analysis."""
        test_positions = [
            {
                'title': 'PhD Research - Wildlife Ecology',
                'organization': 'Test University',
                'location': 'Lincoln, Nebraska',
                'salary': '$25,000 per year',
                'starting_date': '2025-08-01',
                'published_date': '06/20/2025',
                'tags': 'Graduate Opportunities'
            },
            {
                'title': 'Masters in Fisheries Science',
                'organization': 'Fish College', 
                'location': 'San Francisco, California',
                'salary': '$30,000 annually',
                'starting_date': '2025-09-01',
                'published_date': '06/20/2025',
                'tags': 'Graduate Opportunities'
            }
        ]
        
        results = self.analyzer.analyze_positions(test_positions)
        
        # Check that analysis was performed
        assert 'total_positions' in results
        assert 'disciplines' in results
        assert 'geographic_regions' in results
        assert 'salary_analysis_lincoln_adjusted' in results
        assert 'merge_stats' in results
        
        # Check that positions were classified
        assert 'Wildlife Ecology' in results['disciplines']
        assert 'Fisheries Science' in results['disciplines']
        
        # Check geographic regions
        assert 'Midwest' in results['geographic_regions']  # Nebraska
        assert 'West' in results['geographic_regions']      # California


# Integration test 
def test_full_workflow():
    """Test the complete enhanced analysis workflow."""
    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test data file
        test_data = [
            {
                'title': 'Wildlife Biologist Position',
                'organization': 'Wildlife Institute',
                'location': 'Austin, Texas',
                'salary': '$35,000',
                'starting_date': '2025-08-01',
                'published_date': '06/20/2025',
                'tags': 'Graduate Opportunities'
            }
        ]
        
        data_file = temp_path / "graduate_assistantships.json"
        with open(data_file, 'w') as f:
            json.dump(test_data, f)
        
        # Mock the Path objects in the script
        with patch('scripts.enhanced_analysis.Path') as mock_path:
            def path_side_effect(path_str):
                if path_str == "data/graduate_assistantships.json":
                    return data_file
                elif path_str == "data":
                    return temp_path
                else:
                    return Path(path_str)
            
            mock_path.side_effect = path_side_effect
            
            # Run the enhanced analysis
            from scripts.enhanced_analysis import main
            
            # Redirect the main function to use our test directory
            with patch('scripts.enhanced_analysis.HistoricalDataManager') as mock_mgr:
                mock_mgr.return_value = HistoricalDataManager(temp_path)
                
                # This should run without errors
                main()
                
                # Check that output files were created
                assert (temp_path / "enhanced_analysis.json").exists()
                assert (temp_path / "historical_positions.json").exists()


if __name__ == "__main__":
    pytest.main([__file__])