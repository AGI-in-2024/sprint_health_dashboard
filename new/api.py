from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
import json
from datetime import datetime, timedelta
from sprint_health import SprintHealthAnalyzer
from fastapi.responses import JSONResponse
import uvicorn
import pandas as pd
from pydantic import BaseModel, Field
import pickle
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sprint_health_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add cache configuration after imports
CACHE_DIR = Path("cache")
CACHE_FILE = CACHE_DIR / "sprint_health_cache.pkl"
CACHE_VALIDITY_HOURS = 24  # Cache valid for 24 hours

class HealthParameters(BaseModel):
    """Parameters for customizing health calculation"""
    max_todo_percentage: float = Field(default=20.0, description="Maximum allowed percentage of tasks in 'To Do' status")
    max_removed_percentage: float = Field(default=10.0, description="Maximum allowed percentage of removed tasks")
    max_backlog_change: float = Field(default=20.0, description="Maximum allowed backlog change percentage")
    uniformity_weight: float = Field(default=0.25, description="Weight for status transition uniformity")
    backlog_weight: float = Field(default=0.25, description="Weight for backlog stability")
    completion_weight: float = Field(default=0.25, description="Weight for completion rate")
    quality_weight: float = Field(default=0.25, description="Weight for quality metrics")

app = FastAPI(
    title="Sprint Health API",
    description="API for analyzing sprint health metrics",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize SprintHealthAnalyzer
analyzer = None

def init_analyzer():
    """Initialize the SprintHealthAnalyzer with caching"""
    global analyzer
    if analyzer is None:
        try:
            # Create cache directory if it doesn't exist
            CACHE_DIR.mkdir(exist_ok=True)
            
            # Check if valid cache exists
            if CACHE_FILE.exists():
                cache_stat = os.stat(CACHE_FILE)
                cache_age = datetime.now() - datetime.fromtimestamp(cache_stat.st_mtime)
                
                if cache_age < timedelta(hours=CACHE_VALIDITY_HOURS):
                    logger.info("Loading analyzer from cache...")
                    with open(CACHE_FILE, 'rb') as f:
                        analyzer = pickle.load(f)
                    return

            # Initialize new analyzer if no valid cache
            logger.info("Initializing new analyzer...")
            analyzer = SprintHealthAnalyzer()
            analyzer.load_data()
            
            # Cache the analyzer
            with open(CACHE_FILE, 'wb') as f:
                pickle.dump(analyzer, f)
                
            logger.info("Sprint Health Analyzer initialized and cached successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Sprint Health Analyzer: {str(e)}")
            raise

@app.middleware("http")
async def add_error_handling(request: Request, call_next):
    """Global error handling middleware"""
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)}
        )

@app.on_event("startup")
async def startup_event():
    """Initialize analyzer on startup"""
    init_analyzer()

@app.get("/api/health")
async def health_check():
    """Check if the service is healthy"""
    try:
        if analyzer is None or not hasattr(analyzer, 'data_loaded') or not analyzer.data_loaded:
            return {
                "status": "error",
                "message": "Data not loaded"
            }
        return {
            "status": "healthy",
            "data_loaded": True
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Service health check failed"
        )

@app.get("/api/sprints")
async def get_sprints():
    """Get list of all available sprints with their basic info"""
    try:
        if analyzer is None:
            init_analyzer()
            
        sprints_data = []
        for _, sprint in analyzer.sprints_df.iterrows():
            sprint_info = {
                "name": sprint['sprint_name'],
                "status": "active" if sprint['sprint_end_date'] > datetime.now() else "completed",
                "startDate": sprint['sprint_start_date'].strftime("%Y-%m-%d"),
                "endDate": sprint['sprint_end_date'].strftime("%Y-%m-%d")
            }
            sprints_data.append(sprint_info)
            
        return {
            "sprints": sprints_data,
            "count": len(sprints_data)
        }
    except Exception as e:
        logger.error(f"Error getting sprints: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get sprints list"
        )

@app.get("/api/areas")
async def get_areas():
    """Get list of all available areas with task counts"""
    try:
        if analyzer is None:
            init_analyzer()
            
        area_counts = analyzer.entities_df['area'].value_counts().to_dict()
        areas_data = [
            {
                "name": area,
                "taskCount": count,
                "id": str(idx)
            }
            for idx, (area, count) in enumerate(area_counts.items())
            if pd.notna(area)
        ]
        
        return {
            "areas": areas_data,
            "count": len(areas_data)
        }
    except Exception as e:
        logger.error(f"Error getting areas: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get areas list"
        )

@app.get("/api/sprint-health")
async def get_sprint_health(
    sprint_ids: List[str] = Query(..., description="List of sprint IDs to analyze"),
    selected_areas: Optional[List[str]] = Query(None, description="List of areas to filter by"),
    time_point: Optional[float] = Query(None, description="Percentage of sprint duration (0-100) to analyze")
) -> Dict[str, Any]:
    try:
        if analyzer is None:
            init_analyzer()

        # Validate sprint IDs exist
        available_sprints = set(analyzer.sprints_df['sprint_name'].values)
        invalid_sprints = [sprint_id for sprint_id in sprint_ids if sprint_id not in available_sprints]
        if invalid_sprints:
            raise HTTPException(
                status_code=404,
                detail=f"Sprints not found: {', '.join(invalid_sprints)}"
            )

        results = {
            'sprints': {},
            'aggregated': {
                'health_score': 0.0,
                'metrics': {}
            }
        }

        for sprint_id in sprint_ids:
            # Filter data by areas if specified
            sprint_data = analyzer.get_sprint_data(sprint_id)
            if selected_areas:
                sprint_data = sprint_data[sprint_data['area'].isin(selected_areas)]
            
            metrics = analyzer.analyze_sprint_health(
                sprint_id=sprint_id,
                sprint_data=sprint_data,  # Pass filtered data
                time_point=time_point
            )

            if metrics:
                results['sprints'][sprint_id] = {
                    'health_score': metrics['health_score'],
                    'category_scores': metrics['category_scores'],
                    'key_metrics': metrics['key_metrics'],
                    'daily_metrics': metrics['daily_metrics']
                }

        # Calculate aggregated metrics
        if results['sprints']:
            results['aggregated']['health_score'] = sum(
                s['health_score'] for s in results['sprints'].values()
            ) / len(results['sprints'])

        return results

    except Exception as e:
        logger.error(f"Error calculating sprint health: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate sprint health: {str(e)}"
        )

if __name__ == "__main__":
    try:
        logger.info("Starting server...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise 