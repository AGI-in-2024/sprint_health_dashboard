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
data_loader.load_data()

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

@app.get("/api/teams")
def get_teams():
    """Get list of all available teams"""
    teams = data_loader.tasks['workgroup'].dropna().unique().tolist()
    teams = [team if pd.notna(team) else None for team in teams]
    return {
        "teams": teams
    }

@app.get("/api/metrics", response_model=Dict[str, Any])
async def get_metrics(
    selected_sprints: Optional[List[str]] = Query(None, alias="selected_sprints[]"),
    selected_teams: Optional[List[str]] = Query(None, alias="selected_teams[]"),
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
    
    if not selected_teams:
        raise HTTPException(
            status_code=422,
            detail="No teams selected"
        )
    
    try:
        metrics = calculate_metrics(
            data_loader.tasks,
            data_loader.sprints,
            data_loader.history,
            selected_sprints,
            selected_teams,
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

def handle_shutdown(signal, frame):
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