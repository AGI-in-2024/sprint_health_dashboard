import requests
import pytest
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API base URL
BASE_URL = "http://localhost:8000"

class TestSprintHealthAPI:
    """Test suite for Sprint Health API"""

    def setup_method(self):
        """Setup test environment before each test"""
        # Verify API is running
        try:
            response = requests.get(f"{BASE_URL}/api/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
        except Exception as e:
            pytest.fail(f"API is not running: {str(e)}")

    def test_health_check(self):
        """Test health check endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        data = response.json()
        
        assert response.status_code == 200
        assert data["status"] == "healthy"
        assert "entities_count" in data
        assert "sprints_count" in data
        assert "history_count" in data

    def test_get_sprints(self):
        """Test sprints listing endpoint"""
        response = requests.get(f"{BASE_URL}/api/sprints")
        data = response.json()
        
        assert response.status_code == 200
        assert "sprints" in data
        assert "count" in data
        assert isinstance(data["sprints"], list)
        
        # Verify sprint data structure
        if data["sprints"]:
            sprint = data["sprints"][0]
            assert "id" in sprint
            assert "status" in sprint
            assert "start_date" in sprint
            assert "end_date" in sprint
            assert "task_count" in sprint

    def test_get_areas(self):
        """Test areas listing endpoint"""
        response = requests.get(f"{BASE_URL}/api/areas")
        data = response.json()
        
        assert response.status_code == 200
        assert "areas" in data
        assert "count" in data
        assert isinstance(data["areas"], list)
        
        # Verify area data structure
        if data["areas"]:
            area = data["areas"][0]
            assert "name" in area
            assert "task_count" in area

    def test_sprint_health_calculation(self):
        """Test sprint health calculation with various parameters"""
        try:
            # First get available sprints
            sprints_response = requests.get(f"{BASE_URL}/api/sprints")
            sprints_data = sprints_response.json()
            
            if not sprints_data["sprints"]:
                pytest.skip("No sprints available for testing")
            
            # Test single sprint analysis
            sprint_id = sprints_data["sprints"][0]["id"]
            params = {
                "sprint_ids": [sprint_id],
                "time_point": 50  # Test mid-sprint analysis
            }
            
            response = requests.get(f"{BASE_URL}/api/sprint-health", params=params)
            
            # Add detailed error logging
            if response.status_code != 200:
                print(f"\nError Response: {response.text}")
            
            data = response.json()
            assert response.status_code == 200
            assert "sprints" in data
            assert sprint_id in data["sprints"]
            
            # Verify health metrics structure
            sprint_data = data["sprints"][sprint_id]
            assert "health_score" in sprint_data
            assert "advanced_score" in sprint_data
            assert "category_scores" in sprint_data
            assert "metrics" in sprint_data
            assert "daily_metrics" in sprint_data
            
        except Exception as e:
            pytest.fail(f"Test failed with error: {str(e)}")

    def test_multiple_sprints_analysis(self):
        """Test analysis of multiple sprints"""
        # Get available sprints
        sprints_response = requests.get(f"{BASE_URL}/api/sprints")
        sprints_data = sprints_response.json()
        
        if len(sprints_data["sprints"]) < 2:
            pytest.skip("Not enough sprints for multiple sprint testing")
            
        # Select two sprints
        sprint_ids = [sprint["id"] for sprint in sprints_data["sprints"][:2]]
        params = {
            "sprint_ids": sprint_ids
        }
        
        response = requests.get(f"{BASE_URL}/api/sprint-health", params=params)
        data = response.json()
        
        assert response.status_code == 200
        assert "sprints" in data
        assert "aggregated" in data
        
        # Verify aggregated metrics
        assert "health_score" in data["aggregated"]
        assert "metrics" in data["aggregated"]
        
        # Verify all sprints are analyzed
        for sprint_id in sprint_ids:
            assert sprint_id in data["sprints"]

    def test_custom_parameters(self):
        """Test sprint health calculation with custom parameters"""
        # Get a sprint for testing
        sprints_response = requests.get(f"{BASE_URL}/api/sprints")
        sprints_data = sprints_response.json()
        
        if not sprints_data["sprints"]:
            pytest.skip("No sprints available for testing")
            
        sprint_id = sprints_data["sprints"][0]["id"]
        
        # Test with custom parameters
        custom_params = {
            "sprint_ids": [sprint_id],
            "max_todo_percentage": 15.0,
            "max_removed_percentage": 5.0,
            "max_backlog_change": 15.0,
            "uniformity_weight": 0.3,
            "backlog_weight": 0.2,
            "completion_weight": 0.3,
            "quality_weight": 0.2
        }
        
        response = requests.get(f"{BASE_URL}/api/sprint-health", params=custom_params)
        data = response.json()
        
        assert response.status_code == 200
        assert sprint_id in data["sprints"]
        
        # Verify custom parameters are applied
        sprint_data = data["sprints"][sprint_id]
        metrics = sprint_data["metrics"]
        
        assert metrics["todo"]["threshold"] == 15.0
        assert metrics["removed"]["threshold"] == 5.0
        assert metrics["backlog_change"]["threshold"] == 15.0

    def test_error_handling(self):
        """Test API error handling"""
        # Test invalid sprint ID
        params = {
            "sprint_ids": ["invalid_sprint_id"]
        }
        response = requests.get(f"{BASE_URL}/api/sprint-health", params=params)
        assert response.status_code == 404
        
        # Test invalid time point
        params = {
            "sprint_ids": [self._get_valid_sprint_id()],
            "time_point": 150  # Invalid percentage
        }
        response = requests.get(f"{BASE_URL}/api/sprint-health", params=params)
        assert response.status_code == 400

    def _get_valid_sprint_id(self):
        """Helper method to get a valid sprint ID"""
        response = requests.get(f"{BASE_URL}/api/sprints")
        data = response.json()
        if not data["sprints"]:
            pytest.skip("No sprints available for testing")
        return data["sprints"][0]["id"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 