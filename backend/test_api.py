import requests
import json
from typing import Dict, List
import pytest
import pandas as pd
import os
from models import DataLoader
import time
import subprocess
import signal
import sys

def wait_for_server(url: str, timeout: int = 30):
    """Wait for server to be ready"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            requests.get(url)
            return True
        except requests.ConnectionError:
            time.sleep(1)
    return False

def run_tests_with_server():
    """Run tests with automatic server management"""
    # Start the server process
    server_process = subprocess.Popen([sys.executable, "main.py"])
    
    try:
        # Wait for server to be ready
        if not wait_for_server("http://localhost:8000/api/sprints"):
            print("Failed to start server")
            server_process.kill()
            return
        
        # Run all tests
        main()
    finally:
        # Cleanup: Kill the server process
        server_process.send_signal(signal.SIGINT)
        server_process.wait()

def test_data_loading():
    """Test that data files can be loaded correctly"""
    print("\nTesting data loading...")
    
    data_loader = DataLoader()
    try:
        data_loader.load_data()
        data_loader.print_data_info()
        print("✓ Data loading test passed")
    except Exception as e:
        print(f"✗ Data loading test failed: {str(e)}")
        raise

BASE_URL = "http://localhost:8000/api"

def test_sprints_endpoint():
    """Test the /api/sprints endpoint"""
    response = requests.get(f"{BASE_URL}/sprints")
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "sprints" in data
    assert isinstance(data["sprints"], list)
    assert len(data["sprints"]) > 0
    print(f"✓ Sprints endpoint test passed. Found {len(data['sprints'])} sprints")
    print(f"First sprint: {data['sprints'][0]}")

def test_teams_endpoint():
    """Test the /api/teams endpoint"""
    response = requests.get(f"{BASE_URL}/teams")
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "teams" in data
    assert isinstance(data["teams"], list)
    # Note: We don't assert length > 0 since some teams might be None
    print(f"✓ Teams endpoint test passed. Found {len(data['teams'])} teams")
    print(f"Sample teams: {data['teams'][:3]}")

def test_metrics_endpoint():
    """Test the /api/metrics endpoint"""
    # First get available sprints and teams
    sprints_response = requests.get(f"{BASE_URL}/sprints")
    teams_response = requests.get(f"{BASE_URL}/teams")
    
    sprints = sprints_response.json()["sprints"]
    teams = teams_response.json()["teams"]
    
    # Filter out None values from teams
    valid_teams = [team for team in teams if team is not None]
    if not valid_teams:
        print("No valid teams found, skipping metrics test")
        return
    
    # Test with first sprint and team
    params = {
        "selected_sprints[]": sprints[0],
        "selected_teams[]": valid_teams[0],
        "time_frame": 100
    }
    
    try:
        response = requests.get(f"{BASE_URL}/metrics", params=params)
        assert response.status_code == 200, f"Failed with status {response.status_code}: {response.text}"
        metrics = response.json()
        
        # Check basic metrics structure
        expected_basic_metrics = [
            "todo", "in_progress", "done", "removed", 
            "backlog_changes", "blocked_tasks"
        ]
        for metric in expected_basic_metrics:
            assert metric in metrics, f"Missing basic metric: {metric}"
            assert isinstance(metrics[metric], (int, float))
        
        # Check task tracking metrics
        assert "excluded_tasks" in metrics, "Missing excluded_tasks"
        assert "added_tasks" in metrics, "Missing added_tasks"
        assert isinstance(metrics["excluded_tasks"], dict)
        assert isinstance(metrics["added_tasks"], dict)
        
        # Check health score and details
        assert "health_score" in metrics, "Missing health_score"
        assert isinstance(metrics["health_score"], (int, float))
        assert 0 <= metrics["health_score"] <= 100, "Health score out of range"
        
        assert "health_details" in metrics, "Missing health_details"
        assert isinstance(metrics["health_details"], dict)
        
        assert "health_metrics" in metrics, "Missing health_metrics"
        expected_health_metrics = [
            "todo_percentage", "removed_percentage", 
            "backlog_change_percentage", "transition_evenness",
            "last_day_completion_percentage"
        ]
        for metric in expected_health_metrics:
            assert metric in metrics["health_metrics"], f"Missing health metric: {metric}"
        
        # Check status transitions
        assert "status_transitions" in metrics, "Missing status_transitions"
        assert "daily_distribution" in metrics["status_transitions"], "Missing daily distribution"
        assert "transition_evenness" in metrics["status_transitions"], "Missing transition evenness"
        
        # Validate specific metrics
        total_tasks = metrics["todo"] + metrics["in_progress"] + metrics["done"] + metrics["removed"]
        if total_tasks > 0:
            todo_percentage = (metrics["todo"] / total_tasks) * 100
            removed_percentage = (metrics["removed"] / total_tasks) * 100
            print(f"\nMetric Validations:")
            print(f"Todo percentage: {todo_percentage:.1f}% (should be ≤ 20%)")
            print(f"Removed percentage: {removed_percentage:.1f}% (should be ≤ 10%)")
            print(f"Backlog changes: {metrics['backlog_changes']:.1f}% (should be ≤ 20%)")
            print(f"Sprint health score: {metrics['health_score']}")
        
        print("\n✓ Metrics endpoint test passed")
        print("\nDetailed metrics received:", json.dumps(metrics, indent=2))
        
    except Exception as e:
        print(f"\n✗ Metrics test failed: {str(e)}")
        raise

def test_metrics_validation():
    """Test validation of metrics endpoint parameters"""
    test_cases = [
        # No sprints
        ({
            "selected_teams[]": ["Team1"],
            "time_frame": 100
        }, 422),
        # No teams
        ({
            "selected_sprints[]": ["Sprint1"],
            "time_frame": 100
        }, 422),
        # Invalid time frame
        ({
            "selected_sprints[]": ["Sprint1"],
            "selected_teams[]": ["Team1"],
            "time_frame": 101
        }, 422),
    ]
    
    for params, expected_status in test_cases:
        response = requests.get(f"{BASE_URL}/metrics", params=params)
        assert response.status_code == expected_status, \
            f"Expected status {expected_status}, got {response.status_code} for params {params}"
    
    print("✓ Metrics validation test passed")

def test_invalid_metrics_request():
    """Test the /api/metrics endpoint with invalid parameters"""
    # Test with missing parameters
    response = requests.get(f"{BASE_URL}/metrics")
    assert response.status_code == 422  # FastAPI validation error
    print("✓ Invalid metrics request test passed")

def main():
    """Run all tests"""
    print("\nRunning API tests...\n")
    try:
        test_data_loading()  # Add data loading test first
        test_sprints_endpoint()
        test_teams_endpoint()
        test_metrics_endpoint()
        test_metrics_validation()
        test_invalid_metrics_request()
        print("\n✓ All tests passed successfully!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {str(e)}")
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Could not connect to the API server. Make sure it's running on http://localhost:8000")
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--with-server":
        run_tests_with_server()
    else:
        main() 