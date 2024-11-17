import pytest
from models import DataLoader
import pandas as pd
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_models.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@pytest.fixture
def data_loader():
    """Fixture to provide a DataLoader instance"""
    return DataLoader()

def test_entity_ids_parsing(data_loader):
    """Test parsing of entity_ids in DataLoader"""
    data_loader.load_data()
    for _, row in data_loader.sprints.iterrows():
        assert isinstance(row['entity_ids'], (list, set)), f"entity_ids should be a list or set, got {type(row['entity_ids'])}"
        assert len(row['entity_ids']) > 0, f"entity_ids should not be empty for sprint {row['sprint_name']}"

def test_data_loading(data_loader):
    """Test complete data loading process"""
    data_loader.load_data()
    assert data_loader.is_loaded, "Data should be loaded successfully"
    assert len(data_loader.load_errors) == 0, f"Found errors during loading: {data_loader.load_errors}"
    
    # Check DataFrames are not empty
    assert not data_loader.tasks.empty, "Tasks DataFrame should not be empty"
    assert not data_loader.sprints.empty, "Sprints DataFrame should not be empty"
    assert not data_loader.history.empty, "History DataFrame should not be empty"

def test_required_columns(data_loader):
    """Test presence of required columns"""
    data_loader.load_data()
    
    # Check tasks columns
    required_task_columns = ['entity_id', 'status', 'area', 'estimation']
    for col in required_task_columns:
        assert col in data_loader.tasks.columns, f"Missing required column {col} in tasks"
    
    # Check sprints columns
    required_sprint_columns = ['sprint_name', 'sprint_start_date', 'sprint_end_date', 'entity_ids']
    for col in required_sprint_columns:
        assert col in data_loader.sprints.columns, f"Missing required column {col} in sprints"
    
    # Check history columns
    required_history_columns = ['entity_id', 'history_property_name', 'history_date', 'history_change']
    for col in required_history_columns:
        assert col in data_loader.history.columns, f"Missing required column {col} in history"

def test_data_types(data_loader):
    """Test data types of key columns"""
    data_loader.load_data()
    
    # Check tasks data types
    assert pd.api.types.is_numeric_dtype(data_loader.tasks['entity_id']), "entity_id should be numeric"
    assert pd.api.types.is_datetime64_dtype(data_loader.tasks['create_date']), "create_date should be datetime"
    
    # Check sprints data types
    assert pd.api.types.is_datetime64_dtype(data_loader.sprints['sprint_start_date']), "sprint_start_date should be datetime"
    assert pd.api.types.is_datetime64_dtype(data_loader.sprints['sprint_end_date']), "sprint_end_date should be datetime"
    
    # Check history data types
    assert pd.api.types.is_datetime64_dtype(data_loader.history['history_date']), "history_date should be datetime"

def test_data_relationships(data_loader):
    """Test relationships between DataFrames"""
    data_loader.load_data()
    
    # Check if all sprint entity_ids exist in tasks
    for _, row in data_loader.sprints.iterrows():
        entity_ids = row['entity_ids']
        for entity_id in entity_ids:
            assert entity_id in data_loader.tasks['entity_id'].values, \
                f"entity_id {entity_id} from sprint {row['sprint_name']} not found in tasks"

def test_data_quality(data_loader):
    """Test data quality checks"""
    data_loader.load_data()
    data_loader.check_data_quality()
    
    # Check for critical data quality issues
    assert data_loader.tasks['status'].notna().all(), "Found tasks without status"
    assert data_loader.tasks['entity_id'].notna().all(), "Found tasks without entity_id"
    
    # Check date ranges
    assert (data_loader.tasks['create_date'] <= pd.Timestamp.now()).all(), \
        "Found tasks with future create dates"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--log-cli-level=INFO"]) 