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
    todo_tasks = tasks_df[tasks_df['status'].str.lower().isin([
        'к выполнению', 'создано', 'готово к разработке', 'анализ'
    ])]
    return round(todo_tasks['estimation'].sum() / 3600, 1)

def calculate_in_progress(tasks_df):
    """Calculate sum of estimations for tasks in 'In Progress' status"""
    in_progress_tasks = tasks_df[tasks_df['status'].str.lower().isin([
        'в работе', 'в процессе', 'тестирование', 'разработка', 
        'исправление', 'ст', 'локализация'
    ])]
    return round(in_progress_tasks['estimation'].sum() / 3600, 1)

def calculate_done(tasks_df):
    """Calculate sum of estimations for completed tasks"""
    done_tasks = tasks_df[
        (tasks_df['status'].str.lower().isin(['закрыто', 'выполнено', 'ст завершено'])) & 
        (~tasks_df['resolution'].str.lower().isin(['отклонено', 'отменено инициатором', 'дубликат', 'отклонен исполнителем']))
    ]
    return round(done_tasks['estimation'].sum() / 3600, 1)

def calculate_removed(tasks_df):
    """Calculate sum of estimations for removed tasks"""
    removed_tasks = tasks_df[
        (tasks_df['status'].str.lower().isin(['закрыто', 'выполнено'])) & 
        (tasks_df['resolution'].str.lower().isin(['отклонено', 'отменено инициатором', 'дубликат', 'отклонен исполнителем']))
    ]
    return round(removed_tasks['estimation'].sum() / 3600, 1)

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
        return 0.0
        
    blocked_tasks = tasks_df[
        tasks_df['links'].apply(lambda x: ('Заблокировано' in x or 'is blocked by' in x) if pd.notnull(x) else False) &
        (~tasks_df['status'].str.lower().isin(['закрыто', 'выполнено', 'done']))
    ]
    return round(blocked_tasks['estimation'].sum() / 3600, 1)

def calculate_excluded_tasks(tasks_df, sprint_info, history_df):
    """Calculate sum of estimations and count of tasks excluded from sprint on each day."""
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
                estimation = task['estimation'].iloc[0] / 3600
                if date not in daily_excluded:
                    daily_excluded[date] = {'hours': 0, 'count': 0}
                daily_excluded[date]['hours'] += estimation
                daily_excluded[date]['count'] += 1

    return daily_excluded

def calculate_added_tasks(tasks_df, sprint_info, history_df):
    """Calculate sum of estimations and count of tasks added to sprint on each day."""
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
                estimation = task['estimation'].iloc[0] / 3600
                if date not in daily_added:
                    daily_added[date] = {'hours': 0, 'count': 0}
                daily_added[date]['hours'] += estimation
                daily_added[date]['count'] += 1

    return daily_added

def analyze_status_transitions(tasks_df, history_df, sprint_info):
    """Analyze how evenly tasks transition through statuses"""
    sprint_start = sprint_info['sprint_start_date']
    sprint_end = sprint_info['sprint_end_date']
    sprint_duration = (sprint_end - sprint_start).days
    
    # Filter status changes during sprint
    status_changes = history_df[
        (history_df['history_property_name'] == 'Статус') &
        (history_df['history_date'] >= sprint_start) &
        (history_df['history_date'] <= sprint_end)
    ]
    
    # Group changes by day
    daily_stats = {}
    for _, change in status_changes.iterrows():
        date = change['history_date'].date()
        if date not in daily_stats:
            daily_stats[date] = {
                'to_in_progress': 0,
                'to_done': 0,
                'total_changes': 0
            }
        
        # Ensure history_change is a string and handle NaN values
        history_change = str(change['history_change']) if pd.notna(change['history_change']) else ''
        change_str = history_change.lower()
        
        if 'к выполнению -> в работе' in change_str:
            daily_stats[date]['to_in_progress'] += 1
        elif '-> выполнено' in change_str or '-> закрыто' in change_str:
            daily_stats[date]['to_done'] += 1
        daily_stats[date]['total_changes'] += 1
    
    # Calculate transition metrics
    total_days = len(daily_stats)
    total_to_done = sum(day['to_done'] for day in daily_stats.values())
    last_day_done = daily_stats.get(sprint_end.date(), {}).get('to_done', 0)
    
    return {
        'last_day_completion_percentage': (last_day_done / total_to_done * 100) if total_to_done > 0 else 0,
        'daily_distribution': daily_stats,
        'transition_evenness': calculate_transition_evenness(daily_stats, sprint_duration)
    }

def calculate_transition_evenness(daily_stats, sprint_duration):
    """Calculate how evenly tasks transition through statuses"""
    if not daily_stats:
        return 0
    
    # Calculate ideal daily changes
    total_changes = sum(day['total_changes'] for day in daily_stats.values())
    ideal_daily = total_changes / sprint_duration
    
    # Calculate variance from ideal
    actual_days = len(daily_stats)
    variance = sum(
        abs(day['total_changes'] - ideal_daily) 
        for day in daily_stats.values()
    ) / actual_days
    
    # Convert to percentage where 100% is perfectly even
    evenness = max(0, 100 - (variance / ideal_daily * 100)) if ideal_daily > 0 else 0
    return evenness

def calculate_sprint_health(metrics, tasks_df, history_df, sprint_info):
    """Calculate overall sprint health based on all criteria"""
    health_score = 100
    health_details = {}
    
    # 1. Status transitions analysis
    transitions = analyze_status_transitions(tasks_df, history_df, sprint_info)
    
    # Penalty for uneven transitions (weight: 25%)
    evenness_score = transitions['transition_evenness']
    if evenness_score < 70:  # If transitions are less than 70% even
        penalty = min(25, (70 - evenness_score) * 0.5)
        health_score -= penalty
        health_details['transition_evenness_penalty'] = penalty
    
    # Penalty for last day completions (weight: 25%)
    if transitions['last_day_completion_percentage'] > 30:
        penalty = min(25, (transitions['last_day_completion_percentage'] - 30) * 0.5)
        health_score -= penalty
        health_details['last_day_completion_penalty'] = penalty
    
    # 2. Todo percentage check (weight: 20%)
    total_tasks = metrics['todo'] + metrics['in_progress'] + metrics['done'] + metrics['removed']
    if total_tasks > 0:
        todo_percentage = (metrics['todo'] / total_tasks) * 100
        if todo_percentage > 20:
            penalty = min(20, todo_percentage - 20)
            health_score -= penalty
            health_details['todo_penalty'] = penalty
    
    # 3. Removed tasks check (weight: 15%)
    if total_tasks > 0:
        removed_percentage = (metrics['removed'] / total_tasks) * 100
        if removed_percentage > 10:
            penalty = min(15, (removed_percentage - 10) * 1.5)
            health_score -= penalty
            health_details['removed_penalty'] = penalty
    
    # 4. Backlog changes check (weight: 15%)
    if metrics['backlog_changes'] > 20:
        penalty = min(15, metrics['backlog_changes'] - 20)
        health_score -= penalty
        health_details['backlog_penalty'] = penalty
    
    return {
        'score': max(0, min(100, health_score)),
        'details': health_details,
        'metrics_snapshot': {
            'todo_percentage': todo_percentage if total_tasks > 0 else 0,
            'removed_percentage': removed_percentage if total_tasks > 0 else 0,
            'backlog_change_percentage': metrics['backlog_changes'],
            'transition_evenness': evenness_score,
            'last_day_completion_percentage': transitions['last_day_completion_percentage']
        }
    }

def _calculate_base_metrics(sprint_tasks, sprint_info, history_df):
    """Calculate all base metrics for the sprint."""
    try:
        # Calculate individual metrics
        todo = calculate_todo(sprint_tasks)
        in_progress = calculate_in_progress(sprint_tasks)
        done = calculate_done(sprint_tasks)
        removed = calculate_removed(sprint_tasks)
        backlog_changes = calculate_backlog_changes(sprint_tasks, sprint_info, history_df)
        blocked_tasks = calculate_blocked_tasks(sprint_tasks)
        excluded_tasks = calculate_excluded_tasks(sprint_tasks, sprint_info, history_df)
        added_tasks = calculate_added_tasks(sprint_tasks, sprint_info, history_df)
        status_transitions = analyze_status_transitions(sprint_tasks, history_df, sprint_info)
        sprint_health = calculate_sprint_health({
            'todo': todo,
            'in_progress': in_progress,
            'done': done,
            'removed': removed,
            'backlog_changes': backlog_changes,
            'blocked_tasks': blocked_tasks
        }, sprint_tasks, history_df, sprint_info)
        
        # Compile all metrics into a dictionary
        metrics = {
            'todo': todo,
            'in_progress': in_progress,
            'done': done,
            'removed': removed,
            'backlog_changes': backlog_changes,
            'blocked_tasks': blocked_tasks,
            'excluded_tasks': excluded_tasks,
            'added_tasks': added_tasks,
            'status_transitions': status_transitions,
            'health_score': sprint_health['score'],
            'health_details': sprint_health['details'],
            'health_metrics': sprint_health['metrics_snapshot'],
            'sprint_health': sprint_health
        }
        logger.info("Metrics calculated successfully")
        return metrics
    except Exception as e:
        logger.error(f"Error in _calculate_base_metrics: {str(e)}")
        raise

def calculate_metrics(tasks, sprints, history_df, selected_sprints, selected_teams, time_frame):
    """Calculate metrics with improved stability"""
    try:
        # Input validation
        if tasks.empty or sprints.empty:
            raise ValueError("No data available")
            
        # Get sprint information with validation
        sprint_info = sprints[sprints['sprint_name'].isin(selected_sprints)]
        if sprint_info.empty:
            raise ValueError(f"No sprint found with names: {selected_sprints}")
        sprint_info = sprint_info.iloc[0]
        
        # Validate entity_ids
        if not isinstance(sprint_info['entity_ids'], set):
            sprint_info = sprint_info.copy()
            sprint_info['entity_ids'] = parse_entity_ids(sprint_info['entity_ids'])
            
        # Filter tasks with validation
        tasks_in_sprint = tasks[tasks['entity_id'].isin(sprint_info['entity_ids'])].copy()
        if tasks_in_sprint.empty:
            raise ValueError("No tasks found for selected sprint")
            
        sprint_tasks = tasks_in_sprint[tasks_in_sprint['workgroup'].isin(selected_teams)].copy()
        if sprint_tasks.empty:
            raise ValueError("No tasks found for selected teams")
            
        # Ensure numeric values
        sprint_tasks['estimation'] = pd.to_numeric(sprint_tasks['estimation'], errors='coerce').fillna(0)
        
        # Calculate metrics with validation
        metrics = _calculate_base_metrics(sprint_tasks, sprint_info, history_df)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error in calculate_metrics: {str(e)}")
        raise