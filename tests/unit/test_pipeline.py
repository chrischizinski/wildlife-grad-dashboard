import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path
import json
import os

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Mock heavy dependencies BEFORE importing pipeline
sys.modules['src.wildlife_grad.scraper.wildlife_job_scraper'] = MagicMock()
sys.modules['src.wildlife_grad.analysis.enhanced_analysis'] = MagicMock()

from scripts.robust_data_pipeline import RobustDataPipeline

class TestRobustDataPipeline(unittest.TestCase):
    
    @patch('scripts.robust_data_pipeline.create_client')
    @patch('scripts.robust_data_pipeline.load_dotenv')
    @patch('scripts.robust_data_pipeline.GraduatePositionDetector')
    @patch('scripts.robust_data_pipeline.DisciplineClassifier')
    @patch('scripts.robust_data_pipeline.CostOfLivingAdjuster')
    @patch('scripts.robust_data_pipeline.JobPosition')
    def setUp(self, mock_job_pos, mock_col, mock_disc, mock_grad, mock_load_dotenv, mock_create_client):
        # Setup mocks for analysis classes
        self.mock_grad_detector = mock_grad.return_value
        self.mock_disc_classifier = mock_disc.return_value
        self.mock_col_adjuster = mock_col.return_value
        
        # Configure helper methods
        self.mock_grad_detector.is_graduate_position.return_value = (True, "Graduate Assistantship", 0.9)
        self.mock_disc_classifier.classify_position.return_value = ("Wildlife", "Ecology")
        self.mock_col_adjuster.get_cost_index.return_value = 1.0
        
        # Use a real class for JobPosition mock to handle attributes correctly
        class FakeJobPosition:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
            
            def to_dict(self):
                return self.__dict__

        mock_job_pos.side_effect = lambda **kwargs: FakeJobPosition(**kwargs)
        
        # Mock env vars
        with patch.dict(os.environ, {"SUPABASE_URL": "http://test.com", "SUPABASE_ANON_KEY": "test-key"}):
            self.pipeline = RobustDataPipeline()
            self.pipeline.setup_directories = MagicMock() # Don't actually create dirs
            
    def test_enhance_data(self):
        # Mock raw data
        raw_data = [{
            "title": "Graduate Research Assistant",
            "organization": "Test University",
            "location": "Lincoln, NE",
            "description": "PhD position in wildlife ecology.",
            "tags": "research"
        }]
        
        # Test enhancement logic
        # Test enhancement logic
        enhanced = self.pipeline.enhance_data(raw_data)
        with open("debug_test.txt", "a") as f:
            f.write(f"DEBUG: Enhanced data: {enhanced}\n")
        
        self.assertEqual(len(enhanced), 1)
        # Verify our mocks were called
        self.mock_grad_detector.is_graduate_position.assert_called()
        self.mock_disc_classifier.classify_position.assert_called()
        self.mock_col_adjuster.get_cost_index.assert_called()
        
        # Check result
        self.assertTrue(enhanced[0]["is_graduate_position"])
        self.assertEqual(enhanced[0]["discipline_primary"], "Wildlife")

    @patch('scripts.robust_data_pipeline.RobustDataPipeline.upload_to_supabase')
    @patch('scripts.robust_data_pipeline.RobustDataPipeline.generate_dashboard_data')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data='[{"title": "test"}]')
    @patch('json.load')
    @patch('shutil.copy2')
    @patch('json.dump')
    def test_process_scraped_data(self, mock_json_dump, mock_copy, mock_json_load, mock_open, mock_dashboard, mock_upload):
        
        mock_json_load.return_value = [{"title": "test"}]
        mock_upload.return_value = {"status": "success"}
        mock_dashboard.return_value = {"status": "success"}
        
        # Mock enhance_data to just return input
        self.pipeline.enhance_data = MagicMock(return_value=[{"title": "test", "is_graduate_position": True}])
        
        result = self.pipeline.process_scraped_data("data/raw/test.json", "20240101")
        
        self.assertEqual(result["status"], "success")
        mock_upload.assert_called_once()
        mock_dashboard.assert_called_once()

if __name__ == '__main__':
    unittest.main()
