import pandas as pd
from datetime import datetime, timedelta
from crud import calculate_metrics, validate_task_data

def test_status_mapping():
    """Test status mapping and metric calculations with sample data"""
    # Create test data with fixed dates
    fixed_start = datetime(2024, 1, 1)
    fixed_create_date = fixed_start + timedelta(days=1)  # Create tasks one day after sprint start
    
    test_data = {
        'entity_id': [1, 2, 3],
        'status': ['Создано', 'В работе', 'Закрыто'],
        'resolution': ['', '', 'Готово'],
        'estimation': [3600, 7200, 3600],  # 1 hour, 2 hours, 1 hour
        'create_date': [fixed_create_date] * 3,
        'update_date': [fixed_create_date] * 3,
        'area': ['Test Area'] * 3,
        'links': ['', '', '']  # Add links column to test blocked tasks
    }
    tasks_df = pd.DataFrame(test_data)
    
    # Create test sprint data with same fixed dates
    sprint_data = {
        'sprint_name': ['Test Sprint'],
        'entity_ids': [{1, 2, 3}],
        'sprint_start_date': [fixed_start],
        'sprint_end_date': [fixed_start + timedelta(days=14)]
    }
    sprints_df = pd.DataFrame(sprint_data)
    
    # Create empty history data
    history_df = pd.DataFrame()
    
    # Calculate metrics
    metrics = calculate_metrics(
        tasks_df,
        sprints_df,
        history_df,
        ['Test Sprint'],
        ['Test Area'],
        100
    )
    
    # Detailed assertions
    assert metrics['todo'] == 1.0, f"Expected todo=1.0, got {metrics['todo']}"
    assert metrics['in_progress'] == 2.0, f"Expected in_progress=2.0, got {metrics['in_progress']}"
    assert metrics['done'] == 1.0, f"Expected done=1.0, got {metrics['done']}"
    assert metrics['removed'] == 0.0, f"Expected removed=0.0, got {metrics['removed']}"
    assert metrics['blocked_tasks'] == 0.0, f"Expected blocked_tasks=0.0, got {metrics['blocked_tasks']}"
    assert metrics['backlog_changes'] == 0.0, f"Expected backlog_changes=0.0, got {metrics['backlog_changes']}"
    assert metrics['health_score'] > 0, "Health score should be greater than 0"
    assert 'health_details' in metrics, "Health details should be present in metrics"
    assert 'health_metrics' in metrics, "Health metrics should be present in metrics"
    
    print("Status mapping test passed!")

def test_edge_cases():
    """Test edge cases and boundary conditions"""
    fixed_start = datetime(2024, 1, 1)
    fixed_create_date = fixed_start + timedelta(days=1)

    # Test case 1: Empty tasks - create with minimum required columns
    empty_tasks_df = pd.DataFrame({
        'entity_id': [],
        'status': [],
        'resolution': [],
        'estimation': [],
        'create_date': [],
        'update_date': [],
        'area': [],
        'links': []
    })
    
    # Test case 2: All tasks removed
    removed_tasks_data = {
        'entity_id': [1, 2],
        'status': ['Закрыто', 'Закрыто'],
        'resolution': ['отклонено', 'дубликат'],
        'estimation': [3600, 7200],
        'create_date': [fixed_create_date] * 2,
        'update_date': [fixed_create_date] * 2,
        'area': ['Test Area'] * 2,
        'links': ['', '']
    }
    removed_tasks_df = pd.DataFrame(removed_tasks_data)
    
    # Test case 3: All tasks blocked
    blocked_tasks_data = {
        'entity_id': [1, 2],
        'status': ['В работе', 'В работе'],
        'resolution': ['', ''],
        'estimation': [3600, 7200],
        'create_date': [fixed_create_date] * 2,
        'update_date': [fixed_create_date] * 2,
        'area': ['Test Area'] * 2,
        'links': ['is blocked by TASK-123', 'заблокировано TASK-456']
    }
    blocked_tasks_df = pd.DataFrame(blocked_tasks_data)
    
    # Create test sprint data
    sprint_data = {
        'sprint_name': ['Test Sprint'],
        'entity_ids': [{1, 2}],
        'sprint_start_date': [fixed_start],
        'sprint_end_date': [fixed_start + timedelta(days=14)]
    }
    sprints_df = pd.DataFrame(sprint_data)
    
    # Create empty history data with required columns
    history_df = pd.DataFrame({
        'entity_id': [],
        'history_property_name': [],
        'history_date': [],
        'history_change': []
    })
    
    try:
        # Test empty tasks
        metrics_empty = calculate_metrics(
            empty_tasks_df, sprints_df, history_df,
            ['Test Sprint'], ['Test Area'], 100
        )
        assert metrics_empty['todo'] == 0.0, "Empty tasks should have 0 todo"
        assert metrics_empty['done'] == 0.0, "Empty tasks should have 0 done"
        assert metrics_empty['in_progress'] == 0.0, "Empty tasks should have 0 in progress"
        assert metrics_empty['removed'] == 0.0, "Empty tasks should have 0 removed"
        assert metrics_empty['blocked_tasks'] == 0.0, "Empty tasks should have 0 blocked"
        
        # Test removed tasks
        metrics_removed = calculate_metrics(
            removed_tasks_df, sprints_df, history_df,
            ['Test Sprint'], ['Test Area'], 100
        )
        assert metrics_removed['removed'] == 3.0, "Should have 3 hours of removed tasks"
        assert metrics_removed['done'] == 0.0, "Removed tasks shouldn't count as done"
        
        # Test blocked tasks
        metrics_blocked = calculate_metrics(
            blocked_tasks_df, sprints_df, history_df,
            ['Test Sprint'], ['Test Area'], 100
        )
        assert metrics_blocked['blocked_tasks'] == 3.0, "Should have 3 hours of blocked tasks"
        assert metrics_blocked['in_progress'] == 3.0, "Blocked tasks should still count as in progress"
        
        print("Edge cases test passed!")
        
    except Exception as e:
        print(f"Edge cases test failed: {str(e)}")
        raise

if __name__ == "__main__":
    test_status_mapping()
    test_edge_cases() 