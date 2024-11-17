import logging
from typing import Dict, List
import numpy as np
import pandas as pd
from datetime import datetime

# Configure logging for this module
logger = logging.getLogger(__name__)

class SprintHealthCalculator:
    """Handles sprint health score calculations with focused logging"""
    
    def __init__(self):
        self.logger = logger  # Use the module-level logger

    def calculate_health_scores(self, sprint_tasks: pd.DataFrame, daily_metrics: Dict, parameters: Dict = None) -> Dict[str, float]:
        """
        Calculate both original and advanced sprint health scores with custom parameters
        
        Args:
            sprint_tasks: DataFrame of sprint tasks
            daily_metrics: Dictionary of daily metrics
            parameters: Custom parameters for health calculation
        """
        try:
            # Use provided parameters or defaults
            params = parameters or {}
            uniformity_weight = params.get('uniformity_weight', 0.25)
            backlog_weight = params.get('backlog_weight', 0.25)
            completion_weight = params.get('completion_weight', 0.25)
            quality_weight = params.get('quality_weight', 0.25)
            
            self.logger.info(f"\nCalculating health scores for sprint with {len(sprint_tasks)} tasks")
            self.logger.info(f"Daily metrics available: {bool(daily_metrics)}")
            if daily_metrics:
                self.logger.info(f"Days with metrics: {len(daily_metrics)}")
            
            scores = []
            weights = []
            components = {}
            
            DEFAULT_SCORE = 0.7
            using_defaults = []

            # 1. Todo percentage (weight: 0.10)
            try:
                todo_pct = self._calculate_todo_percentage(sprint_tasks)
                todo_score = max(0, 1 - (todo_pct / 15))  # Allow up to 15% todo
                self.logger.info(f"Todo percentage: {todo_pct:.1f}% -> score: {todo_score:.2f}")
            except Exception as e:
                self.logger.warning(f"Using default for todo score: {e}")
                todo_score = DEFAULT_SCORE
                using_defaults.append('todo')
            scores.append(todo_score)
            weights.append(0.10)
            components['todo_score'] = todo_score

            # 2. Removed percentage (weight: 0.08)
            try:
                removed_pct = self._calculate_removed_percentage(sprint_tasks)
                removed_score = max(0, 1 - (removed_pct / 15))  # Allow up to 15% removed
                self.logger.info(f"Removed percentage: {removed_pct:.1f}% -> score: {removed_score:.2f}")
            except Exception as e:
                self.logger.warning(f"Using default for removed score: {e}")
                removed_score = DEFAULT_SCORE
                using_defaults.append('removed')
            scores.append(removed_score)
            weights.append(0.08)
            components['removed_score'] = removed_score

            # 3. Backlog stability (weight: 0.12)
            try:
                if daily_metrics and len(daily_metrics) > 0:
                    start_date = datetime.strptime(list(daily_metrics.keys())[0], '%Y-%m-%d')
                    backlog_change = self._calculate_backlog_change(sprint_tasks, start_date)
                    backlog_score = max(0, 1 - (backlog_change / 30))  # Allow up to 30% change
                    self.logger.info(f"Backlog change: {backlog_change:.1f}% -> score: {backlog_score:.2f}")
                else:
                    backlog_score = DEFAULT_SCORE
                    using_defaults.append('backlog')
            except Exception as e:
                self.logger.warning(f"Using default for backlog score: {e}")
                backlog_score = DEFAULT_SCORE
                using_defaults.append('backlog')
            scores.append(backlog_score)
            weights.append(0.12)
            components['backlog_score'] = backlog_score

            # 4. Status transition uniformity (weight: 0.18)
            try:
                uniformity_score = self._calculate_status_uniformity(daily_metrics)
                self.logger.info(f"Status uniformity score: {uniformity_score:.2f}")
            except Exception as e:
                self.logger.warning(f"Using default for uniformity score: {e}")
                uniformity_score = DEFAULT_SCORE
                using_defaults.append('uniformity')
            scores.append(uniformity_score)
            weights.append(0.18)
            components['uniformity_score'] = uniformity_score

            # 5. Completion rate (weight: 0.20)
            try:
                completion_rate = self._calculate_completion_rate(sprint_tasks)
                self.logger.info(f"Completion rate: {completion_rate:.2f}")
            except Exception as e:
                self.logger.warning(f"Using default for completion rate: {e}")
                completion_rate = DEFAULT_SCORE
                using_defaults.append('completion')
            scores.append(completion_rate)
            weights.append(0.20)
            components['completion_score'] = completion_rate

            # 6. Sprint burndown adherence (weight: 0.12)
            try:
                burndown_score = self._calculate_burndown_adherence(sprint_tasks, daily_metrics)
                self.logger.info(f"Burndown adherence score: {burndown_score:.2f}")
            except Exception as e:
                self.logger.warning(f"Using default for burndown score: {e}")
                burndown_score = DEFAULT_SCORE
                using_defaults.append('burndown')
            scores.append(burndown_score)
            weights.append(0.12)
            components['burndown_score'] = burndown_score

            # 7. Team collaboration (weight: 0.05)
            try:
                collaboration_score = self._calculate_team_collaboration(sprint_tasks)
                self.logger.info(f"Team collaboration score: {collaboration_score:.2f}")
            except Exception as e:
                self.logger.warning(f"Using default for collaboration score: {e}")
                collaboration_score = DEFAULT_SCORE
                using_defaults.append('collaboration')
            scores.append(collaboration_score)
            weights.append(0.05)
            components['collaboration_score'] = collaboration_score

            # 8. Task aging (weight: 0.05)
            try:
                aging_score = self._calculate_task_aging(sprint_tasks)
                self.logger.info(f"Task aging score: {aging_score:.2f}")
            except Exception as e:
                self.logger.warning(f"Using default for aging score: {e}")
                aging_score = DEFAULT_SCORE
                using_defaults.append('aging')
            scores.append(aging_score)
            weights.append(0.05)
            components['aging_score'] = aging_score

            # 9. Work distribution (weight: 0.05)
            try:
                distribution_score = self._calculate_work_distribution(sprint_tasks)
                self.logger.info(f"Work distribution score: {distribution_score:.2f}")
            except Exception as e:
                self.logger.warning(f"Using default for distribution score: {e}")
                distribution_score = DEFAULT_SCORE
                using_defaults.append('distribution')
            scores.append(distribution_score)
            weights.append(0.05)
            components['distribution_score'] = distribution_score

            # 10. Sprint velocity stability (weight: 0.05)
            try:
                velocity_score = self._calculate_velocity_stability(daily_metrics)
                self.logger.info(f"Velocity stability score: {velocity_score:.2f}")
            except Exception as e:
                self.logger.warning(f"Using default for velocity score: {e}")
                velocity_score = DEFAULT_SCORE
                using_defaults.append('velocity')
            scores.append(velocity_score)
            weights.append(0.05)
            components['velocity_score'] = velocity_score

            # Calculate final scores
            total_weight = sum(weights)
            if abs(total_weight - 1.0) > 0.001:
                self.logger.warning(f"Weights don't sum to 1.0: {total_weight}")
            
            original_score = sum(score * weight for score, weight in zip(scores, weights)) / total_weight
            advanced_score = self._calculate_comprehensive_score(sprint_tasks, daily_metrics)
            
            self.logger.info(f"""
            Sprint Health Summary:
            Components using defaults: {', '.join(using_defaults) if using_defaults else 'None'}
            Weights sum: {total_weight}
            Final Score: {original_score:.2f}
            Advanced Score: {advanced_score:.2f}
            """)
            
            return {
                'original': float(original_score),
                'advanced': float(advanced_score),
                'components': components
            }
                
        except Exception as e:
            self.logger.error(f"Error calculating health scores: {str(e)}")
            return {
                'original': DEFAULT_SCORE,
                'advanced': DEFAULT_SCORE,
                'components': {k: DEFAULT_SCORE for k in [
                    'todo_score', 'removed_score', 'backlog_score', 
                    'uniformity_score', 'completion_score', 'burndown_score',
                    'collaboration_score', 'aging_score', 'distribution_score',
                    'velocity_score'
                ]}
            }

    def _calculate_status_uniformity(self, daily_metrics: Dict) -> float:
        """Calculate uniformity of status transitions"""
        if not daily_metrics or len(daily_metrics) <= 1:
            return 0.7

        velocities = []
        for metrics in daily_metrics.values():
            daily_velocity = (metrics.get('done_count', 0) + 
                           metrics.get('in_progress_count', 0))
            velocities.append(daily_velocity)

        velocity_std = np.std(velocities)
        velocity_mean = np.mean(velocities)
        
        return max(0, 1 - (velocity_std / (max(abs(velocity_mean), 1) * 2)))

    def _calculate_completion_rate(self, sprint_tasks: pd.DataFrame) -> float:
        """Calculate task completion rate with status normalization"""
        completed_statuses = {
            'сделано', 'закрыто', 'выполнено', 'готово',
            'done', 'completed', 'closed', 'ready'
        }
        
        if 'status' not in sprint_tasks.columns:
            return 0.7
            
        completed_tasks = sprint_tasks[
            sprint_tasks['status'].str.lower().str.strip().isin(completed_statuses)
        ]
        
        return len(completed_tasks) / len(sprint_tasks) if len(sprint_tasks) > 0 else 0.7

    def _calculate_burndown_adherence(self, sprint_tasks: pd.DataFrame, daily_metrics: Dict) -> float:
        """Calculate adherence to ideal burndown"""
        if not daily_metrics or len(daily_metrics) <= 1:
            return 0.7

        ideal_burndown = np.linspace(len(sprint_tasks), 0, len(daily_metrics))
        actual_burndown = [
            metrics.get('todo_count', 0) + metrics.get('in_progress_count', 0) 
            for metrics in daily_metrics.values()
        ]
        
        burndown_diff = np.mean(np.abs(np.array(actual_burndown) - ideal_burndown))
        return max(0, 1 - (burndown_diff / (len(sprint_tasks) * 0.75)))

    def _calculate_team_collaboration(self, sprint_tasks: pd.DataFrame) -> float:
        """Calculate team collaboration score based on task assignments"""
        if 'assignee' not in sprint_tasks.columns:
            return 0.7

        unique_assignees = sprint_tasks['assignee'].nunique()
        total_tasks = len(sprint_tasks)
        
        # Calculate tasks per assignee ratio
        tasks_per_assignee = total_tasks / max(unique_assignees, 1)
        
        # Ideal range: 5-15 tasks per assignee
        if 5 <= tasks_per_assignee <= 15:
            return 1.0
        elif tasks_per_assignee < 5:
            return max(0.5, tasks_per_assignee / 5)
        else:
            return max(0.5, 1 - (tasks_per_assignee - 15) / 30)

    def _calculate_task_aging(self, sprint_tasks: pd.DataFrame) -> float:
        """Calculate task aging score with more lenient thresholds"""
        if 'processing_time' not in sprint_tasks.columns:
            return 0.7

        # Get processing times for completed tasks only
        completed_tasks = sprint_tasks[
            sprint_tasks['status'].str.lower().str.strip().isin([
                'сделано', 'закрыто', 'выполнено', 'готово',
                'done', 'completed', 'closed', 'ready'
            ])
        ]
        
        if completed_tasks.empty:
            return 0.7
        
        avg_age = completed_tasks['processing_time'].mean()
        
        # More lenient scoring: 
        # - Perfect score up to 7 days
        # - Linear decrease from 7 to 30 days
        # - Minimum score of 0.3 after 30 days
        if avg_age <= 7:
            return 1.0
        elif avg_age <= 30:
            return max(0.3, 1.0 - (avg_age - 7) / 23)
        else:
            return 0.3

    def _calculate_work_distribution(self, sprint_tasks: pd.DataFrame) -> float:
        """Calculate evenness of work distribution among team members"""
        if 'assignee' not in sprint_tasks.columns:
            return 0.7

        task_counts = sprint_tasks['assignee'].value_counts()
        if len(task_counts) <= 1:
            return 0.7

        # Calculate coefficient of variation (CV)
        cv = task_counts.std() / task_counts.mean()
        
        # More lenient scoring:
        # - Perfect score if CV <= 0.3 (30% variation)
        # - Linear decrease from 0.3 to 1.0 CV
        # - Minimum score of 0.3
        if cv <= 0.3:
            return 1.0
        elif cv <= 1.0:
            return max(0.3, 1.0 - (cv - 0.3) / 0.7)
        else:
            return 0.3

    def _calculate_velocity_stability(self, daily_metrics: Dict) -> float:
        """Calculate stability of sprint velocity with improved scoring"""
        if not daily_metrics or len(daily_metrics) <= 1:
            return 0.7

        daily_velocities = []
        for metrics in daily_metrics.values():
            # Include both completed and in-progress tasks
            velocity = metrics.get('done_count', 0) + metrics.get('in_progress_count', 0)
            daily_velocities.append(velocity)

        if not daily_velocities or all(v == 0 for v in daily_velocities):
            return 0.7
        
        velocity_std = np.std(daily_velocities)
        velocity_mean = np.mean(daily_velocities)
        
        if velocity_mean == 0:
            return 0.5
        
        cv = velocity_std / velocity_mean
        
        # More lenient scoring:
        # - Perfect score if CV <= 0.2 (20% variation)
        # - Linear decrease from 0.2 to 0.8 CV
        # - Minimum score of 0.3
        if cv <= 0.2:
            return 1.0
        elif cv <= 0.8:
            return max(0.3, 1.0 - (cv - 0.2) / 0.6)
        else:
            return 0.3

    def _calculate_todo_percentage(self, sprint_tasks: pd.DataFrame) -> float:
        """Calculate percentage of tasks in 'To Do' status"""
        if sprint_tasks.empty:
            return 0.0
            
        todo_tasks = sprint_tasks[
            sprint_tasks['status'].str.lower().isin(['к выполнению', 'создано'])
        ]
        
        if 'estimation' not in sprint_tasks.columns:
            return (len(todo_tasks) / len(sprint_tasks)) * 100
            
        todo_estimation = todo_tasks['estimation'].sum()
        total_estimation = sprint_tasks['estimation'].sum()
        
        return (todo_estimation / total_estimation * 100) if total_estimation else 0

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
        initial_tasks = sprint_tasks[sprint_tasks['create_date'] <= sprint_start]
        added_tasks = sprint_tasks[sprint_tasks['create_date'] > sprint_start]
        
        initial_estimation = initial_tasks['estimation'].sum()
        added_estimation = added_tasks['estimation'].sum()
        
        return (added_estimation / initial_estimation * 100) if initial_estimation else 0

    def _calculate_comprehensive_score(self, sprint_tasks: pd.DataFrame, daily_metrics: Dict) -> float:
        """Calculate comprehensive health score with additional metrics"""
        try:
            # Calculate advanced metrics
            task_aging = sprint_tasks['processing_time'].mean() if not sprint_tasks.empty else 0
            daily_completed = [m['done_count'] for m in daily_metrics.values()]
            velocity_std = np.std(daily_completed) if daily_completed else 0
            scope_changes = sum(
                m['added_tasks']['count'] + m['removed_tasks']['count'] 
                for m in daily_metrics.values()
            )
            team_collaboration = (
                sprint_tasks['assignee'].nunique() / len(sprint_tasks) 
                if len(sprint_tasks) else 0
            )
            
            # Calculate additional metrics
            completion_trend = self._calculate_completion_trend(daily_metrics)
            workload_balance = self._calculate_workload_balance(sprint_tasks)
            
            # Calculate component scores with adjusted thresholds
            task_aging_score = max(0, 1 - (task_aging / 45))  # Allow up to 45 days aging
            velocity_consistency_score = max(0, 1 - (velocity_std / 10))  # More lenient with velocity variations
            scope_stability_score = max(0, 1 - (scope_changes / 30))  # Allow more scope changes
            team_collaboration_score = min(team_collaboration / 3, 1)  # Expect 3 team members per task
            completion_trend_score = completion_trend
            workload_balance_score = workload_balance
            
            # Weighted combination with balanced weights
            weights = {
                'task_aging': 0.15,
                'velocity_consistency': 0.15,
                'scope_stability': 0.15,
                'team_collaboration': 0.15,
                'completion_trend': 0.20,
                'workload_balance': 0.20
            }
            
            comprehensive_score = (
                task_aging_score * weights['task_aging'] +
                velocity_consistency_score * weights['velocity_consistency'] +
                scope_stability_score * weights['scope_stability'] +
                team_collaboration_score * weights['team_collaboration'] +
                completion_trend_score * weights['completion_trend'] +
                workload_balance_score * weights['workload_balance']
            )
            
            return comprehensive_score
            
        except Exception as e:
            self.logger.error(f"Error calculating comprehensive score: {str(e)}")
            return 0.5

    def _calculate_completion_trend(self, daily_metrics: Dict) -> float:
        """Calculate the trend in completion rate over the sprint"""
        try:
            if not daily_metrics:
                return 0.5
            
            completion_rates = []
            for metrics in daily_metrics.values():
                total = metrics['todo_count'] + metrics['in_progress_count'] + metrics['done_count']
                completion_rate = metrics['done_count'] / total if total > 0 else 0
                completion_rates.append(completion_rate)
            
            if len(completion_rates) < 2:
                return 0.5
            
            # Calculate trend using linear regression
            x = np.arange(len(completion_rates))
            slope = np.polyfit(x, completion_rates, 1)[0]
            
            # Convert slope to score (positive slope is good)
            trend_score = 0.5 + (slope * 50)  # Scale slope to [-0.5, 0.5] range
            return max(0, min(1, trend_score))  # Clamp to [0, 1]
            
        except Exception as e:
            self.logger.error(f"Error calculating completion trend: {str(e)}")
            return 0.5

    def _calculate_workload_balance(self, sprint_tasks: pd.DataFrame) -> float:
        """Calculate how evenly work is distributed among team members"""
        try:
            if sprint_tasks.empty or 'assignee' not in sprint_tasks.columns:
                return 0.5
            
            # Count tasks per assignee
            tasks_per_assignee = sprint_tasks['assignee'].value_counts()
            
            if len(tasks_per_assignee) < 2:
                return 0.5
            
            # Calculate coefficient of variation
            cv = tasks_per_assignee.std() / tasks_per_assignee.mean()
            
            # Convert to score (lower cv is better)
            balance_score = max(0, 1 - (cv / 0.5))  # Allow up to 50% variation
            return balance_score
            
        except Exception as e:
            self.logger.error(f"Error calculating workload balance: {str(e)}")
            return 0.5

    def _validate_sprint_data(self, sprint_tasks: pd.DataFrame) -> bool:
        """Validate sprint data before calculation"""
        try:
            required_columns = ['status', 'create_date', 'update_date', 'processing_time']
            missing_columns = [col for col in required_columns if col not in sprint_tasks.columns]
            
            if missing_columns:
                self.logger.warning(f"Missing required columns: {missing_columns}")
                return False
            
            if sprint_tasks.empty:
                self.logger.warning("Empty sprint tasks dataframe")
                return False
            
            # Validate processing_time
            if sprint_tasks['processing_time'].isna().all():
                self.logger.warning("No valid processing_time values")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating sprint data: {str(e)}")
            return False