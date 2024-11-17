import pytest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test configuration
@pytest.fixture(autouse=True)
def setup_test_environment():
    # Setup test environment variables if needed
    pass 