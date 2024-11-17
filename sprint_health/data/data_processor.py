import pandas as pd
from pathlib import Path
from typing import Tuple
import logging

class DataProcessor:
    @staticmethod
    def load_data(data_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load and preprocess all required data files"""
        try:
            # Load history data
            history_df = pd.read_csv(
                data_dir / "history-Table 1.csv",
                encoding='utf-8',
                sep=';',
                skiprows=1
            )
            
            # Load tasks data (assuming it exists in your dataset)
            tasks_df = pd.read_csv(
                data_dir / "data_for_spb_hakaton_entities1-Table 1.csv",
                encoding='utf-8',
                sep=';'
            )
            
            # Create sprints dataframe from history data
            sprints_df = DataProcessor._extract_sprints_data(history_df)
            
            # Preprocess data
            tasks_df = DataProcessor._preprocess_tasks(tasks_df)
            history_df = DataProcessor._preprocess_history(history_df)
            
            return tasks_df, history_df, sprints_df
            
        except Exception as e:
            logging.error(f"Error loading data: {str(e)}")
            raise
    
    @staticmethod
    def _preprocess_tasks(df: pd.DataFrame) -> pd.DataFrame:
        """Preprocess tasks dataframe"""
        df = df.copy()
        
        # Map Russian column names to expected names
        column_mapping = {
            'Когда создана': 'create_date',
            'Когда обновлена последний раз': 'update_date',
            'Срок исполнения': 'due_date',
            'Оценка в часах': 'estimation',
            'Приоритет': 'priority',
            'GUID задачи': 'entity_id',
            'На кого назначена': 'assignee',
            'Рабочая группа': 'team'
        }
        df = df.rename(columns=column_mapping)
        
        # Convert dates to datetime
        date_columns = ['create_date', 'update_date', 'due_date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format='%m/%d/%y %H:%M', errors='coerce')
        
        # Convert estimation to hours if needed
        if 'estimation' in df.columns:
            df['estimation'] = pd.to_numeric(df['estimation'].fillna(0), errors='coerce')
            
        # Clean up priority field
        if 'priority' in df.columns:
            priority_map = {
                'Критический': 1,
                'Высокий': 2,
                'Средний': 3,
                'Низкий': 4
            }
            df['priority_value'] = df['priority'].map(priority_map)
        
        return df
    
    @staticmethod
    def _preprocess_history(df: pd.DataFrame) -> pd.DataFrame:
        """Preprocess history dataframe"""
        df = df.copy()
        
        # Map Russian column names
        column_mapping = {
            'history_property_name': 'history_property_name',
            'history_date': 'history_date',
            'history_change': 'history_change',
            'entity_id': 'entity_id'
        }
        df = df.rename(columns=column_mapping)
        
        # Convert dates
        df['history_date'] = pd.to_datetime(df['history_date'], format='%m/%d/%y %H:%M', errors='coerce')
        
        # Extract old and new values from history_change
        df['old_value'] = df['history_change'].str.extract(r'^(.*?)(?:\s+->|$)')
        df['new_value'] = df['history_change'].str.extract(r'.*?->\s*(.*?)$')
        
        # Clean up empty values
        df['old_value'] = df['old_value'].replace('<empty>', None)
        df['new_value'] = df['new_value'].replace('<empty>', None)
        
        return df
    
    @staticmethod
    def _extract_sprints_data(history_df: pd.DataFrame) -> pd.DataFrame:
        """Extract sprint information from history data"""
        sprint_changes = history_df[
            history_df['history_property_name'] == 'Спринт'
        ].copy()
        
        # Get unique sprints and their first/last dates
        sprints = []
        for sprint in sprint_changes['new_value'].unique():
            if pd.isna(sprint):
                continue
                
            sprint_data = sprint_changes[sprint_changes['new_value'] == sprint]
            sprints.append({
                'sprint_id': sprint,
                'start_date': sprint_data['history_date'].min(),
                'end_date': sprint_data['history_date'].max()
            })
        
        return pd.DataFrame(sprints) 