from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
import json
from datetime import datetime, timedelta
from sprint_health import SprintHealthAnalyzer
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel, Field
import pandas as pd

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
    """Initialize the SprintHealthAnalyzer if not already initialized"""
    global analyzer
    if analyzer is None:
        try:
            analyzer = SprintHealthAnalyzer()
            analyzer.load_data()
            logger.info("Sprint Health Analyzer initialized successfully")
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
        if analyzer is None or not hasattr(analyzer, 'entities_df') or analyzer.entities_df is None:
            return {
                "status": "error",
                "message": "Data not loaded"
            }
        return {
            "status": "healthy",
            "data_loaded": True,
            "entities_count": len(analyzer.entities_df),
            "sprints_count": len(analyzer.sprints_df),
            "history_count": len(analyzer.history_df)
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Service health check failed"
        )

@app.get("/api/sprint-health")
async def get_sprint_health(
    sprint_ids: List[str] = Query(..., description="List of sprint IDs to analyze"),
    selected_areas: Optional[List[str]] = Query(None, description="List of areas to filter by"),
    time_point: Optional[float] = Query(
        None, 
        description="Percentage of sprint duration (0-100) to analyze. If not provided, analyzes entire sprint."
    ),
    max_todo_percentage: float = Query(20.0, description="Maximum allowed percentage of tasks in 'To Do' status"),
    max_removed_percentage: float = Query(10.0, description="Maximum allowed percentage of removed tasks"),
    max_backlog_change: float = Query(20.0, description="Maximum allowed backlog change percentage"),
    uniformity_weight: float = Query(0.25, description="Weight for status transition uniformity"),
    backlog_weight: float = Query(0.25, description="Weight for backlog stability"),
    completion_weight: float = Query(0.25, description="Weight for completion rate"),
    quality_weight: float = Query(0.25, description="Weight for quality metrics")
) -> Dict[str, Any]:
    """Get detailed sprint health metrics for selected sprints"""
    try:
        # Validate time_point first if provided
        if time_point is not None and not 0 <= time_point <= 100:
            raise HTTPException(
                status_code=400,
                detail="Time point must be between 0 and 100"
            )
            
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

        # Initialize results dictionary
        results = {
            'sprints': {},
            'aggregated': {
                'health_score': 0.0,
                'metrics': {}
            }
        }

        # Analyze each sprint with proper error handling
        for sprint_id in sprint_ids:
            try:
                # Create parameters dictionary
                parameters = {
                    'max_todo_percentage': max_todo_percentage,
                    'max_removed_percentage': max_removed_percentage,
                    'max_backlog_change': max_backlog_change,
                    'uniformity_weight': uniformity_weight,
                    'backlog_weight': backlog_weight,
                    'completion_weight': completion_weight,
                    'quality_weight': quality_weight
                }

                metrics = analyzer.analyze_sprint_health(sprint_id, parameters, time_point)
                
                if not metrics:
                    logger.warning(f"No metrics returned for sprint {sprint_id}")
                    continue

                # Extract health scores and components
                sprint_result = {
                    'health_score': metrics.get('health_scores', {}).get('original', 0.0),
                    'advanced_score': metrics.get('health_scores', {}).get('advanced', 0.0),
                    'category_scores': {
                        'delivery': {
                            'score': metrics.get('status_transition_uniformity', 0.0),
                            'weight': '25%',
                            'description': 'Measures sprint completion rate and timing'
                        },
                        'stability': {
                            'score': max(0.0, 1.0 - (metrics.get('removed_percentage', 0.0) / 100)),
                            'weight': '20%',
                            'description': 'Evaluates sprint scope and backlog changes'
                        },
                        'flow': {
                            'score': metrics.get('status_transition_uniformity', 0.0),
                            'weight': '20%',
                            'description': 'Assesses work distribution and blocked tasks'
                        },
                        'quality': {
                            'score': metrics.get('health_scores', {}).get('components', {}).get('quality_score', 0.0),
                            'weight': '20%',
                            'description': 'Measures rework and technical debt management'
                        },
                        'team_load': {
                            'score': metrics.get('health_scores', {}).get('components', {}).get('team_load_score', 0.0),
                            'weight': '15%',
                            'description': 'Evaluates team workload distribution'
                        }
                    },
                    'metrics': metrics.get('metrics', {}),
                    'daily_metrics': metrics.get('daily_metrics', {})
                }

                results['sprints'][sprint_id] = sprint_result

            except Exception as e:
                logger.error(f"Error analyzing sprint {sprint_id}: {str(e)}")
                results['sprints'][sprint_id] = {
                    'error': f"Failed to analyze sprint: {str(e)}"
                }

        # Calculate aggregated metrics if we have valid results
        valid_sprints = [s for s in results['sprints'].values() if 'error' not in s]
        if valid_sprints:
            results['aggregated']['health_score'] = sum(s['health_score'] for s in valid_sprints) / len(valid_sprints)
            
            # Aggregate other metrics
            for sprint_result in valid_sprints:
                for metric_name, metric_data in sprint_result.get('metrics', {}).items():
                    if metric_name not in results['aggregated']['metrics']:
                        results['aggregated']['metrics'][metric_name] = {
                            'value': 0.0,
                            'unit': metric_data.get('unit', ''),
                            'description': f"Average {metric_data.get('description', '').lower()}"
                        }
                    results['aggregated']['metrics'][metric_name]['value'] += metric_data.get('value', 0.0)

            # Calculate averages for aggregated metrics
            for metric in results['aggregated']['metrics'].values():
                metric['value'] /= len(valid_sprints)

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating sprint health: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate sprint health: {str(e)}"
        )

def _calculate_metrics_at_timepoint(metrics: Dict, time_point: float) -> Dict:
    """Calculate metrics at a specific time point in the sprint"""
    if not 0 <= time_point <= 100:
        raise ValueError("Time point must be between 0 and 100")
        
    # Get dates sorted
    dates = sorted(metrics['daily_metrics'].keys())
    if not dates:
        return metrics
        
    # Calculate target date
    total_days = len(dates)
    target_day = int((time_point / 100) * (total_days - 1))
    target_date = dates[target_day]
    
    # Filter daily metrics
    filtered_metrics = {
        date: data 
        for date, data in metrics['daily_metrics'].items()
        if date <= target_date
    }
    
    # Update metrics with filtered data
    metrics['daily_metrics'] = filtered_metrics
    return metrics

@app.get("/api/sprints")
async def get_sprints():
    """Get list of all available sprints with their basic info"""
    try:
        if analyzer is None:
            init_analyzer()
            
        sprints_data = []
        for _, sprint in analyzer.sprints_df.iterrows():
            sprints_data.append({
                "id": sprint['sprint_name'],
                "status": sprint['sprint_status'],
                "start_date": sprint['sprint_start_date'].strftime("%Y-%m-%d"),
                "end_date": sprint['sprint_end_date'].strftime("%Y-%m-%d"),
                "task_count": len(sprint['entity_ids']) if isinstance(sprint['entity_ids'], set) else 0
            })
            
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
                "task_count": count
            }
            for area, count in area_counts.items()
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

if __name__ == "__main__":
    try:
        logger.info("Starting server...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise 