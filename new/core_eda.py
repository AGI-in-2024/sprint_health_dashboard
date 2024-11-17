import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
from datetime import datetime, timedelta
import logging

# Configure plot style - using a built-in style
plt.style.use('ggplot')  # Changed from 'seaborn' to 'ggplot'
sns.set_theme(style="whitegrid")  # Set seaborn style explicitly

class CoreEDA:
    def __init__(self, entities_df=None, history_df=None, sprints_df=None):
        """
        Initialize CoreEDA with optional dataframes for entities, history, and sprints.
        
        Args:
            entities_df (pd.DataFrame): Tasks/entities dataset
            history_df (pd.DataFrame): History changes dataset
            sprints_df (pd.DataFrame): Sprints dataset
        """
        self.entities_df = entities_df.copy() if entities_df is not None else None
        self.history_df = history_df.copy() if history_df is not None else None
        self.sprints_df = sprints_df.copy() if sprints_df is not None else None
        
        self.output_dir = Path('analysis/results/core_eda')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        # Store analysis results
        self.results = {
            'entities': {},
            'history': {},
            'sprints': {},
            'cross_analysis': {},
            'metadata': {
                'analysis_timestamp': datetime.now().isoformat(),
                'datasets_analyzed': {
                    'entities': entities_df is not None,
                    'history': history_df is not None,
                    'sprints': sprints_df is not None
                }
            }
        }

    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=self.output_dir / 'core_eda.log'
        )
        self.logger = logging.getLogger(__name__)

    def preprocess_data(self):
        """Preprocess all datasets"""
        try:
            self.logger.info("Starting data preprocessing...")
            
            if self.entities_df is not None:
                # Store original length for data quality metrics
                original_len = len(self.entities_df)
                
                # Remove duplicates
                self.entities_df = self.entities_df.drop_duplicates(subset=['entity_id'])
                
                # Convert date columns with proper error handling
                date_cols = ['create_date', 'update_date', 'due_date']
                for col in date_cols:
                    if col in self.entities_df.columns:
                        self.entities_df[col] = pd.to_datetime(self.entities_df[col], errors='coerce')
                
                # Handle numeric columns
                numeric_cols = ['estimation', 'spent']
                for col in numeric_cols:
                    if col in self.entities_df.columns:
                        # Convert to numeric, handling any non-numeric values
                        self.entities_df[col] = pd.to_numeric(self.entities_df[col], errors='coerce')
                        
                        # Handle outliers using IQR method
                        q1 = self.entities_df[col].quantile(0.25)
                        q3 = self.entities_df[col].quantile(0.75)
                        iqr = q3 - q1
                        lower_bound = q1 - 1.5 * iqr
                        upper_bound = q3 + 1.5 * iqr
                        
                        # Replace outliers with median
                        median = self.entities_df[col].median()
                        self.entities_df[col] = self.entities_df[col].apply(
                            lambda x: median if pd.isna(x) or x < lower_bound or x > upper_bound else x
                        )
                
                # Normalize priority values
                priority_mapping = {
                    'критический': 'Критический',
                    'высокий': 'Высокий',
                    'средний': 'Средний',
                    'низкий': 'Низкий',
                    'critical': 'Критический',
                    'high': 'Высокий',
                    'medium': 'Средний',
                    'low': 'Низкий'
                }
                if 'priority' in self.entities_df.columns:
                    self.entities_df['priority'] = (self.entities_df['priority']
                        .str.lower()
                        .map(priority_mapping)
                        .fillna('Средний'))  # Default to medium priority if unknown
                
                # Calculate processing time (in days)
                if all(col in self.entities_df.columns for col in ['update_date', 'create_date']):
                    self.entities_df['processing_time'] = (
                        self.entities_df['update_date'] - self.entities_df['create_date']
                    ).dt.total_seconds() / (24 * 3600)
                    self.entities_df['processing_time'] = self.entities_df['processing_time'].clip(lower=0)
                
                # Use area as team indicator
                if 'area' in self.entities_df.columns:
                    self.entities_df['team'] = self.entities_df['area']
                
                # Add data quality metrics
                self.results['entities']['data_quality'] = {
                    'original_rows': original_len,
                    'cleaned_rows': len(self.entities_df),
                    'duplicates_removed': original_len - len(self.entities_df),
                    'missing_values': self.entities_df.isnull().sum().to_dict(),
                    'outliers_detected': {
                        col: sum((self.entities_df[col] < lower_bound) | (self.entities_df[col] > upper_bound))
                        for col in numeric_cols if col in self.entities_df.columns
                    },
                    'invalid_dates': {
                        col: sum(self.entities_df[col].isna()) 
                        for col in date_cols if col in self.entities_df.columns
                    },
                    'priority_distribution': (
                        self.entities_df['priority'].value_counts().to_dict()
                        if 'priority' in self.entities_df.columns else {}
                    )
                }

            if self.history_df is not None:
                original_history_len = len(self.history_df)
                
                # Remove duplicates
                self.history_df = self.history_df.drop_duplicates()
                
                # Convert history date with better error handling
                if 'history_date' in self.history_df.columns:
                    self.history_df['history_date'] = pd.to_datetime(
                        self.history_df['history_date'],
                        format='%m/%d/%y %H:%M',
                        errors='coerce'
                    )
                
                # Clean up history changes with improved parsing
                if 'history_change' in self.history_df.columns:
                    # Split history changes into old and new values
                    def extract_change_values(change):
                        if pd.isna(change):
                            return pd.Series({'old_value': '', 'new_value': ''})
                        parts = str(change).split(' -> ')
                        if len(parts) == 2:
                            return pd.Series({'old_value': parts[0].strip(), 'new_value': parts[1].strip()})
                        return pd.Series({'old_value': '', 'new_value': parts[0].strip() if parts else ''})

                    # Apply the extraction function
                    change_values = self.history_df['history_change'].apply(extract_change_values)
                    self.history_df['old_value'] = change_values['old_value']
                    self.history_df['new_value'] = change_values['new_value']
                    
                    # Clean up extracted values
                    self.history_df['old_value'] = self.history_df['old_value'].replace('<empty>', '')
                    self.history_df['new_value'] = self.history_df['new_value'].str.strip()
                
                # Add history data quality metrics
                self.results['history']['data_quality'] = {
                    'original_rows': original_history_len,
                    'cleaned_rows': len(self.history_df),
                    'duplicates_removed': original_history_len - len(self.history_df),
                    'missing_dates': sum(self.history_df['history_date'].isna()),
                    'invalid_changes': sum(
                        (self.history_df['old_value'] == '') & 
                        (self.history_df['new_value'] == '')
                    ) if 'old_value' in self.history_df.columns else 0
                }

            if self.sprints_df is not None:
                original_sprints_len = len(self.sprints_df)
                
                # Remove duplicates
                self.sprints_df = self.sprints_df.drop_duplicates()
                
                # Convert sprint dates
                date_cols = ['sprint_start_date', 'sprint_end_date']
                for col in date_cols:
                    if col in self.sprints_df.columns:
                        self.sprints_df[col] = pd.to_datetime(
                            self.sprints_df[col], 
                            errors='coerce'
                        )
                
                # Convert entity_ids to sets with better error handling
                if 'entity_ids' in self.sprints_df.columns:
                    self.sprints_df['entity_ids'] = self.sprints_df['entity_ids'].apply(
                        lambda x: set(map(str.strip, str(x).strip('{}').split(',')))
                        if pd.notna(x) else set()
                    )
                
                # Add sprints data quality metrics
                self.results['sprints']['data_quality'] = {
                    'original_rows': original_sprints_len,
                    'cleaned_rows': len(self.sprints_df),
                    'duplicates_removed': original_sprints_len - len(self.sprints_df),
                    'invalid_dates': {
                        col: sum(self.sprints_df[col].isna())
                        for col in date_cols if col in self.sprints_df.columns
                    },
                    'empty_sprints': sum(
                        self.sprints_df['entity_ids'].apply(len) == 0
                    ) if 'entity_ids' in self.sprints_df.columns else 0
                }
            
            self.logger.info("Data preprocessing completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during preprocessing: {str(e)}")
            raise

    def analyze_entities(self):
        """Analyze the entities (tasks) dataset"""
        if self.entities_df is None:
            return
        
        entity_analysis = {
            'basic_stats': {
                'total_tasks': len(self.entities_df),
                'unique_assignees': self.entities_df['assignee'].nunique(),
                'priority_distribution': self.entities_df['priority'].value_counts().to_dict(),
                'avg_processing_time': float(self.entities_df['processing_time'].mean()),
                'median_processing_time': float(self.entities_df['processing_time'].median())
            },
            'temporal_patterns': {
                'tasks_by_month': self.entities_df.groupby(
                    self.entities_df['create_date'].dt.strftime('%Y-%m')
                ).size().to_dict(),
                'avg_processing_time_by_priority': self.entities_df.groupby('priority')[
                    'processing_time'
                ].mean().to_dict()
            },
            'workload_analysis': {
                'tasks_per_assignee': self.entities_df['assignee'].value_counts().head(10).to_dict(),
                'avg_tasks_per_assignee': float(len(self.entities_df) / self.entities_df['assignee'].nunique())
            }
        }
        
        self.results['entities'] = entity_analysis
        self._create_entities_visualizations()

    def analyze_history(self):
        """Analyze the history dataset"""
        if self.history_df is None:
            return
        
        history_analysis = {
            'change_patterns': {
                'total_changes': len(self.history_df),
                'changes_by_type': self.history_df['history_property_name'].value_counts().to_dict(),
                'changes_by_entity': self.history_df['entity_id'].value_counts().describe().to_dict()
            },
            'temporal_analysis': {
                'changes_by_month': self.history_df.groupby(
                    self.history_df['history_date'].dt.strftime('%Y-%m')
                ).size().to_dict(),
                'avg_changes_per_day': float(
                    self.history_df.groupby(self.history_df['history_date'].dt.date).size().mean()
                )
            },
            'status_transitions': self._analyze_status_transitions()
        }
        
        self.results['history'] = history_analysis
        self._create_history_visualizations()

    def analyze_sprints(self):
        """Analyze the sprints dataset"""
        if self.sprints_df is None:
            return
        
        # Calculate duration safely
        duration_series = (
            self.sprints_df['sprint_end_date'] - self.sprints_df['sprint_start_date']
        ).dt.total_seconds() / (24 * 3600)  # Convert to days
        
        sprint_analysis = {
            'basic_stats': {
                'total_sprints': len(self.sprints_df),
                'avg_duration': float(duration_series.mean()) if not duration_series.empty else 0.0,
                'status_distribution': self.sprints_df['sprint_status'].value_counts().to_dict()
            },
            'task_metrics': {
                'avg_tasks_per_sprint': float(pd.Series([len(ids) for ids in self.sprints_df['entity_ids']]).mean()),
                'max_tasks_per_sprint': int(max(len(ids) for ids in self.sprints_df['entity_ids'])),
                'min_tasks_per_sprint': int(min(len(ids) for ids in self.sprints_df['entity_ids']))
            },
            'temporal_patterns': {
                'sprints_by_month': self.sprints_df.groupby(
                    self.sprints_df['sprint_start_date'].dt.strftime('%Y-%m')
                ).size().to_dict()
            }
        }
        
        self.results['sprints'] = sprint_analysis
        self._create_sprint_visualizations()

    def cross_dataset_analysis(self):
        """Perform analysis across datasets"""
        if not all([self.entities_df is not None, 
                   self.history_df is not None, 
                   self.sprints_df is not None]):
            return
        
        cross_analysis = {
            'task_lifecycle': self._analyze_task_lifecycle(),
            'sprint_efficiency': self._analyze_sprint_efficiency(),
            'workload_distribution': self._analyze_workload_distribution()
        }
        
        self.results['cross_analysis'] = cross_analysis

    def _analyze_status_transitions(self):
        """Analyze status transitions from history data"""
        status_changes = self.history_df[
            self.history_df['history_property_name'] == 'Статус'
        ].copy()
        
        # Convert tuple keys to strings for JSON serialization
        transitions = status_changes.groupby(['old_value', 'new_value']).size()
        transitions_dict = {
            f"{old_val} -> {new_val}": count 
            for (old_val, new_val), count in transitions.items()
        }
        
        return transitions_dict

    def _analyze_task_lifecycle(self):
        """Analyze task lifecycle across datasets"""
        lifecycle_metrics = {
            'avg_time_to_completion': {},
            'completion_rates': {},
            'sprint_completion_correlation': {}
        }
        
        # Calculate average time to completion by priority
        for priority in self.entities_df['priority'].unique():
            priority_tasks = self.entities_df[self.entities_df['priority'] == priority]
            avg_time = float(priority_tasks['processing_time'].mean())
            lifecycle_metrics['avg_time_to_completion'][priority] = avg_time
        
        # Calculate completion rates by sprint
        for _, sprint in self.sprints_df.iterrows():
            # Get the entity IDs for this sprint
            sprint_entity_ids = sprint['entity_ids']
            
            # Find tasks that belong to this sprint
            sprint_tasks = self.entities_df[
                self.entities_df['entity_id'].isin(sprint_entity_ids)  # Changed from 'id' to 'entity_id'
            ]
            
            if not sprint_tasks.empty:
                completion_rate = float(
                    (sprint_tasks['status'] == 'Completed').mean()
                    if 'status' in sprint_tasks.columns else 0.0
                )
            else:
                completion_rate = 0.0
                
            lifecycle_metrics['completion_rates'][sprint['sprint_name']] = completion_rate
        
        return lifecycle_metrics

    def _analyze_sprint_efficiency(self):
        """Analyze sprint efficiency metrics"""
        efficiency_metrics = {
            'completion_rate': {},
            'velocity': {},
            'predictability': {}
        }
        
        for _, sprint in self.sprints_df.iterrows():
            sprint_entity_ids = sprint['entity_ids']
            
            # Find tasks that belong to this sprint
            sprint_tasks = self.entities_df[
                self.entities_df['entity_id'].isin(sprint_entity_ids)  # Changed from 'id' to 'entity_id'
            ]
            
            # Calculate completion rate
            completion_rate = float(
                (sprint_tasks['status'] == 'Completed').mean()
                if not sprint_tasks.empty and 'status' in sprint_tasks.columns else 0.0
            )
            efficiency_metrics['completion_rate'][sprint['sprint_name']] = completion_rate
            
            # Calculate velocity (tasks per day)
            sprint_duration = (sprint['sprint_end_date'] - sprint['sprint_start_date']).days
            velocity = len(sprint_tasks) / max(sprint_duration, 1)
            efficiency_metrics['velocity'][sprint['sprint_name']] = float(velocity)
        
        return efficiency_metrics

    def _analyze_workload_distribution(self):
        """Analyze workload distribution across assignees and sprints"""
        workload_metrics = {
            'assignee_load': {},
            'sprint_load': {},
            'team_capacity': {}
        }
        
        # Calculate assignee workload
        assignee_tasks = self.entities_df.groupby('assignee').size()
        workload_metrics['assignee_load'] = assignee_tasks.to_dict()
        
        # Calculate sprint workload
        sprint_tasks = self.sprints_df['entity_ids'].apply(len)
        workload_metrics['sprint_load'] = sprint_tasks.to_dict()
        
        return workload_metrics

    def _create_entities_visualizations(self):
        """Create visualizations for entities dataset"""
        # Priority distribution
        plt.figure(figsize=(10, 6))
        sns.countplot(data=self.entities_df, x='priority')
        plt.title('Task Distribution by Priority')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(self.output_dir / 'priority_distribution.png')
        plt.close()
        
        # Processing time by priority
        plt.figure(figsize=(10, 6))
        sns.boxplot(data=self.entities_df, x='priority', y='processing_time')
        plt.title('Processing Time by Priority')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(self.output_dir / 'processing_time_distribution.png')
        plt.close()

    def _create_history_visualizations(self):
        """Create visualizations for history dataset"""
        # Changes over time
        plt.figure(figsize=(12, 6))
        changes_by_date = self.history_df.groupby(
            self.history_df['history_date'].dt.date
        ).size()
        plt.plot(changes_by_date.index, changes_by_date.values)
        plt.title('Changes Over Time')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(self.output_dir / 'changes_over_time.png')
        plt.close()

    def _create_sprint_visualizations(self):
        """Create visualizations for sprints dataset"""
        # Sprint duration distribution
        plt.figure(figsize=(10, 6))
        sprint_durations = (
            self.sprints_df['sprint_end_date'] - self.sprints_df['sprint_start_date']
        ).dt.total_seconds() / (24 * 3600)  # Convert to days
        plt.hist(sprint_durations, bins=20)
        plt.title('Sprint Duration Distribution')
        plt.xlabel('Duration (days)')
        plt.ylabel('Count')
        plt.tight_layout()
        plt.savefig(self.output_dir / 'sprint_duration_distribution.png')
        plt.close()

    def run_analysis(self):
        """Run all analyses and save results"""
        try:
            print("Starting Core EDA analysis...")
            
            # Preprocess data
            self.preprocess_data()
            
            # Run individual analyses
            self.analyze_entities()
            self.analyze_history()
            self.analyze_sprints()
            self.cross_dataset_analysis()
            
            # Save results to JSON
            results_file = self.output_dir / 'core_eda_results.json'
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"\nAnalysis completed successfully. Results saved to {results_file}")
            return self.results
            
        except Exception as e:
            print(f"Error during analysis: {str(e)}")
            raise

def main():
    """Main function to run the core EDA analysis"""
    try:
        print("Loading datasets...")
        
        # Load entities data
        entities_df = pd.read_csv(
            "analysis/data_for_spb_hakaton_entities/data_for_spb_hakaton_entities1-Table 1.csv",
            encoding='utf-8',
            sep=';',  # Using semicolon separator
            skiprows=1  # Skip the "Table 1" header
        )
        
        # Load history data
        history_df = pd.read_csv(
            "analysis/data_for_spb_hakaton_entities/history-Table 1.csv",
            encoding='utf-8',
            sep=';',
            skiprows=1
        )
        
        # Load sprints data
        sprints_df = pd.read_csv(
            "analysis/data_for_spb_hakaton_entities/sprints-Table 1.csv",
            encoding='utf-8',
            sep=';',
            skiprows=1
        )
        
        print("Datasets loaded successfully")
        
        # Initialize and run analysis
        eda = CoreEDA(entities_df, history_df, sprints_df)
        results = eda.run_analysis()
        
        # Print key insights
        print("\nKey Insights:")
        print("-" * 50)
        if 'entities' in results:
            print(f"Total tasks: {results['entities']['basic_stats']['total_tasks']}")
            print(f"Unique assignees: {results['entities']['basic_stats']['unique_assignees']}")
        if 'sprints' in results:
            print(f"Total sprints: {results['sprints']['basic_stats']['total_sprints']}")
        if 'history' in results:
            print(f"Total changes tracked: {results['history']['change_patterns']['total_changes']}")
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        raise

if __name__ == "__main__":
    main() 