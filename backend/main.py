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
from urllib.parse import unquote
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
from pydantic import BaseModel

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
    """Get list of all available sprints with better error handling"""
    try:
        if data_loader.sprints.empty:
            # Generate sprints per area
            areas = data_loader.tasks['area'].unique()
            synthetic_sprints = []
            
            for area in areas:
                area_tasks = data_loader.tasks[data_loader.tasks['area'] == area]
                if area_tasks.empty:
                    continue
                    
                start_date = area_tasks['create_date'].min()
                end_date = area_tasks['create_date'].max()
                
                # Create 2-week sprints between start and end dates
                sprint_dates = pd.date_range(start=start_date, end=end_date, freq='2W')
                
                for i in range(len(sprint_dates) - 1):
                    sprint_start = sprint_dates[i]
                    sprint_end = sprint_dates[i + 1]
                    
                    # Get tasks created during this sprint
                    sprint_tasks = area_tasks[
                        (area_tasks['create_date'] >= sprint_start) &
                        (area_tasks['create_date'] < sprint_end)
                    ]
                    
                    if not sprint_tasks.empty:
                        sprint_name = f"Sprint {i+1} - {area} ({sprint_start.strftime('%Y.%m.%d')})"
                        synthetic_sprints.append({
                            'sprint_name': sprint_name,
                            'sprint_start_date': sprint_start,
                            'sprint_end_date': sprint_end,
                            'entity_ids': sprint_tasks['entity_id'].tolist(),
                            'area': area
                        })
            
            # Update data_loader.sprints with synthetic data
            data_loader.sprints = pd.DataFrame(synthetic_sprints)
            logger.info(f"Generated {len(synthetic_sprints)} synthetic sprints across {len(areas)} areas")
            
        return {
            "sprints": data_loader.sprints['sprint_name'].tolist()
        }
    except Exception as e:
        logger.error(f"Error in get_sprints: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get sprints: {str(e)}"
        )

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
    
    try:
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
        
        # Get sprint info
        sprint_info = data_loader.sprints[
            data_loader.sprints['sprint_name'].isin(selected_sprints)
        ]
        
        if sprint_info.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for selected sprints: {selected_sprints}"
            )
        
        # Calculate metrics
        metrics = calculate_metrics(
            data_loader.tasks,
            sprint_info,
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

@app.get("/api/sprint-statistics/{sprint_name}")
async def get_sprint_statistics(sprint_name: str):
    """Get detailed statistics for a specific sprint"""
    try:
        sprint_info = data_loader.sprints[
            data_loader.sprints['sprint_name'] == sprint_name
        ]
        
        if sprint_info.empty:
            raise HTTPException(status_code=404, detail=f"Sprint {sprint_name} not found")
            
        sprint_info = sprint_info.iloc[0]
        sprint_tasks = data_loader.tasks[
            data_loader.tasks['entity_id'].isin(sprint_info['entity_ids'])
        ]
        
        # Calculate basic metrics
        total_tasks = len(sprint_tasks)
        completed_tasks = len(sprint_tasks[
            sprint_tasks['status'].str.lower().isin(['закрыто', 'выполнено'])
        ])
        
        # Ensure numeric types
        sprint_tasks['estimation'] = pd.to_numeric(sprint_tasks['estimation'], errors='coerce').fillna(0)
        sprint_tasks['spent'] = pd.to_numeric(sprint_tasks['spent'], errors='coerce').fillna(0)
        
        return {
            "sprint_name": sprint_name,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "status_distribution": sprint_tasks['status'].value_counts().to_dict(),
            "priority_distribution": sprint_tasks['priority'].value_counts().to_dict(),
            "type_distribution": sprint_tasks['type'].value_counts().to_dict(),
            "average_metrics": {
                "estimation": float(sprint_tasks['estimation'].mean() / 3600),
                "spent": float(sprint_tasks['spent'].mean() / 3600),
                "efficiency": float((sprint_tasks['spent'].sum() / sprint_tasks['estimation'].sum() * 100)
                                 if sprint_tasks['estimation'].sum() > 0 else 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating sprint statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workload-analysis")
async def get_workload_analysis(
    selected_sprints: Optional[List[str]] = Query(None, alias="selected_sprints[]")
):
    """Get workload analysis across sprints"""
    try:
        if not selected_sprints:
            raise HTTPException(status_code=422, detail="No sprints selected")
            
        all_tasks = []
        for sprint in selected_sprints:
            sprint_info = data_loader.sprints[
                data_loader.sprints['sprint_name'] == sprint
            ]
            if sprint_info.empty:
                continue
                
            sprint_tasks = data_loader.tasks[
                data_loader.tasks['entity_id'].isin(sprint_info.iloc[0]['entity_ids'])
            ]
            all_tasks.append(sprint_tasks)
            
        if not all_tasks:
            raise HTTPException(status_code=404, detail="No tasks found for selected sprints")
            
        combined_tasks = pd.concat(all_tasks)
        
        # Calculate workload metrics
        assignee_workload = combined_tasks.groupby('assignee').agg({
            'entity_id': 'count',
            'estimation': 'sum',
            'spent': 'sum'
        }).fillna(0).to_dict('index')
        
        # Calculate team efficiency
        workgroup_efficiency = combined_tasks.groupby('workgroup').agg({
            'entity_id': 'count',
            'estimation': 'mean',
            'spent': 'mean'
        }).fillna(0).to_dict('index')
        
        return {
            "assignee_workload": assignee_workload,
            "workgroup_efficiency": workgroup_efficiency,
            "priority_distribution": combined_tasks['priority'].value_counts().to_dict(),
            "overall_metrics": {
                "total_tasks": len(combined_tasks),
                "total_estimation": float(combined_tasks['estimation'].sum() / 3600),
                "total_spent": float(combined_tasks['spent'].sum() / 3600),
                "average_task_completion_time": float(combined_tasks['spent'].mean() / 3600)
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating workload analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trend-analysis")
async def get_trend_analysis(
    selected_sprints: Optional[List[str]] = Query(None, alias="selected_sprints[]")
):
    """Get trend analysis across multiple sprints"""
    try:
        if not selected_sprints:
            raise HTTPException(status_code=422, detail="No sprints selected")
            
        trends = []
        for sprint in selected_sprints:
            sprint_info = data_loader.sprints[
                data_loader.sprints['sprint_name'] == sprint
            ]
            if sprint_info.empty:
                continue
                
            sprint_info = sprint_info.iloc[0]
            sprint_tasks = data_loader.tasks[
                data_loader.tasks['entity_id'].isin(sprint_info['entity_ids'])
            ]
            
            # Calculate metrics for this sprint
            total_tasks = len(sprint_tasks)
            completed_tasks = len(sprint_tasks[
                sprint_tasks['status'].str.lower().isin(['закрыто', 'выполнено'])
            ])
            
            sprint_history = data_loader.history[
                data_loader.history['entity_id'].isin(sprint_tasks['entity_id'])
            ]
            
            trends.append({
                "sprint_name": sprint,
                "metrics": {
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                    "average_completion_time": float(sprint_tasks['spent'].mean() / 3600)
                },
                "daily_activity": sprint_history.groupby('date')['entity_id'].count().to_dict(),
                "status_distribution": sprint_tasks['status'].value_counts().to_dict()
            })
            
        if not trends:
            raise HTTPException(status_code=404, detail="No trend data found for selected sprints")
            
        return {
            "trends": trends,
            "comparative_analysis": {
                "average_completion_rate": sum(t["metrics"]["completion_rate"] for t in trends) / len(trends),
                "task_volume_trend": [t["metrics"]["total_tasks"] for t in trends],
                "completion_time_trend": [t["metrics"]["average_completion_time"] for t in trends]
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating trend analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/plot-data/task-flow")
async def get_task_flow(
    selected_sprints: List[str] = Query(None, alias="selected_sprints[]"),
    selected_areas: List[str] = Query(None, alias="selected_areas[]")
) -> List[TaskFlow]:
    """Get task flow data for visualization"""
    try:
        if not selected_sprints or not selected_areas:
            raise HTTPException(status_code=400, detail="Missing required parameters")

        sprint_info = data_loader.sprints[
            data_loader.sprints['sprint_name'].isin(selected_sprints)
        ]

        result = []
        for _, sprint in sprint_info.iterrows():
            sprint_tasks = data_loader.tasks[
                (data_loader.tasks['entity_id'].isin(sprint['entity_ids'])) &
                (data_loader.tasks['area'].isin(selected_areas))
            ]

            # Get status changes from history
            status_changes = data_loader.history[
                (data_loader.history['entity_id'].isin(sprint_tasks['entity_id'])) &
                (data_loader.history['history_property_name'] == 'Статус')
            ]

            # Generate daily status flow
            sprint_start = pd.to_datetime(sprint['sprint_start_date'])
            sprint_end = pd.to_datetime(sprint['sprint_end_date'])
            dates = pd.date_range(sprint_start, sprint_end)

            status_flow = []
            for date in dates:
                tasks_at_date = sprint_tasks[sprint_tasks['create_date'] <= date]
                status_counts = {
                    'date': date.strftime('%Y-%m-%d'),
                    'todo': len(tasks_at_date[tasks_at_date['status'].str.lower().isin(['создано', 'к выполнению'])]),
                    'in_progress': len(tasks_at_date[tasks_at_date['status'].str.lower().isin(['в работе', 'в процессе'])]),
                    'done': len(tasks_at_date[tasks_at_date['status'].str.lower().isin(['закрыто', 'выполнено'])]),
                    'blocked': len(tasks_at_date[tasks_at_date['links'].str.contains('заблокировано|is blocked by', case=False, na=False)]),
                    'removed': len(tasks_at_date[tasks_at_date['resolution'].str.lower().isin(['отклонено', 'отменено'])])
                }
                status_flow.append(status_counts)

            result.append({
                'sprint_name': sprint['sprint_name'],
                'status_flow': status_flow
            })

        return result

    except Exception as e:
        logger.error(f"Error getting task flow data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/plot-data/task-distribution")
async def get_task_distribution(
    selected_sprints: List[str] = Query(None, alias="selected_sprints[]"),
    selected_areas: List[str] = Query(None, alias="selected_areas[]")
) -> List[TaskDistribution]:
    """Get task distribution data for visualization"""
    try:
        if not selected_sprints or not selected_areas:
            raise HTTPException(status_code=400, detail="Missing required parameters")

        result = []
        for sprint_name in selected_sprints:
            sprint_info = data_loader.sprints[
                data_loader.sprints['sprint_name'] == sprint_name
            ].iloc[0]

            sprint_tasks = data_loader.tasks[
                (data_loader.tasks['entity_id'].isin(sprint_info['entity_ids'])) &
                (data_loader.tasks['area'].isin(selected_areas))
            ]

            # Calculate status distribution
            status_dist = {
                'todo': len(sprint_tasks[sprint_tasks['status'].str.lower().isin(['создано', 'к выполнению'])]),
                'in_progress': len(sprint_tasks[sprint_tasks['status'].str.lower().isin(['в работе', 'в процессе'])]),
                'done': len(sprint_tasks[sprint_tasks['status'].str.lower().isin(['закрыто', 'выполнено'])]),
                'removed': len(sprint_tasks[sprint_tasks['resolution'].str.lower().isin(['отклонено', 'отменено'])])
            }

            # Calculate workload distribution by assignee
            workload_dist = {}
            for assignee in sprint_tasks['assignee'].unique():
                if pd.isna(assignee): continue
                assignee_tasks = sprint_tasks[sprint_tasks['assignee'] == assignee]
                workload_dist[assignee] = {
                    'estimation': assignee_tasks['estimation'].sum() / 3600,
                    'spent': assignee_tasks['spent'].sum() / 3600
                }

            result.append({
                'sprint_name': sprint_name,
                'status_distribution': status_dist,
                'workload_distribution': workload_dist
            })

        return result

    except Exception as e:
        logger.error(f"Error getting task distribution data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/plot-data/sprint-health-indicators")
async def get_sprint_health_indicators(
    selected_sprints: List[str] = Query(None, alias="selected_sprints[]"),
    selected_areas: List[str] = Query(None, alias="selected_areas[]")
) -> List[HealthIndicator]:
    """Get health indicators for sprints"""
    try:
        if not selected_sprints or not selected_areas:
            raise HTTPException(status_code=400, detail="Missing required parameters")

        result = []
        for sprint_name in selected_sprints:
            sprint_info = data_loader.sprints[
                data_loader.sprints['sprint_name'] == sprint_name
            ].iloc[0]

            sprint_tasks = data_loader.tasks[
                (data_loader.tasks['entity_id'].isin(sprint_info['entity_ids'])) &
                (data_loader.tasks['area'].isin(selected_areas))
            ]

            total_tasks = len(sprint_tasks)
            if total_tasks == 0:
                continue

            # Calculate metrics
            todo_count = len(sprint_tasks[sprint_tasks['status'].str.lower().isin(['создано', 'к выполнению'])])
            removed_count = len(sprint_tasks[sprint_tasks['resolution'].str.lower().isin(['отклонено', 'отменено'])])
            completed_count = len(sprint_tasks[sprint_tasks['status'].str.lower().isin(['закрыто', 'выполнено'])])
            blocked_count = len(sprint_tasks[sprint_tasks['links'].str.contains('заблокировано|is blocked by', case=False, na=False)])

            # Calculate transition evenness from history
            status_changes = data_loader.history[
                (data_loader.history['entity_id'].isin(sprint_tasks['entity_id'])) &
                (data_loader.history['history_property_name'] == 'Статус')
            ]
            
            # Group changes by day and calculate evenness
            daily_changes = status_changes.groupby(status_changes['history_date'].dt.date).size()
            transition_evenness = 100 * (1 - daily_changes.std() / daily_changes.mean()) if len(daily_changes) > 0 else 0

            metrics = {
                'todo_percentage': (todo_count / total_tasks) * 100,
                'removed_percentage': (removed_count / total_tasks) * 100,
                'transition_evenness': transition_evenness,
                'total_tasks': total_tasks,
                'completed_tasks': completed_count,
                'blocked_tasks': blocked_count
            }

            # Calculate health score
            health_score = 100
            if metrics['todo_percentage'] > 20:
                health_score -= min(25, metrics['todo_percentage'] - 20)
            if metrics['removed_percentage'] > 10:
                health_score -= min(25, metrics['removed_percentage'] - 10)
            if metrics['transition_evenness'] < 70:
                health_score -= min(25, 70 - metrics['transition_evenness'])
            if metrics['blocked_tasks'] / total_tasks > 0.1:
                health_score -= min(25, (metrics['blocked_tasks'] / total_tasks * 100) - 10)

            result.append({
                'sprint_name': sprint_name,
                'metrics': metrics,
                'health_score': max(0, health_score)
            })

        return result

    except Exception as e:
        logger.error(f"Error getting health indicators: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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