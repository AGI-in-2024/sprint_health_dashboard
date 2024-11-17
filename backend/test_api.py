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
            response = requests.get(url)
            if response.status_code == 200:
                return True
            time.sleep(1)
        except requests.ConnectionError:
            time.sleep(1)
    return False

def run_tests_with_server():
    """Run tests with automatic server management"""
    # Start the server process
    server_process = subprocess.Popen([sys.executable, "main.py"])
    
    try:
        # Wait for server to be ready
        if not wait_for_server("http://localhost:8000/api/health"):
            print("Failed to start server")
            server_process.kill()
            return
        
        # Run all tests
        main()
    finally:
        # Cleanup: Kill the server process
        server_process.send_signal(signal.SIGINT)
        server_process.wait()

def test_health_endpoint():
    """Test the health check endpoint"""
    response = requests.get("http://localhost:8000/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
    print("✓ Health endpoint test passed")

def test_data_loading():
    """Test that data files can be loaded correctly"""
    print("\nTesting data loading...")
    
    data_loader = DataLoader()
    try:
        data_loader.load_data()
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

def test_areas_endpoint():
    """Test the /api/areas endpoint"""
    response = requests.get(f"{BASE_URL}/areas")
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "areas" in data
    assert isinstance(data["areas"], list)
    assert len(data["areas"]) > 0
    print(f"✓ Areas endpoint test passed. Found {len(data['areas'])} areas")
    print(f"Sample areas: {data['areas'][:3]}")

def test_metrics_endpoint():
    """Test the /api/metrics endpoint with comprehensive validation"""
    # First get available sprints and areas
    sprints_response = requests.get(f"{BASE_URL}/sprints")
    areas_response = requests.get(f"{BASE_URL}/areas")
    
    sprints = sprints_response.json()["sprints"]
    areas = areas_response.json()["areas"]
    
    # Validate inputs
    if not sprints or not areas:
        print("No sprints or areas found, skipping metrics test")
        return
    
    # Test with first sprint and area
    params = {
        "selected_sprints[]": [sprints[0]],  # Updated to handle list of sprints
        "selected_areas[]": areas[:2],  # Test with multiple areas
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
        
        # Check sprint health metrics
        assert "sprint_health" in metrics, "Missing sprint_health"
        health = metrics["sprint_health"]
        assert "score" in health, "Missing health score"
        assert "details" in health, "Missing health details"
        assert "metrics_snapshot" in health, "Missing health metrics snapshot"
        
        # Validate health score range
        assert 0 <= health["score"] <= 100, f"Health score {health['score']} out of range [0,100]"
        
        # Validate metrics snapshot
        snapshot = health["metrics_snapshot"]
        expected_snapshot_metrics = [
            "todo_percentage",
            "removed_percentage",
            "backlog_change_percentage",
            "transition_evenness",
            "last_day_completion_percentage"
        ]
        for metric in expected_snapshot_metrics:
            assert metric in snapshot, f"Missing snapshot metric: {metric}"
            assert isinstance(snapshot[metric], (int, float)), f"Invalid type for {metric}"
        
        # Check status transitions
        assert "status_transitions" in metrics, "Missing status_transitions"
        transitions = metrics["status_transitions"]
        assert "daily_distribution" in transitions, "Missing daily distribution"
        assert "transition_evenness" in transitions, "Missing transition evenness"
        assert "last_day_completion_percentage" in transitions, "Missing last day completion percentage"
        
        # Print detailed validation results
        print("\nMetrics Validation Results:")
        print(f"Health Score: {health['score']}")
        print(f"Todo Percentage: {snapshot['todo_percentage']:.1f}%")
        print(f"Removed Percentage: {snapshot['removed_percentage']:.1f}%")
        print(f"Backlog Changes: {snapshot['backlog_change_percentage']:.1f}%")
        print(f"Transition Evenness: {snapshot['transition_evenness']:.1f}%")
        print(f"Last Day Completion: {snapshot['last_day_completion_percentage']:.1f}%")
        
        if health["details"]:
            print("\nHealth Score Penalties:")
            for penalty, value in health["details"].items():
                print(f"- {penalty}: -{value:.1f} points")
        
        print("\n✓ Metrics endpoint test passed")
        
    except Exception as e:
        print(f"\n✗ Metrics test failed: {str(e)}")
        raise

def test_metrics_time_frame():
    """Test metrics endpoint with different time frames"""
    sprints = requests.get(f"{BASE_URL}/sprints").json()["sprints"]
    areas = requests.get(f"{BASE_URL}/areas").json()["areas"]
    
    time_frames = [0, 50, 100]
    for time_frame in time_frames:
        params = {
            "selected_sprints[]": [sprints[0]],
            "selected_areas[]": [areas[0]],
            "time_frame": time_frame
        }
        
        response = requests.get(f"{BASE_URL}/metrics", params=params)
        assert response.status_code == 200, f"Failed for time_frame={time_frame}"
        metrics = response.json()
        
        print(f"\nMetrics at {time_frame}% of sprint:")
        print(f"Todo: {metrics['todo']}")
        print(f"In Progress: {metrics['in_progress']}")
        print(f"Done: {metrics['done']}")
        print(f"Health Score: {metrics['sprint_health']['score']}")
    
    print("\n✓ Time frame test passed")

def test_metrics_validation():
    """Test validation of metrics endpoint parameters"""
    test_cases = [
        # No sprints
        ({
            "selected_areas[]": ["Area1"],
            "time_frame": 100
        }, 422),
        # No areas
        ({
            "selected_sprints[]": ["Sprint1"],
            "time_frame": 100
        }, 422),
        # Invalid time frame
        ({
            "selected_sprints[]": ["Sprint1"],
            "selected_areas[]": ["Area1"],
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

def test_metrics_calculations():
    """Test specific metric calculations with known data"""
    sprints = requests.get(f"{BASE_URL}/sprints").json()["sprints"]
    areas = requests.get(f"{BASE_URL}/areas").json()["areas"]
    
    params = {
        "selected_sprints[]": [sprints[0]],
        "selected_areas[]": [areas[0]],
        "time_frame": 100
    }
    
    response = requests.get(f"{BASE_URL}/metrics", params=params)
    metrics = response.json()
    
    # Validate metric relationships
    total = metrics['todo'] + metrics['in_progress'] + metrics['done'] + metrics['removed']
    
    # Basic assertions
    assert total > 0, "Total tasks should be greater than 0"
    assert metrics['todo'] >= 0, "Todo tasks cannot be negative"
    assert metrics['in_progress'] >= 0, "In progress tasks cannot be negative"
    assert metrics['done'] >= 0, "Done tasks cannot be negative"
    
    # Validate percentages
    assert 0 <= metrics['sprint_health']['metrics_snapshot']['todo_percentage'] <= 100
    assert 0 <= metrics['sprint_health']['metrics_snapshot']['removed_percentage'] <= 100
    
    # Check time consistency
    time_0 = requests.get(f"{BASE_URL}/metrics", 
                         params={**params, "time_frame": 0}).json()
    time_50 = requests.get(f"{BASE_URL}/metrics", 
                          params={**params, "time_frame": 50}).json()
    time_100 = metrics
    
    # Tasks should not decrease over time
    assert time_0['done'] <= time_50['done'] <= time_100['done'], \
        "Done tasks should not decrease over time"
    
    print("\nMetric Relationships Validation:")
    print(f"Total Tasks: {total}")
    print(f"Distribution: Todo={metrics['todo']}, In Progress={metrics['in_progress']}, "
          f"Done={metrics['done']}, Removed={metrics['removed']}")
    
    return metrics

def test_data_consistency():
    """Test data consistency across different API calls"""
    sprints = requests.get(f"{BASE_URL}/sprints").json()["sprints"]
    areas = requests.get(f"{BASE_URL}/areas").json()["areas"]
    
    # Test multiple calls with same parameters
    params = {
        "selected_sprints[]": [sprints[0]],
        "selected_areas[]": [areas[0]],
        "time_frame": 100
    }
    
    response1 = requests.get(f"{BASE_URL}/metrics", params=params)
    response2 = requests.get(f"{BASE_URL}/metrics", params=params)
    
    metrics1 = response1.json()
    metrics2 = response2.json()
    
    # Results should be identical for same parameters
    assert metrics1 == metrics2, "Inconsistent results for same parameters"
    
    # Test area combinations
    if len(areas) >= 2:
        params_single = {
            "selected_sprints[]": [sprints[0]],
            "selected_areas[]": [areas[0]],
            "time_frame": 100
        }
        params_multiple = {
            "selected_sprints[]": [sprints[0]],
            "selected_areas[]": areas[:2],
            "time_frame": 100
        }
        
        single_area = requests.get(f"{BASE_URL}/metrics", params=params_single).json()
        multiple_areas = requests.get(f"{BASE_URL}/metrics", params=params_multiple).json()
        
        # Multiple areas should have equal or more tasks
        assert multiple_areas['done'] >= single_area['done'], \
            "Multiple areas should include all tasks from single area"
    
    print("\n✓ Data consistency test passed")

def test_status_distribution():
    """Test status distribution anomalies"""
    sprints = requests.get(f"{BASE_URL}/sprints").json()["sprints"]
    areas = requests.get(f"{BASE_URL}/areas").json()["areas"]
    
    params = {
        "selected_sprints[]": [sprints[0]],
        "selected_areas[]": [areas[0]],
        "time_frame": 100
    }
    
    response = requests.get(f"{BASE_URL}/metrics", params=params)
    metrics = response.json()
    
    # Check for suspicious patterns
    if metrics['todo'] == 0 and metrics['in_progress'] == 0:
        print("\nWarning: No active tasks found (todo=0, in_progress=0)")
        print("This might indicate:")
        print("- Data filtering issue")
        print("- Status mapping problem")
        print("- All tasks already completed")
        
    # Calculate ratios
    total = metrics['todo'] + metrics['in_progress'] + metrics['done'] + metrics['removed']
    done_ratio = (metrics['done'] / total) * 100 if total > 0 else 0
    
    if done_ratio > 95:
        print(f"\nWarning: Unusually high completion rate ({done_ratio:.1f}%)")
        print("Consider checking:")
        print("- Status classification logic")
        print("- Time frame filtering")
        print("- Data completeness")

def test_time_based_metrics():
    """Validate time-based metric calculations"""
    sprints = requests.get(f"{BASE_URL}/sprints").json()["sprints"]
    areas = requests.get(f"{BASE_URL}/areas").json()["areas"]
    
    # Test all time frames from 0 to 100 in steps of 10
    time_frames = range(0, 101, 10)
    results = []
    
    params = {
        "selected_sprints[]": [sprints[0]],
        "selected_areas[]": [areas[0]]
    }
    
    for time_frame in time_frames:
        response = requests.get(f"{BASE_URL}/metrics", 
                              params={**params, "time_frame": time_frame})
        metrics = response.json()
        results.append({
            'time_frame': time_frame,
            'todo': metrics['todo'],
            'in_progress': metrics['in_progress'],
            'done': metrics['done'],
            'health_score': metrics['sprint_health']['score']
        })
    
    print("\nTime-based Progression:")
    for r in results:
        print(f"Time {r['time_frame']}%: "
              f"Todo={r['todo']}, "
              f"In Progress={r['in_progress']}, "
              f"Done={r['done']}, "
              f"Health={r['health_score']:.1f}")
              
    # Validate progression
    for i in range(len(results)-1):
        curr, next = results[i], results[i+1]
        assert curr['done'] <= next['done'], \
            f"Done tasks decreased from {curr['time_frame']}% to {next['time_frame']}%"

def test_status_mapping():
    """Test detailed status mapping and classification"""
    sprints = requests.get(f"{BASE_URL}/sprints").json()["sprints"]
    areas = requests.get(f"{BASE_URL}/areas").json()["areas"]
    
    params = {
        "selected_sprints[]": [sprints[0]],
        "selected_areas[]": [areas[0]],
        "time_frame": 100
    }
    
    response = requests.get(f"{BASE_URL}/metrics", params=params)
    metrics = response.json()
    
    print("\nStatus Classification Analysis:")
    print("1. Task Status Distribution:")
    total = metrics['todo'] + metrics['in_progress'] + metrics['done'] + metrics['removed']
    print(f"- Todo: {metrics['todo']} ({metrics['todo']/total*100:.1f}%)")
    print(f"- In Progress: {metrics['in_progress']} ({metrics['in_progress']/total*100:.1f}%)")
    print(f"- Done: {metrics['done']} ({metrics['done']/total*100:.1f}%)")
    print(f"- Removed: {metrics['removed']} ({metrics['removed']/total*100:.1f}%)")
    
    print("\n2. Status Transitions:")
    transitions = metrics['status_transitions']
    print(f"- Transition Evenness: {transitions['transition_evenness']:.1f}%")
    print(f"- Last Day Completion: {transitions['last_day_completion_percentage']:.1f}%")
    
    # Check daily distribution
    daily_dist = transitions['daily_distribution']
    if daily_dist:
        print("\n3. Daily Status Changes:")
        for date, changes in daily_dist.items():
            print(f"Date {date}:")
            print(f"- To In Progress: {changes.get('to_in_progress', 0)}")
            print(f"- To Done: {changes.get('to_done', 0)}")
            print(f"- Total Changes: {changes.get('total_changes', 0)}")

def test_detailed_time_progression():
    """Analyze detailed metrics progression through sprint"""
    sprints = requests.get(f"{BASE_URL}/sprints").json()["sprints"]
    areas = requests.get(f"{BASE_URL}/areas").json()["areas"]
    
    params = {
        "selected_sprints[]": [sprints[0]],
        "selected_areas[]": [areas[0]]
    }
    
    print("\nDetailed Sprint Progression Analysis:")
    
    # Analyze key transition points
    key_points = [0, 25, 50, 75, 100]
    for point in key_points:
        response = requests.get(f"{BASE_URL}/metrics", 
                              params={**params, "time_frame": point})
        metrics = response.json()
        
        print(f"\nAt {point}% of Sprint:")
        print(f"1. Task Counts:")
        print(f"- Todo: {metrics['todo']}")
        print(f"- In Progress: {metrics['in_progress']}")
        print(f"- Done: {metrics['done']}")
        print(f"- Removed: {metrics['removed']}")
        
        print(f"\n2. Health Metrics:")
        health = metrics['sprint_health']
        print(f"- Overall Score: {health['score']:.1f}")
        print(f"- Todo %: {health['metrics_snapshot']['todo_percentage']:.1f}%")
        print(f"- Backlog Changes: {health['metrics_snapshot']['backlog_change_percentage']:.1f}%")
        print(f"- Transition Evenness: {health['metrics_snapshot']['transition_evenness']:.1f}%")
        
        if health['details']:
            print("\n3. Score Penalties:")
            for penalty, value in health['details'].items():
                print(f"- {penalty}: -{value:.1f}")

def test_data_quality():
    """Check data quality and completeness"""
    sprints = requests.get(f"{BASE_URL}/sprints").json()["sprints"]
    areas = requests.get(f"{BASE_URL}/areas").json()["areas"]
    
    print("\nData Quality Analysis:")
    
    # Test each sprint
    for sprint in sprints:
        params = {
            "selected_sprints[]": [sprint],
            "selected_areas[]": areas,
            "time_frame": 100
        }
        
        response = requests.get(f"{BASE_URL}/metrics", params=params)
        metrics = response.json()
        
        total = metrics['todo'] + metrics['in_progress'] + metrics['done'] + metrics['removed']
        active = metrics['todo'] + metrics['in_progress']
        
        print(f"\nSprint: {sprint}")
        print(f"1. Task Counts:")
        print(f"- Total Tasks: {total}")
        print(f"- Active Tasks: {active}")
        print(f"- Completion Rate: {(metrics['done']/total*100 if total else 0):.1f}%")
        
        if active == 0:
            print("WARNING: No active tasks found!")
        if metrics['done']/total > 0.95:
            print("WARNING: Unusually high completion rate!")

def main():
    """Run all tests"""
    print("\nRunning API tests...\n")
    try:
        test_health_endpoint()
        test_data_loading()
        test_sprints_endpoint()
        test_areas_endpoint()
        test_metrics_endpoint()
        test_metrics_time_frame()
        test_metrics_calculations()
        test_data_consistency()
        test_metrics_validation()
        test_invalid_metrics_request()
        test_status_distribution()
        test_time_based_metrics()
        test_status_mapping()
        test_detailed_time_progression()
        test_data_quality()
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