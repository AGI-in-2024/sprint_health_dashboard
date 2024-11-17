import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Optional
import logging
import json
import sys
from pathlib import Path
from core_eda import CoreEDA
from sprint_health_calculator import SprintHealthCalculator
from data_loader import DataLoader

# Configure logging at the start of the script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Print to console
        logging.FileHandler('sprint_health.log')  # Also save to file
    ]
)

logger = logging.getLogger(__name__)  # Get logger for this module

class SprintHealthAnalyzer(CoreEDA):
    """Analyzer for Sprint Health metrics and visualization"""
    
    def __init__(self, entities_df=None, history_df=None, sprints_df=None):
        # If no dataframes provided, load them
        if all(df is None for df in [entities_df, history_df, sprints_df]):
            loader = DataLoader()
            entities_df, history_df, sprints_df = loader.load_datasets()
            
        super().__init__(entities_df, history_df, sprints_df)
        self.health_calculator = SprintHealthCalculator()
        self.logger = logging.getLogger(__name__)  # Get logger for this class
        
        # Additional setup for sprint health analysis
        self.output_dir = Path('analysis/results/sprint_health')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Expanded status category mappings
        self.status_categories = {
            'К выполнению': 'todo',
            'Создано': 'todo',
            'В работе': 'in_progress',
            'В процессе': 'in_progress',
            'На проверке': 'in_progress',
            'Сделано': 'done',
            'Закрыто': 'done',
            'Выполнено': 'done',
            'Готово': 'done',
            'Отклонено': 'removed',
            'Отменено инициатором': 'removed',
            'Дубликат': 'removed',
            'Отклонен исполнителем': 'removed'
        }

    def load_data(self):
        """Load data from CSV files"""
        try:
            logger.info("Loading datasets...")
            
            # Define data directory and validate its existence
            script_dir = Path(__file__).parent  # Get the directory containing this script
            possible_paths = [
                script_dir / "data_for_spb_hakaton_entities",  # Check in new/ directory
                Path("data_for_spb_hakaton_entities"),         # Check in current directory
                Path("analysis") / "data_for_spb_hakaton_entities",
                Path(__file__).parent.parent / "data_for_spb_hakaton_entities",
                Path("/home/dukhanin/agile_new/new/data_for_spb_hakaton_entities")  # Add the specific path
            ]
            
            data_dir = None
            for path in possible_paths:
                if path.exists():
                    data_dir = path
                    break
            
            if data_dir is None:
                raise FileNotFoundError(
                    f"Data directory not found. Tried paths:\n"
                    f"{chr(10).join([f'- {p.absolute()}' for p in possible_paths])}"
                )

            logger.info(f"Using data directory: {data_dir}")

            # Define file paths
            entities_file = data_dir / "data_for_spb_hakaton_entities1-Table 1.csv"
            history_file = data_dir / "history-Table 1.csv"
            sprints_file = data_dir / "sprints-Table 1.csv"

            # Validate file existence
            missing_files = []
            for file_path in [entities_file, history_file, sprints_file]:
                if not file_path.exists():
                    missing_files.append(file_path)
            
            if missing_files:
                raise FileNotFoundError(
                    f"The following required data files are missing:\n"
                    f"{chr(10).join([f'- {f}' for f in missing_files])}"
                )
            
            # Load entities data with proper column names
            logger.info("Loading entities data...")
            self.entities_df = pd.read_csv(
                entities_file,
                encoding='utf-8',
                sep=';',
                skiprows=1
            )
            
            # Load history data with proper structure
            logger.info("Loading history data...")
            self.history_df = pd.read_csv(
                history_file,
                encoding='utf-8',
                sep=';',
                skiprows=1
            )
            
            # Reset index for history data to get proper column structure
            if isinstance(self.history_df.index, pd.MultiIndex):
                self.history_df = self.history_df.reset_index()
            
            # Rename columns to match expected structure
            history_columns = {
                'level_0': 'entity_id',
                'level_1': 'history_property_name',
                'level_2': 'history_date',
                'level_3': 'history_version',
                'level_4': 'history_change_type',
                'level_5': 'history_change'
            }
            self.history_df = self.history_df.rename(columns=history_columns)
            
            # Load sprints data
            logger.info("Loading sprints data...")
            self.sprints_df = pd.read_csv(
                sprints_file,
                encoding='utf-8',
                sep=';',
                skiprows=1
            )
            
            # Fix column names and data types
            self._preprocess_loaded_data()
            
            logger.info("All datasets loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            raise

    def _preprocess_loaded_data(self):
        """Preprocess loaded data to ensure correct format"""
        try:
            logger.info("\nPreprocessing data...")
            
            # Fix entities DataFrame
            if 'Table 1' in self.entities_df.columns:
                logger.info("Processing entities data...")
                # Convert to string first to ensure proper splitting
                self.entities_df['Table 1'] = self.entities_df['Table 1'].astype(str)
                # Split the combined column into separate columns
                self.entities_df = pd.DataFrame([
                    x.split(';') for x in self.entities_df['Table 1'].values
                ])
                self.entities_df.columns = [
                    'entity_id', 'area', 'type', 'status', 'state', 'priority', 
                    'ticket_number', 'name', 'create_date', 'created_by', 'update_date',
                    'updated_by', 'parent_ticket_id', 'assignee', 'owner', 'due_date',
                    'rank', 'estimation', 'spent', 'workgroup'
                ]

            # Fix history DataFrame
            if self.history_df is not None:
                logger.info("Processing history data...")
                
                # Convert history_date to datetime
                self.history_df['history_date'] = pd.to_datetime(
                    self.history_df['history_date'],
                    format='%m/%d/%y %H:%M',
                    errors='coerce'
                )
                
                # Split history_change into old_value and new_value
                if 'history_change' in self.history_df.columns:
                    logger.info("Splitting history_change into old_value and new_value")
                    
                    def split_history_change(change):
                        if pd.isna(change):
                            return pd.Series({'old_value': None, 'new_value': None})
                        parts = str(change).split(' -> ')
                        if len(parts) == 2:
                            return pd.Series({'old_value': parts[0].strip(), 'new_value': parts[1].strip()})
                        return pd.Series({'old_value': None, 'new_value': parts[0].strip() if parts else None})
                    
                    # Split the history_change column
                    change_values = self.history_df['history_change'].apply(split_history_change)
                    self.history_df['old_value'] = change_values['old_value']
                    self.history_df['new_value'] = change_values['new_value']
                    
                    logger.info(f"Split {len(self.history_df)} history changes")
                
                # Validate history dates
                invalid_dates = self.history_df['history_date'].isna().sum()
                if invalid_dates > 0:
                    logger.warning(f"Warning: {invalid_dates} invalid dates found in history data")

            # Fix sprints DataFrame
            if 'Table 1' in self.sprints_df.columns:
                logger.info("Processing sprints data...")
                self.sprints_df['Table 1'] = self.sprints_df['Table 1'].astype(str)
                # Split the combined column into separate columns
                temp_df = pd.DataFrame([
                    x.split(';') for x in self.sprints_df['Table 1'].values
                ])
                temp_df.columns = [
                    'sprint_name', 'sprint_status', 'sprint_start_date', 
                    'sprint_end_date', 'entity_ids'
                ]
                self.sprints_df = temp_df

            # Convert dates with proper error handling
            logger.info("Converting dates...")
            
            # Convert entity dates
            date_cols = ['create_date', 'update_date', 'due_date']
            for col in date_cols:
                if col in self.entities_df.columns:
                    self.entities_df[col] = pd.to_datetime(
                        self.entities_df[col], 
                        format='%Y-%m-%d %H:%M:%S.%f',
                        errors='coerce'
                    )

            # Convert sprint dates
            sprint_date_cols = ['sprint_start_date', 'sprint_end_date']
            for col in sprint_date_cols:
                if col in self.sprints_df.columns:
                    self.sprints_df[col] = pd.to_datetime(
                        self.sprints_df[col], 
                        format='%Y-%m-%d %H:%M:%S.%f',
                        errors='coerce'
                    )

            # Process entity_ids in sprints
            if 'entity_ids' in self.sprints_df.columns:
                self.sprints_df['entity_ids'] = self.sprints_df['entity_ids'].apply(
                    lambda x: set(str(x).strip('{}').split(',')) if pd.notna(x) else set()
                )

            # Print validation info
            logger.info("\nDate parsing validation:")
            for col in date_cols:
                valid_dates = self.entities_df[col].notna().sum()
                total_rows = len(self.entities_df)
                logger.info(f"Entities - {col}: {valid_dates}/{total_rows} dates parsed successfully")

            for col in sprint_date_cols:
                valid_dates = self.sprints_df[col].notna().sum()
                total_rows = len(self.sprints_df)
                logger.info(f"Sprints - {col}: {valid_dates}/{total_rows} dates parsed successfully")

            # Add history date validation
            if self.history_df is not None:
                valid_history_dates = self.history_df['history_date'].notna().sum()
                total_history_rows = len(self.history_df)
                logger.info(f"History - history_date: {valid_history_dates}/{total_history_rows} dates parsed successfully")

            # Calculate processing time
            logger.info("Calculating processing time...")
            if all(col in self.entities_df.columns for col in ['create_date', 'update_date']):
                self.entities_df['processing_time'] = (
                    self.entities_df['update_date'] - self.entities_df['create_date']
                ).dt.total_seconds() / (24 * 3600)  # Convert to days
                self.entities_df['processing_time'] = self.entities_df['processing_time'].clip(lower=0)
                logger.info(f"Calculated processing time for {len(self.entities_df)} tasks")

            logger.info("\nDatasets preprocessed successfully")
            
        except Exception as e:
            logger.error(f"Error during preprocessing: {str(e)}")
            raise

    def _get_sprint_tasks(self, entity_ids: set) -> pd.DataFrame:
        """Get all tasks for a sprint with their history"""
        try:
            # Clean and process entity IDs
            if isinstance(entity_ids, str):
                entity_ids = set(entity_ids.strip('{}').split(','))
            
            # Clean individual IDs
            entity_ids = {str(id).strip() for id in entity_ids if pd.notna(id)}
            
            # Get tasks
            sprint_tasks = self.entities_df[
                self.entities_df['entity_id'].astype(str).isin(entity_ids)
            ].copy()
            
            logger.info(f"Found {len(sprint_tasks)} tasks for sprint")
            return sprint_tasks
            
        except Exception as e:
            logger.error(f"Error getting sprint tasks: {str(e)}")
            return pd.DataFrame()

    def _calculate_todo_percentage(self, sprint_tasks: pd.DataFrame) -> float:
        """Calculate percentage of tasks in 'To Do' status"""
        if sprint_tasks.empty:
            return 0.0
            
        todo_tasks = sprint_tasks[
            sprint_tasks['status'].str.lower().isin(['к выполнению', 'создано'])
        ]
        
        if 'estimation' not in sprint_tasks.columns:
            # Fall back to count-based percentage if no estimation available
            return (len(todo_tasks) / len(sprint_tasks)) * 100
            
        todo_estimation = todo_tasks['estimation'].sum()
        total_estimation = sprint_tasks['estimation'].sum()
        
        return (todo_estimation / total_estimation * 100) if total_estimation else 0

    def _get_added_tasks_for_date(self, sprint_tasks: pd.DataFrame, date: datetime) -> Dict:
        """Get tasks added on a specific date"""
        added_tasks = sprint_tasks[sprint_tasks['create_date'].dt.date == date.date()]
        return {
            'count': len(added_tasks),
            'estimation': float(added_tasks['estimation'].sum() / 3600) if 'estimation' in added_tasks.columns else 0.0
        }

    def _get_removed_tasks_for_date(self, sprint_tasks: pd.DataFrame, date: datetime) -> Dict:
        """Get tasks removed on a specific date"""
        # Get status changes to 'removed' on this date
        removed_changes = self.history_df[
            (self.history_df['entity_id'].isin(sprint_tasks['entity_id'])) &
            (self.history_df['history_property_name'] == 'resolution') &
            (self.history_df['history_date'].dt.date == date.date()) &
            (self.history_df['new_value'].str.lower().isin([
                'отклонено', 'отменено инициатором', 'дубликат', 'отклонен исполнителем'
            ]))
        ]
        
        removed_tasks = sprint_tasks[sprint_tasks['entity_id'].isin(removed_changes['entity_id'])]
        return {
            'count': len(removed_tasks),
            'estimation': float(removed_tasks['estimation'].sum() / 3600) if 'estimation' in removed_tasks.columns else 0.0
        }

    def analyze_sprint_health(self, sprint_id: str, parameters: dict = None, time_point: float = None) -> Dict:
        """
        Analyze health metrics for a specific sprint with custom parameters
        
        Args:
            sprint_id: ID of the sprint to analyze
            parameters: Custom parameters for health calculation
            time_point: Percentage point in sprint duration to analyze (0-100)
        """
        try:
            # Get sprint data
            sprint_data = self.sprints_df[self.sprints_df['sprint_name'] == sprint_id].iloc[0]
            sprint_start = pd.to_datetime(sprint_data['sprint_start_date'])
            sprint_end = pd.to_datetime(sprint_data['sprint_end_date'])
            
            # Get sprint tasks
            sprint_tasks = self._get_sprint_tasks(sprint_data['entity_ids'])
            
            # Calculate daily metrics
            daily_metrics = self._calculate_daily_metrics(sprint_tasks, sprint_start, sprint_end)
            
            # Apply time point filtering if specified
            if time_point is not None:
                daily_metrics = self._filter_metrics_by_timepoint(daily_metrics, time_point)
            
            # Calculate health scores with custom parameters
            health_scores = self.health_calculator.calculate_health_scores(
                sprint_tasks, 
                daily_metrics,
                parameters
            )
            
            # Calculate overall sprint metrics
            sprint_metrics = {
                'health_scores': health_scores,
                'metrics': {
                    'todo': {
                        'value': self._calculate_todo_percentage(sprint_tasks),
                        'threshold': parameters.get('max_todo_percentage', 20.0) if parameters else 20.0,
                        'unit': '%',
                        'description': 'Percentage of tasks in To Do status'
                    },
                    'removed': {
                        'value': self._calculate_removed_percentage(sprint_tasks),
                        'threshold': parameters.get('max_removed_percentage', 10.0) if parameters else 10.0,
                        'unit': '%',
                        'description': 'Percentage of removed tasks'
                    },
                    'backlog_change': {
                        'value': self._calculate_backlog_change(sprint_tasks, sprint_start),
                        'threshold': parameters.get('max_backlog_change', 20.0) if parameters else 20.0,
                        'unit': '%',
                        'description': 'Percentage of backlog changes'
                    }
                },
                'status_transition_uniformity': self._calculate_status_uniformity(sprint_tasks, sprint_start, sprint_end),
                'daily_metrics': daily_metrics
            }
            
            return sprint_metrics
            
        except Exception as e:
            self.logger.error(f"Error analyzing sprint health: {str(e)}")
            raise

    def _filter_metrics_by_timepoint(self, daily_metrics: Dict, time_point: float) -> Dict:
        """Filter daily metrics up to specified time point percentage"""
        if not 0 <= time_point <= 100:
            raise ValueError("Time point must be between 0 and 100")
        
        total_days = len(daily_metrics)
        days_to_keep = int((time_point / 100) * total_days)
        
        # Sort dates and keep only up to the specified point
        sorted_dates = sorted(daily_metrics.keys())
        keep_dates = sorted_dates[:days_to_keep]
        
        return {date: metrics for date, metrics in daily_metrics.items() if date in keep_dates}

    def _calculate_removed_percentage(self, sprint_tasks: pd.DataFrame) -> float:
        """Calculate percentage of removed tasks"""
        removed_tasks = sprint_tasks[
            sprint_tasks['resolution'].str.lower().isin([
                'отклонено', 'отменено инициатором', 'дубликат', 'отклонен исполнителем'
            ])
        ]
        return len(removed_tasks) / len(sprint_tasks) * 100 if len(sprint_tasks) else 0

    def _calculate_backlog_change(self, sprint_tasks: pd.DataFrame, sprint_start: datetime) -> float:
        """Calculate backlog change percentage after sprint start"""
        initial_tasks = sprint_tasks[sprint_tasks['create_date'] <= sprint_start + timedelta(days=2)]
        added_tasks = sprint_tasks[sprint_tasks['create_date'] > sprint_start + timedelta(days=2)]
        
        initial_estimation = initial_tasks['estimation'].sum()
        added_estimation = added_tasks['estimation'].sum()
        
        return (added_estimation / initial_estimation * 100) if initial_estimation else 0

    def _calculate_status_uniformity(
        self, 
        sprint_tasks: pd.DataFrame, 
        sprint_start: datetime, 
        sprint_end: datetime
    ) -> float:
        """Calculate how uniform status transitions are throughout the sprint"""
        try:
            # Ensure we have valid datetime objects
            if not isinstance(sprint_start, pd.Timestamp) and not isinstance(sprint_start, datetime):
                sprint_start = pd.to_datetime(sprint_start)
            if not isinstance(sprint_end, pd.Timestamp) and not isinstance(sprint_end, datetime):
                sprint_end = pd.to_datetime(sprint_end)

            # Get status changes from history with proper date filtering
            status_changes = self.history_df[
                (self.history_df['entity_id'].isin(sprint_tasks['entity_id'])) &
                (self.history_df['history_property_name'].isin(['Статус', 'status'])) &
                (self.history_df['history_date'].notna()) &  # Ensure we have valid dates
                (self.history_df['history_date'] >= sprint_start) &
                (self.history_df['history_date'] <= sprint_end)
            ]
            
            # Calculate daily status changes
            if status_changes.empty:
                self.logger.warning(f"No status changes found for sprint between {sprint_start} and {sprint_end}")
                return 0.0
            
            daily_changes = status_changes.groupby(
                status_changes['history_date'].dt.date
            ).size()
            
            # Calculate coefficient of variation (lower is more uniform)
            if daily_changes.empty or daily_changes.mean() == 0:
                return 1.0  # Assuming full uniformity if no changes
            
            # Modified to invert the coefficient for uniformity scoring
            uniformity_score = float(1 - (daily_changes.std() / daily_changes.mean()))
            uniformity_score = max(0.0, uniformity_score)  # Ensure non-negative
            
            return uniformity_score
            
        except Exception as e:
            self.logger.error(f"Error calculating status uniformity: {str(e)}")
            return 1.0  # Default to maximum uniformity on error

    def _calculate_blocked_tasks(self, sprint_tasks: pd.DataFrame) -> Dict:
        """Calculate blocked tasks metrics"""
        blocked_tasks = sprint_tasks[
            ~sprint_tasks['status'].isin(['Сделано', 'Закрыто', 'Выполнено'])
        ]
        
        return {
            'count': len(blocked_tasks),
            'estimation': float(blocked_tasks['estimation'].sum() / 3600)  # Convert to hours
        }

    def _calculate_daily_metrics(
        self, 
        sprint_tasks: pd.DataFrame, 
        sprint_start: datetime, 
        sprint_end: datetime
    ) -> Dict:
        """Calculate metrics for each day of the sprint"""
        try:
            daily_metrics = {}
            current_date = sprint_start
            
            while current_date <= sprint_end:
                date_str = current_date.strftime('%Y-%m-%d')
                
                try:
                    # Get tasks state for this day
                    tasks_state = self._get_tasks_state_for_date(sprint_tasks, current_date)
                    
                    # Get added/removed tasks
                    added = self._get_added_tasks_for_date(sprint_tasks, current_date)
                    removed = self._get_removed_tasks_for_date(sprint_tasks, current_date)
                    
                    daily_metrics[date_str] = {
                        'todo_count': tasks_state['todo'],
                        'in_progress_count': tasks_state['in_progress'],
                        'done_count': tasks_state['done'],
                        'added_tasks': added,
                        'removed_tasks': removed
                    }
                except Exception as e:
                    self.logger.error(f"Error calculating metrics for date {date_str}: {str(e)}")
                    # Add default metrics for this day
                    daily_metrics[date_str] = {
                        'todo_count': 0,
                        'in_progress_count': 0,
                        'done_count': 0,
                        'added_tasks': {'count': 0, 'estimation': 0.0},
                        'removed_tasks': {'count': 0, 'estimation': 0.0}
                    }
                
                current_date += timedelta(days=1)
                
            return daily_metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating daily metrics: {str(e)}")
            return {}

    def _get_tasks_state_for_date(self, sprint_tasks: pd.DataFrame, date: datetime) -> Dict:
        """Get task counts by status for a specific date"""
        try:
            # Get status changes up to this date
            status_changes = self.history_df[
                (self.history_df['entity_id'].isin(sprint_tasks['entity_id'])) &
                (self.history_df['history_property_name'].isin(['Статус', 'status'])) &
                (self.history_df['history_date'] <= date)
            ]
            
            # Initialize status counts
            status_counts = {
                'todo': 0,
                'in_progress': 0,
                'done': 0,
                'removed': 0
            }
            
            if status_changes.empty:
                logger.warning(f"No status changes found up to date {date}")
                return status_counts
            
            # Get latest status for each task
            latest_statuses = (status_changes
                .sort_values('history_date')
                .groupby('entity_id')
                .last()
                .reset_index())
            
            # Count tasks in each category
            for _, row in latest_statuses.iterrows():
                status = None
                if pd.notna(row.get('new_value')):
                    status = str(row['new_value']).strip()
                elif pd.notna(row.get('history_change')):
                    # Fallback to history_change if new_value is not available
                    change = str(row['history_change']).strip()
                    if ' -> ' in change:
                        status = change.split(' -> ')[1].strip()
                    else:
                        status = change
                
                if status:
                    category = self.status_categories.get(status, 'todo')
                    if category in status_counts:
                        status_counts[category] += 1
                    else:
                        logger.warning(f"Unknown category '{category}' for status '{status}'. Defaulting to 'todo'.")
                        status_counts['todo'] += 1
                else:
                    logger.warning(f"No status found for task {row['entity_id']}")
                    status_counts['todo'] += 1
            
            # Add tasks that haven't had any status changes
            unchanged_tasks = sprint_tasks[~sprint_tasks['entity_id'].isin(latest_statuses['entity_id'])]
            for _, task in unchanged_tasks.iterrows():
                if pd.notna(task['status']):
                    status = str(task['status']).strip()
                    category = self.status_categories.get(status, 'todo')
                    if category in status_counts:
                        status_counts[category] += 1
                    else:
                        logger.warning(f"Unknown category '{category}' for status '{status}'. Defaulting to 'todo'.")
                        status_counts['todo'] += 1
                else:
                    status_counts['todo'] += 1
            
            logger.debug(f"Task counts for {date}: {status_counts}")
            return status_counts
            
        except Exception as e:
            logger.error(f"Error getting tasks state for date {date}: {str(e)}")
            return {'todo': 0, 'in_progress': 0, 'done': 0, 'removed': 0}

    def _create_sprint_health_visualizations(self, sprint_metrics: Dict, sprint_id: str):
        """Create visualizations for sprint health metrics"""
        # Create output directory for this sprint
        sprint_dir = self.output_dir / sprint_id
        sprint_dir.mkdir(exist_ok=True)
        
        # Plot daily task status distribution
        self._plot_daily_status_distribution(sprint_metrics['daily_metrics'], sprint_dir)
        
        # Plot sprint health indicators
        self._plot_health_indicators(sprint_metrics, sprint_dir)
        
        # Save metrics to JSON
        self._save_metrics(sprint_metrics, sprint_dir)

    def _plot_daily_status_distribution(self, daily_metrics: Dict, output_dir: Path):
        """Plot daily distribution of task statuses"""
        dates = list(daily_metrics.keys())
        todo_counts = [m['todo_count'] for m in daily_metrics.values()]
        in_progress_counts = [m['in_progress_count'] for m in daily_metrics.values()]
        done_counts = [m['done_count'] for m in daily_metrics.values()]
        
        plt.figure(figsize=(12, 6))
        plt.stackplot(dates, 
                     [todo_counts, in_progress_counts, done_counts],
                     labels=['To Do', 'In Progress', 'Done'])
        plt.title('Daily Task Status Distribution')
        plt.xlabel('Date')
        plt.ylabel('Number of Tasks')
        plt.xticks(rotation=45)
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / 'daily_status_distribution.png')
        plt.close()

    def _plot_health_indicators(self, sprint_metrics: Dict, output_dir: Path):
        """Plot sprint health indicators including both scoring methods"""
        # Get health scores
        health_scores = sprint_metrics['health_scores']
        
        # Create comparison plot
        plt.figure(figsize=(12, 6))
        
        # Plot both scoring methods
        scores = [
            health_scores['original'],
            health_scores['advanced']
        ]
        labels = ['Original Score', 'Advanced Score']
        
        bars = plt.bar(labels, scores)
        
        # Color bars based on score values
        for bar, score in zip(bars, scores):
            if score >= 0.8:
                bar.set_color('green')
            elif score >= 0.6:
                bar.set_color('yellow')
            else:
                bar.set_color('red')
                
        plt.title('Sprint Health Scores Comparison')
        plt.ylabel('Score')
        plt.ylim(0, 1)  # Set y-axis limits from 0 to 1
        
        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}',
                    ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(output_dir / 'health_scores_comparison.png')
        plt.close()
        
        # Plot detailed components
        self._plot_health_components(health_scores['components'], output_dir)

    def _plot_health_components(self, components: Dict, output_dir: Path):
        """Plot detailed breakdown of health score components"""
        plt.figure(figsize=(12, 6))
        
        labels = list(components.keys())
        values = list(components.values())
        
        bars = plt.bar(labels, values)
        
        # Color bars based on component values
        for bar, value in zip(bars, values):
            if value >= 0.8:
                bar.set_color('green')
            elif value >= 0.6:
                bar.set_color('yellow')
            else:
                bar.set_color('red')
        
        plt.title('Health Score Components')
        plt.ylabel('Score')
        plt.ylim(0, 1)
        plt.xticks(rotation=45, ha='right')
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}',
                    ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(output_dir / 'health_components.png')
        plt.close()

    def _save_metrics(self, sprint_metrics: Dict, output_dir: Path):
        """Save metrics to JSON file"""
        with open(output_dir / 'metrics.json', 'w') as f:
            json.dump(sprint_metrics, f, indent=2, default=str)

def main():
    """Main function to run sprint health analysis"""
    try:
        logger.info("Starting sprint health analysis")
        
        # Initialize analyzer
        analyzer = SprintHealthAnalyzer()
        
        try:
            # Load data
            analyzer.load_data()
        except FileNotFoundError as e:
            logger.error("\nData Loading Error:")
            logger.error(str(e))
            logger.error("\nPlease ensure the data files are in one of the following locations:")
            logger.error("- ./data_for_spb_hakaton_entities/")
            logger.error("- ./analysis/data_for_spb_hakaton_entities/")
            logger.error("- ../data_for_spb_hakaton_entities/")
            return
        except Exception as e:
            logger.error(f"\nUnexpected error loading data: {str(e)}")
            return
            
        # Analyze each sprint
        for sprint_id in analyzer.sprints_df['sprint_name'].unique():
            logger.info(f"\nAnalyzing sprint: {sprint_id}")
            
            try:
                # Get sprint data for debugging
                sprint_data = analyzer.sprints_df[
                    analyzer.sprints_df['sprint_name'] == sprint_id
                ].iloc[0]
                entity_ids = sprint_data['entity_ids']
                logger.info(f"Sprint entity IDs: {len(entity_ids) if isinstance(entity_ids, set) else 'N/A'}")
                
                metrics = analyzer.analyze_sprint_health(sprint_id)
                
                # Print key insights
                logger.info("\nSprint Health Metrics:")
                logger.info(f"Health Score: {metrics['health_score']:.2f}")
                logger.info(f"Todo Percentage: {metrics['todo_percentage']:.1f}%")
                logger.info(f"Removed Percentage: {metrics['removed_percentage']:.1f}%")
                logger.info(f"Backlog Change: {metrics['backlog_change']:.1f}%")
                logger.info("-" * 50)
                
            except Exception as e:
                logger.error(f"Error analyzing sprint {sprint_id}: {str(e)}")
                continue
            
    except Exception as e:
        logger.error(f"Critical error during sprint health analysis: {str(e)}")
        raise

if __name__ == "__main__":
    main() 