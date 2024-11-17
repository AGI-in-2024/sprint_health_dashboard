from datetime import datetime, timedelta
import pandas as pd
import json
import logging

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

def calculate_todo(tasks_df):
    """Calculate sum of estimations for tasks in 'To Do' status"""
    # Convert status and resolution to lowercase before comparison
    tasks_df['status'] = tasks_df['status'].str.lower()
    tasks_df['resolution'] = tasks_df['resolution'].str.lower()
    
    # According to requirements, "К выполнению" category includes tasks in "Создано" status
    todo_statuses = {
        'к выполнению', 'создано', 'готово к разработке', 'новый', 
        'открыто', 'запланировано', 'отложен', 'в ожидании'
    }
    
    # Log unique statuses for debugging
    logger.info(f"\nUnique statuses before todo filtering: {tasks_df['status'].unique()}")
    
    todo_tasks = tasks_df[
        (tasks_df['status'].isin(todo_statuses)) &
        # Only include tasks with no resolution or non-terminal resolutions
        ((tasks_df['resolution'].isna()) | 
         (~tasks_df['resolution'].isin(['отклонено', 'отменено инициатором', 'дубликат'])))
    ]
    
    logger.info(f"Found {len(todo_tasks)} todo tasks")
    return round(todo_tasks['estimation'].sum() / 3600, 1), todo_statuses  # Return both value and statuses

def calculate_in_progress(tasks_df):
    """Calculate sum of estimations for tasks in 'In Progress' status"""
    # According to requirements, these are tasks not in Done or Removed categories
    done_statuses = {'закрыто', 'выполнено', 'ст завершено', 'завершено'}
    removed_resolutions = {'отклонено', 'отменено инициатором', 'дубликат', 'отклонен исполнителем'}
    
    # Get todo value and statuses
    _, todo_statuses = calculate_todo(tasks_df)
    
    in_progress_tasks = tasks_df[
        # Not in todo status
        (~tasks_df['status'].str.lower().isin(todo_statuses)) &
        # Not in done status
        (~tasks_df['status'].str.lower().isin(done_statuses)) &
        # Not removed
        ((tasks_df['resolution'].isna()) | 
         (~tasks_df['resolution'].str.lower().isin(removed_resolutions)))
    ]
    
    return round(in_progress_tasks['estimation'].sum() / 3600, 1)

def calculate_done(tasks_df):
    """Calculate sum of estimations for completed tasks"""
    # According to requirements: tasks in "Закрыто"/"Выполнено" status excluding removed ones
    done_statuses = {'закрыто', 'выполнено', 'ст завершено', 'завершено'}
    removed_resolutions = {'отклонено', 'отменено инициатором', 'дубликат', 'отклонен исполнителем'}
    
    done_tasks = tasks_df[
        (tasks_df['status'].str.lower().isin(done_statuses)) &
        # Not removed
        ((tasks_df['resolution'].isna()) | 
         (~tasks_df['resolution'].str.lower().isin(removed_resolutions)))
    ]
    
    logger.info(f"\nDone tasks count: {len(done_tasks)}")
    if not done_tasks.empty:
        logger.info("Sample done tasks statuses and resolutions:")
        logger.info(done_tasks['status'].value_counts().head())
        logger.info(done_tasks['resolution'].value_counts().head())
    
    return round(done_tasks['estimation'].sum() / 3600, 1)

def calculate_removed(tasks_df):
    """Calculate sum of estimations for removed tasks"""
    # According to requirements: tasks in "Закрыто"/"Выполнено" with specific resolutions
    done_statuses = {'закрыто', 'выполнено'}
    removed_resolutions = {
        'отклонено', 'отменено инициатором', 'дубликат', 
        'отклонен исполнителем'  # For defects
    }
    
    removed_tasks = tasks_df[
        (tasks_df['status'].str.lower().isin(done_statuses)) & 
        (tasks_df['resolution'].str.lower().isin(removed_resolutions))
    ]
    
    removed_sum = removed_tasks['estimation'].sum() / 3600
    logger.info(f"Removed tasks estimation sum: {removed_sum} hours")
    return round(removed_sum, 1)

def calculate_backlog_changes(tasks_df, sprint_info, history_df):
    """Calculate percentage of backlog changes after sprint start"""
    sprint_start = sprint_info['sprint_start_date']
    two_days_after = sprint_start + timedelta(days=2)
    
    # Get tasks added before sprint start + 2 days
    initial_tasks = tasks_df[tasks_df['create_date'] <= two_days_after]
    initial_estimation = initial_tasks['estimation'].sum()
    
    # Get tasks added after sprint start + 2 days
    added_tasks = tasks_df[tasks_df['create_date'] > two_days_after]
    added_estimation = added_tasks['estimation'].sum()
    
    if initial_estimation == 0:
        return 0.0
    
    change_percentage = round(added_estimation * 100 / initial_estimation, 1)
    return change_percentage

def calculate_blocked_tasks(tasks_df):
    """Calculate sum of estimations for blocked tasks in work days (Ч/Д)"""
    # If links column doesn't exist, return 0
    if 'links' not in tasks_df.columns:
        logger.info("No 'links' column found. Blocked tasks count: 0")
        return 0.0
        
    blocked_tasks = tasks_df[
        tasks_df['links'].apply(lambda x: ('заблокировано' in x.lower() or 'is blocked by' in x.lower()) if pd.notnull(x) else False) &
        (~tasks_df['status'].str.lower().isin(['закрыто', 'выполнено', 'done']))
    ]
    blocked_sum = blocked_tasks['estimation'].sum() / 3600
    logger.info(f"Blocked tasks estimation sum: {blocked_sum} hours")
    return round(blocked_sum, 1)

def calculate_excluded_tasks(tasks_df, sprint_info, history_df):
    """Calculate sum of estimations and count of tasks excluded from sprint on each day."""
    # Check if history_df is empty or missing required columns
    if history_df.empty or 'history_property_name' not in history_df.columns:
        logger.info("No history data available for excluded tasks calculation")
        return {}
        
    sprint_start = sprint_info['sprint_start_date']
    sprint_end = sprint_info['sprint_end_date']
    
    # Filter history for sprint field changes
    sprint_changes = history_df[
        (history_df['history_property_name'] == 'Спринт') &
        (history_df['history_date'] >= sprint_start) &
        (history_df['history_date'] <= sprint_end)
    ]
    
    # Track daily changes
    daily_excluded = {}
    
    for _, change in sprint_changes.iterrows():
        date = change['history_date'].date()
        entity_id = change['entity_id']
    
        history_change = change['history_change']
        if isinstance(history_change, str) and "-> <empty>" in history_change:
            # Check if task was removed from sprint
            task = tasks_df[tasks_df['entity_id'] == entity_id]
            if not task.empty:
                estimation = pd.to_numeric(task['estimation'], errors='coerce').fillna(0).iloc[0] / 3600
                if date not in daily_excluded:
                    daily_excluded[date] = {'hours': 0, 'count': 0}
                daily_excluded[date]['hours'] += estimation
                daily_excluded[date]['count'] += 1
    
    logger.info(f"Excluded tasks daily changes: {daily_excluded}")
    return daily_excluded

def calculate_added_tasks(tasks_df, sprint_info, history_df):
    """Calculate sum of estimations and count of tasks added to sprint on each day."""
    # Check if history_df is empty or missing required columns
    if history_df.empty or 'history_property_name' not in history_df.columns:
        logger.info("No history data available for added tasks calculation")
        return {}
        
    sprint_start = sprint_info['sprint_start_date']
    sprint_end = sprint_info['sprint_end_date']
    
    # Filter history for sprint field changes
    sprint_changes = history_df[
        (history_df['history_property_name'] == 'Спринт') &
        (history_df['history_date'] >= sprint_start) &
        (history_df['history_date'] <= sprint_end)
    ]
    
    # Track daily changes
    daily_added = {}
    
    for _, change in sprint_changes.iterrows():
        date = change['history_date'].date()
        entity_id = change['entity_id']
    
        history_change = change['history_change']
        if isinstance(history_change, str) and "<empty> ->" in history_change:
            # Check if task was added to sprint
            task = tasks_df[tasks_df['entity_id'] == entity_id]
            if not task.empty:
                estimation = pd.to_numeric(task['estimation'], errors='coerce').fillna(0).iloc[0] / 3600
                if date not in daily_added:
                    daily_added[date] = {'hours': 0, 'count': 0}
                daily_added[date]['hours'] += estimation
                daily_added[date]['count'] += 1
    
    logger.info(f"Added tasks daily changes: {daily_added}")
    return daily_added

def analyze_status_transitions(tasks_df, history_df, sprint_info):
    """Analyze how evenly tasks transition through statuses"""
    # Check if history_df is empty or missing required columns
    if history_df.empty or 'history_property_name' not in history_df.columns:
        logger.info("No history data available for status transitions analysis")
        return {
            'last_day_completion_percentage': 0,
            'daily_distribution': {},
            'transition_evenness': 0
        }
        
    sprint_start = pd.to_datetime(sprint_info['sprint_start_date'])
    sprint_end = pd.to_datetime(sprint_info['sprint_end_date'])
    # Calculate sprint_duration as a timedelta
    sprint_duration = sprint_end - sprint_start
    
    # Filter status changes during sprint
    status_changes = history_df[
        (history_df['history_property_name'] == 'Статус') &
        (history_df['history_date'] >= sprint_start) &
        (history_df['history_date'] <= sprint_end)
    ]
    
    # Group changes by day
    daily_stats = {}
    # Expand status transitions patterns
    status_transitions = {
        'to_in_progress': [
            'создано -> в работе',
            'к выполнению -> в работе',
            'анализ -> разработка',
            'готово к разработке -> в разработке',
            '-> в работе',
            '-> разработка',
            '-> тестирование',
            'создано -> разработка',
            'создано -> анализ',
            '-> в процессе',
            '-> исправление'
        ],
        'to_done': [
            '-> выполнено',
            '-> закрыто',
            '-> ст завершено',
            '-> завершено',
            'в работе -> закрыто',
            'тестирование -> закрыто',
            'разработка -> выполнено'
        ]
    }
    
    # Add debug logging for transitions
    for _, change in status_changes.iterrows():
        history_change = str(change['history_change']).lower()
        logger.debug(f"Processing status change: {history_change}")
        
        date = change['history_date'].date()
        if date not in daily_stats:
            daily_stats[date] = {
                'to_in_progress': 0,
                'to_done': 0,
                'total_changes': 0
            }
        
        # Check for status transitions
        for transition in status_transitions['to_in_progress']:
            if transition in history_change:
                daily_stats[date]['to_in_progress'] += 1
                break
                
        for transition in status_transitions['to_done']:
            if transition in history_change:
                daily_stats[date]['to_done'] += 1
                break
                
        daily_stats[date]['total_changes'] += 1
    
    # Calculate transition metrics
    total_days = len(daily_stats)
    total_to_done = sum(day['to_done'] for day in daily_stats.values())
    last_day_done = daily_stats.get(sprint_end.date(), {}).get('to_done', 0)
    
    # Calculate transition evenness
    evenness = calculate_transition_evenness(daily_stats, sprint_duration)
    
    logger.info(f"Total days with changes: {total_days}")
    logger.info(f"Total tasks done: {total_to_done}")
    logger.info(f"Last day done: {last_day_done}")
    
    return {
        'last_day_completion_percentage': (last_day_done / total_to_done * 100) if total_to_done > 0 else 0,
        'daily_distribution': daily_stats,
        'transition_evenness': evenness
    }

def calculate_transition_evenness(daily_stats, sprint_duration):
    """Calculate how evenly tasks transition through statuses"""
    if not daily_stats:
        return 0
    
    # Ensure sprint_duration is a timedelta and get days as int
    if isinstance(sprint_duration, pd.Timedelta):
        duration_days = sprint_duration.days
    else:
        # If somehow sprint_duration is not a timedelta, calculate it safely
        duration_days = max(1, len(daily_stats))
    
    # Calculate ideal daily changes
    total_changes = sum(day['total_changes'] for day in daily_stats.values())
    ideal_daily = total_changes / duration_days if duration_days > 0 else 0
    
    # Calculate variance from ideal
    actual_days = len(daily_stats)
    if actual_days == 0 or ideal_daily == 0:
        evenness = 0
    else:
        variance = sum(
            abs(day['total_changes'] - ideal_daily) 
            for day in daily_stats.values()
        ) / actual_days
        
        # Convert to percentage where 100% is perfectly even
        evenness = max(0, 100 - (variance / ideal_daily * 100)) if ideal_daily > 0 else 0
    
    logger.info(f"Sprint duration (days): {duration_days}")
    logger.info(f"Total changes: {total_changes}")
    logger.info(f"Ideal daily changes: {ideal_daily:.2f}")
    logger.info(f"Transition evenness: {evenness:.1f}%")
    
    return evenness

def calculate_sprint_health(metrics, tasks_df, history_df, sprint_info):
    """Calculate simplified sprint health score"""
    try:
        total_tasks = metrics['todo'] + metrics['in_progress'] + metrics['done'] + metrics['removed']
        if total_tasks == 0:
            return {
                'score': 0,
                'details': {
                    'delivery_score': 0,
                    'stability_score': 0,
                    'flow_score': 0,
                    'quality_score': 0,
                    'team_load_score': 0,
                    'completion_rate': 0,
                    'blocked_ratio': 0,
                    'last_day_completion': 0
                }
            }

        # Calculate basic metrics
        completion_rate = (metrics['done'] / total_tasks) * 100 if total_tasks > 0 else 0
        blocked_ratio = (metrics['blocked_tasks'] / total_tasks) * 100 if total_tasks > 0 else 0
        last_day_completion = metrics.get('status_transitions', {}).get('last_day_completion_percentage', 0)

        # Calculate category scores
        delivery_score = min(100, max(0, completion_rate))
        stability_score = min(100, max(0, 100 - metrics['backlog_changes']))
        flow_score = min(100, max(0, 100 - blocked_ratio))
        quality_score = min(100, max(0, 100 - last_day_completion))
        team_load_score = 80  # Default score if no specific calculation

        # Calculate final health score
        health_score = (
            delivery_score * 0.25 +
            stability_score * 0.20 +
            flow_score * 0.20 +
            quality_score * 0.20 +
            team_load_score * 0.15
        )

        return {
            'score': round(health_score, 1),
            'details': {
                'delivery_score': round(delivery_score, 1),
                'stability_score': round(stability_score, 1),
                'flow_score': round(flow_score, 1),
                'quality_score': round(quality_score, 1),
                'team_load_score': round(team_load_score, 1),
                'completion_rate': round(completion_rate, 1),
                'blocked_ratio': round(blocked_ratio, 1),
                'last_day_completion': round(last_day_completion, 1)
            }
        }
    except Exception as e:
        logger.error(f"Error calculating sprint health: {str(e)}")
        return {
            'score': 0,
            'details': {
                'delivery_score': 0,
                'stability_score': 0,
                'flow_score': 0,
                'quality_score': 0,
                'team_load_score': 0,
                'completion_rate': 0,
                'blocked_ratio': 0,
                'last_day_completion': 0
            }
        }

def _calculate_base_metrics(sprint_tasks, sprint_info, history_df):
    """Calculate all base metrics for the sprint up to the selected time frame."""
    try:
        # Ensure 'estimation' is numeric
        sprint_tasks['estimation'] = pd.to_numeric(sprint_tasks['estimation'], errors='coerce').fillna(0)
        
        # Calculate individual metrics
        todo_value, _ = calculate_todo(sprint_tasks)  # Unpack the tuple
        in_progress = calculate_in_progress(sprint_tasks)
        done = calculate_done(sprint_tasks)
        removed = calculate_removed(sprint_tasks)
        backlog_changes = calculate_backlog_changes(sprint_tasks, sprint_info, history_df)
        blocked_tasks = calculate_blocked_tasks(sprint_tasks)
        excluded_tasks = calculate_excluded_tasks(sprint_tasks, sprint_info, history_df)
        added_tasks = calculate_added_tasks(sprint_tasks, sprint_info, history_df)
        status_transitions = analyze_status_transitions(sprint_tasks, history_df, sprint_info)
        
        sprint_health = calculate_sprint_health({
            'todo': todo_value,
            'in_progress': in_progress,
            'done': done,
            'removed': removed,
            'backlog_changes': backlog_changes,
            'blocked_tasks': blocked_tasks,
            'status_transitions': status_transitions
        }, sprint_tasks, history_df, sprint_info)
        
        return {
            'todo': todo_value,
            'in_progress': in_progress,
            'done': done,
            'removed': removed,
            'backlog_changes': backlog_changes,
            'blocked_tasks': blocked_tasks,
            'excluded_tasks': excluded_tasks,
            'added_tasks': added_tasks,
            'status_transitions': status_transitions,
            'health_score': sprint_health['score'],
            'health_details': sprint_health['details']
        }
    except Exception as e:
        logger.error(f"Error in _calculate_base_metrics: {str(e)}")
        raise

def validate_task_data(tasks_df):
    """Enhanced task data validation"""
    validation_results = {
        'missing_status': tasks_df['status'].isna().sum(),
        'missing_resolution': tasks_df['resolution'].isna().sum(),
        'missing_estimation': tasks_df['estimation'].isna().sum(),
        'unique_statuses': sorted(tasks_df['status'].unique().tolist()),
        'unique_resolutions': sorted(tasks_df['resolution'].dropna().unique().tolist()),
        'status_counts': tasks_df['status'].value_counts().to_dict(),
        'resolution_counts': tasks_df['resolution'].value_counts().to_dict()
    }
    
    logger.info("\nDetailed Data Quality Validation:")
    logger.info(f"Missing status: {validation_results['missing_status']}")
    logger.info(f"Missing resolution: {validation_results['missing_resolution']}")
    logger.info(f"Missing estimation: {validation_results['missing_estimation']}")
    logger.info("\nStatus Distribution:")
    for status, count in validation_results['status_counts'].items():
        logger.info(f"- {status}: {count}")
    logger.info("\nResolution Distribution:")
    for resolution, count in validation_results['resolution_counts'].items():
        logger.info(f"- {resolution}: {count}")
    
    return validation_results

def calculate_metrics(tasks, sprints, history_df, selected_sprints, selected_areas, time_frame):
    """Calculate metrics with improved logging and validation"""
    try:
        # Input validation and logging
        logger.info(f"\nCalculating metrics for:")
        logger.info(f"Selected sprints: {selected_sprints}")
        logger.info(f"Selected areas: {selected_areas}")
        logger.info(f"Time frame: {time_frame}%")
        
        # Log initial data shapes
        logger.info(f"\nInitial data shapes:")
        logger.info(f"Tasks: {tasks.shape}")
        logger.info(f"Sprints: {sprints.shape}")
        logger.info(f"History: {history_df.shape}")
        
        if sprints.empty:
            raise ValueError("No sprint data available")
            
        # Get sprint information
        sprint_info = sprints[sprints['sprint_name'].isin(selected_sprints)]
        if sprint_info.empty:
            raise ValueError(f"No sprint found with names: {selected_sprints}")
        sprint_info = sprint_info.iloc[0]
        
        # Handle empty tasks DataFrame
        if tasks.empty:
            logger.info("No tasks data available - returning zero metrics")
            return {
                'todo': 0.0,
                'in_progress': 0.0,
                'done': 0.0,
                'removed': 0.0,
                'backlog_changes': 0.0,
                'blocked_tasks': 0.0,
                'excluded_tasks': {},
                'added_tasks': {},
                'status_transitions': {
                    'last_day_completion_percentage': 0,
                    'daily_distribution': {},
                    'transition_evenness': 0
                },
                'health_score': 0,
                'health_details': {},
                'health_metrics': {
                    'todo_percentage': 0,
                    'removed_percentage': 0,
                    'backlog_change_percentage': 0,
                    'transition_evenness': 0,
                    'last_day_completion_percentage': 0
                }
            }
        
        # Calculate time frame dates
        sprint_start = pd.to_datetime(sprint_info['sprint_start_date'])
        sprint_end = pd.to_datetime(sprint_info['sprint_end_date'])
        sprint_duration = sprint_end - sprint_start
        selected_end_date = sprint_start + sprint_duration * (time_frame / 100)
        
        logger.info(f"\nTime frame dates:")
        logger.info(f"Sprint start: {sprint_start}")
        logger.info(f"Selected end: {selected_end_date}")
        
        # Modified time frame filtering
        tasks_in_sprint = tasks[
            (tasks['entity_id'].isin(sprint_info['entity_ids'])) &
            (
                (tasks['create_date'] <= selected_end_date) |
                (tasks['update_date'] <= selected_end_date) |
                (pd.isna(tasks['update_date']) & (tasks['create_date'] <= selected_end_date))
            )
        ].copy()
        
        # Add debug logging
        logger.info(f"\nTasks before time frame filter: {len(tasks)}")
        logger.info(f"Tasks after time frame filter: {len(tasks_in_sprint)}")
        
        # Normalize status and resolution immediately after filtering
        tasks_in_sprint['status'] = tasks_in_sprint['status'].str.lower().str.strip()
        tasks_in_sprint['resolution'] = tasks_in_sprint['resolution'].str.lower().str.strip()
        
        # Log status distribution before area filtering
        logger.info("\nStatus distribution before area filter:")
        logger.info(tasks_in_sprint['status'].value_counts())
        
        logger.info(f"\nTasks in sprint: {len(tasks_in_sprint)}")
        
        sprint_tasks = tasks_in_sprint[
            tasks_in_sprint['area'].isin(selected_areas)
        ].copy()
        
        logger.info(f"Tasks after area filter: {len(sprint_tasks)}")
        
        # Log status distribution for filtered tasks
        logger.info("\nStatus distribution in filtered tasks:")
        logger.info(sprint_tasks['status'].value_counts())
        
        # Add data validation after filtering
        validate_task_data(sprint_tasks)
        
        # Calculate metrics
        metrics = _calculate_base_metrics(sprint_tasks, sprint_info, history_df)
        
        logger.info("\nCalculated metrics summary:")
        logger.info(f"Todo: {metrics['todo']}")
        logger.info(f"In Progress: {metrics['in_progress']}")
        logger.info(f"Done: {metrics['done']}")
        logger.info(f"Removed: {metrics['removed']}")
        logger.info(f"Health Score: {metrics['health_score']}")
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error in calculate_metrics: {str(e)}")
        raise