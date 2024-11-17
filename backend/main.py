from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from models import DataLoader
from crud import calculate_metrics
import uvicorn
import pandas as pd
from fastapi import Request
from fastapi.responses import JSONResponse
import logging
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize data loader
data_loader = DataLoader()
try:
    data_loader.load_data()
    # Add data quality check
    data_loader.check_data_quality()
    logger.info("Data loaded and validated successfully")
except Exception as e:
    logger.error(f"Error during data initialization: {str(e)}")
    sys.exit(1)

# Add health check endpoint
@app.get("/api/health")
async def health_check():
    """Check if the service is healthy"""
    if not data_loader.is_loaded:
        return {
            "status": "error",
            "message": "Data not loaded",
            "errors": data_loader.load_errors
        }
    return {"status": "healthy"}

# Add error handling middleware
@app.middleware("http")
async def add_error_handling(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)}  # Add error details to response
        )

@app.get("/api/sprints")
def get_sprints():
    """Get list of all available sprints"""
    return {
        "sprints": data_loader.sprints['sprint_name'].tolist()
    }

@app.get("/api/areas")
def get_areas():
    """Get list of all available areas"""
    try:
        # Convert to Series first if it's a DataFrame column
        if isinstance(data_loader.tasks['area'], pd.DataFrame):
            areas_series = data_loader.tasks['area'].iloc[:, 0]
        else:
            areas_series = data_loader.tasks['area']
            
        # Get unique values
        areas = areas_series.dropna().unique().tolist()
        
        # Add debug logging
        logger.info(f"Found {len(areas)} unique areas")
        logger.debug(f"Areas: {areas}")
        
        return {
            "areas": areas
        }
    except Exception as e:
        logger.error(f"Error in get_areas: {str(e)}")
        logger.error(f"Data type of area column: {type(data_loader.tasks['area'])}")
        logger.error(f"Column names: {data_loader.tasks.columns.tolist()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get areas: {str(e)}"
        )

@app.get("/api/metrics", response_model=Dict[str, Any])
async def get_metrics(
    selected_sprints: Optional[List[str]] = Query(None, alias="selected_sprints[]"),
    selected_areas: Optional[List[str]] = Query(None, alias="selected_areas[]"),
    time_frame: Optional[int] = Query(100, ge=0, le=100)
):
    """Get metrics with improved error handling"""
    if not data_loader.is_loaded:
        raise HTTPException(
            status_code=503,
            detail="Service unavailable - data not loaded"
        )
    
    # Validate inputs
    if not selected_sprints:
        raise HTTPException(
            status_code=422,
            detail="No sprints selected"
        )
    
    if not selected_areas:
        raise HTTPException(
            status_code=422,
            detail="No areas selected"
        )
    
    try:
        metrics = calculate_metrics(
            data_loader.tasks,
            data_loader.sprints,
            data_loader.history,
            selected_sprints,
            selected_areas,
            time_frame
        )
        return metrics
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error calculating metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while calculating metrics"
        )

@app.get("/api/sprint-health")
async def get_sprint_health(
    selected_sprints: Optional[List[str]] = Query(None, alias="selected_sprints[]"),
    selected_areas: Optional[List[str]] = Query(None, alias="selected_areas[]"),
    time_frame: Optional[int] = Query(100, ge=0, le=100)
):
    """Get detailed sprint health metrics with breakdown"""
    if not data_loader.is_loaded:
        raise HTTPException(
            status_code=503,
            detail="Service unavailable - data not loaded"
        )
    
    # Validate inputs
    if not selected_sprints:
        raise HTTPException(
            status_code=422,
            detail="No sprints selected"
        )
    
    if not selected_areas:
        raise HTTPException(
            status_code=422,
            detail="No areas selected"
        )
    
    try:
        # Get base metrics first
        metrics = calculate_metrics(
            data_loader.tasks,
            data_loader.sprints,
            data_loader.history,
            selected_sprints,
            selected_areas,
            time_frame
        )
        
        # Extract sprint health data
        sprint_health = metrics.get('sprint_health', {})
        
        return {
            'health_score': sprint_health.get('score', 0),
            'details': sprint_health.get('details', {}),
            'metrics_snapshot': sprint_health.get('metrics_snapshot', {}),
            'category_scores': {
                'delivery': {
                    'score': sprint_health.get('metrics_snapshot', {}).get('delivery_score', 0),
                    'weight': '25%',
                    'description': 'Measures sprint completion rate and timing'
                },
                'stability': {
                    'score': sprint_health.get('metrics_snapshot', {}).get('stability_score', 0),
                    'weight': '20%',
                    'description': 'Evaluates sprint scope and backlog changes'
                },
                'flow': {
                    'score': sprint_health.get('metrics_snapshot', {}).get('flow_score', 0),
                    'weight': '20%',
                    'description': 'Assesses work distribution and blocked tasks'
                },
                'quality': {
                    'score': sprint_health.get('metrics_snapshot', {}).get('quality_score', 0),
                    'weight': '20%',
                    'description': 'Measures rework and technical debt management'
                },
                'team_load': {
                    'score': sprint_health.get('metrics_snapshot', {}).get('team_load_score', 0),
                    'weight': '15%',
                    'description': 'Evaluates team workload distribution'
                }
            },
            'key_metrics': {
                'completion_rate': {
                    'value': sprint_health.get('metrics_snapshot', {}).get('completion_rate', 0),
                    'unit': '%',
                    'description': 'Percentage of completed tasks'
                },
                'scope_changes': {
                    'value': sprint_health.get('metrics_snapshot', {}).get('scope_change_ratio', 0),
                    'unit': '%',
                    'description': 'Percentage of removed tasks'
                },
                'blocked_tasks': {
                    'value': sprint_health.get('metrics_snapshot', {}).get('blocked_ratio', 0),
                    'unit': '%',
                    'description': 'Percentage of blocked tasks'
                },
                'rework': {
                    'value': sprint_health.get('metrics_snapshot', {}).get('rework_count', 0),
                    'unit': 'tasks',
                    'description': 'Number of tasks requiring rework'
                },
                'tech_debt': {
                    'value': sprint_health.get('metrics_snapshot', {}).get('tech_debt_ratio', 0),
                    'unit': '%',
                    'description': 'Percentage of technical debt tasks'
                },
                'flow_evenness': {
                    'value': sprint_health.get('metrics_snapshot', {}).get('evenness_score', 0),
                    'unit': '%',
                    'description': 'How evenly work progresses through the sprint'
                },
                'last_day_completion': {
                    'value': sprint_health.get('metrics_snapshot', {}).get('last_day_completion_percentage', 0),
                    'unit': '%',
                    'description': 'Percentage of tasks completed on last day'
                }
            }
        }
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error calculating sprint health: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while calculating sprint health"
        )

def handle_shutdown(signal_number, frame):
    """Handle graceful shutdown"""
    logger.info("Shutting down gracefully...")
    # Cleanup code here if needed
    sys.exit(0)

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

if __name__ == "__main__":
    try:
        logger.info("Starting server...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1) 