import pandas as pd
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime

class DataLoader:
    """Handles loading and initial processing of datasets for sprint analysis"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define possible data directory paths
        self.possible_paths = [
            Path("data_for_spb_hakaton_entities"),
            Path("new") / "data_for_spb_hakaton_entities",
            Path("analysis") / "data_for_spb_hakaton_entities",
            Path(__file__).parent / "data_for_spb_hakaton_entities",
            Path(__file__).parent.parent / "data_for_spb_hakaton_entities",
            Path("/home/dukhanin/agile_new/new/data_for_spb_hakaton_entities")
        ]
        
        self.data_dir = None
        self.entities_df = None
        self.history_df = None
        self.sprints_df = None

    def load_datasets(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Load all datasets from the data directory
        
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: entities, history, and sprints dataframes
        """
        try:
            self.logger.info("Loading datasets...")
            
            # Find data directory
            self._find_data_directory()
            
            # Load each dataset
            self.entities_df = self._load_entities()
            self.history_df = self._load_history()
            self.sprints_df = self._load_sprints()
            
            # Validate loaded data
            self._validate_datasets()
            
            self.logger.info("All datasets loaded successfully")
            return self.entities_df, self.history_df, self.sprints_df
            
        except Exception as e:
            self.logger.error(f"Error loading datasets: {str(e)}")
            raise

    def _find_data_directory(self):
        """Find the data directory from possible paths"""
        for path in self.possible_paths:
            if path.exists():
                self.data_dir = path
                self.logger.info(f"Found data directory: {self.data_dir}")
                return
                
        raise FileNotFoundError(
            f"Data directory not found. Tried paths:\n"
            f"{chr(10).join([f'- {p.absolute()}' for p in self.possible_paths])}"
        )

    def _load_entities(self) -> pd.DataFrame:
        """Load and process entities dataset"""
        try:
            file_path = self.data_dir / "data_for_spb_hakaton_entities1-Table 1.csv"
            
            if not file_path.exists():
                raise FileNotFoundError(f"Entities file not found: {file_path}")
            
            # Load data
            df = pd.read_csv(
                file_path,
                encoding='utf-8',
                sep=';',
                skiprows=1
            )
            
            # Process combined column if needed
            if 'Table 1' in df.columns:
                df = pd.DataFrame([
                    x.split(';') for x in df['Table 1'].astype(str).values
                ])
                df.columns = [
                    'entity_id', 'area', 'type', 'status', 'state', 'priority', 
                    'ticket_number', 'name', 'create_date', 'created_by', 'update_date',
                    'updated_by', 'parent_ticket_id', 'assignee', 'owner', 'due_date',
                    'rank', 'estimation', 'spent', 'workgroup'
                ]
            
            # Convert date columns
            date_cols = ['create_date', 'update_date', 'due_date']
            for col in date_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(
                        df[col],
                        format='%Y-%m-%d %H:%M:%S.%f',
                        errors='coerce'
                    )
            
            # Convert numeric columns
            numeric_cols = ['estimation', 'spent']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            self.logger.info(f"Loaded entities dataset: {len(df)} rows")
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading entities dataset: {str(e)}")
            raise

    def _load_history(self) -> pd.DataFrame:
        """Load and process history dataset"""
        try:
            file_path = self.data_dir / "history-Table 1.csv"
            
            if not file_path.exists():
                raise FileNotFoundError(f"History file not found: {file_path}")
            
            # Load data
            df = pd.read_csv(
                file_path,
                encoding='utf-8',
                sep=';',
                skiprows=1
            )
            
            # Reset index for proper column structure
            if isinstance(df.index, pd.MultiIndex):
                df = df.reset_index()
            
            # Rename columns
            history_columns = {
                'level_0': 'entity_id',
                'level_1': 'history_property_name',
                'level_2': 'history_date',
                'level_3': 'history_version',
                'level_4': 'history_change_type',
                'level_5': 'history_change'
            }
            df = df.rename(columns=history_columns)
            
            # Convert history_date
            if 'history_date' in df.columns:
                df['history_date'] = pd.to_datetime(
                    df['history_date'],
                    format='%m/%d/%y %H:%M',
                    errors='coerce'
                )
            
            # Process history changes
            if 'history_change' in df.columns:
                def split_history_change(change):
                    if pd.isna(change):
                        return pd.Series({'old_value': None, 'new_value': None})
                    parts = str(change).split(' -> ')
                    if len(parts) == 2:
                        return pd.Series({'old_value': parts[0].strip(), 'new_value': parts[1].strip()})
                    return pd.Series({'old_value': None, 'new_value': parts[0].strip() if parts else None})
                
                change_values = df['history_change'].apply(split_history_change)
                df['old_value'] = change_values['old_value']
                df['new_value'] = change_values['new_value']
            
            self.logger.info(f"Loaded history dataset: {len(df)} rows")
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading history dataset: {str(e)}")
            raise

    def _load_sprints(self) -> pd.DataFrame:
        """Load and process sprints dataset"""
        try:
            file_path = self.data_dir / "sprints-Table 1.csv"
            
            if not file_path.exists():
                raise FileNotFoundError(f"Sprints file not found: {file_path}")
            
            # Load data
            df = pd.read_csv(
                file_path,
                encoding='utf-8',
                sep=';',
                skiprows=1
            )
            
            # Process combined column if needed
            if 'Table 1' in df.columns:
                df['Table 1'] = df['Table 1'].astype(str)
                temp_df = pd.DataFrame([
                    x.split(';') for x in df['Table 1'].values
                ])
                temp_df.columns = [
                    'sprint_name', 'sprint_status', 'sprint_start_date', 
                    'sprint_end_date', 'entity_ids'
                ]
                df = temp_df
            
            # Convert dates
            date_cols = ['sprint_start_date', 'sprint_end_date']
            for col in date_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(
                        df[col],
                        format='%Y-%m-%d %H:%M:%S.%f',
                        errors='coerce'
                    )
            
            # Process entity_ids
            if 'entity_ids' in df.columns:
                df['entity_ids'] = df['entity_ids'].apply(
                    lambda x: set(str(x).strip('{}').split(',')) if pd.notna(x) else set()
                )
            
            self.logger.info(f"Loaded sprints dataset: {len(df)} rows")
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading sprints dataset: {str(e)}")
            raise

    def _validate_datasets(self):
        """Validate loaded datasets for consistency"""
        try:
            # Check if all datasets were loaded
            if any(df is None for df in [self.entities_df, self.history_df, self.sprints_df]):
                raise ValueError("One or more datasets failed to load")
            
            # Validate entities dataset
            if 'entity_id' not in self.entities_df.columns:
                raise ValueError("Entities dataset missing entity_id column")
            
            # Validate history dataset
            if 'entity_id' not in self.history_df.columns:
                raise ValueError("History dataset missing entity_id column")
            
            # Validate sprints dataset
            if 'entity_ids' not in self.sprints_df.columns:
                raise ValueError("Sprints dataset missing entity_ids column")
            
            # Check for data consistency
            history_entities = set(self.history_df['entity_id'].unique())
            entities_ids = set(self.entities_df['entity_id'].unique())
            
            # Check if all history entries refer to valid entities
            invalid_history = history_entities - entities_ids
            if invalid_history:
                self.logger.warning(
                    f"Found {len(invalid_history)} history entries referring to non-existent entities"
                )
            
            self.logger.info("Dataset validation completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error validating datasets: {str(e)}")
            raise

def main():
    """Test data loading functionality"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        loader = DataLoader()
        entities_df, history_df, sprints_df = loader.load_datasets()
        
        print("\nDataset Summary:")
        print(f"Entities: {len(entities_df)} rows")
        print(f"History: {len(history_df)} rows")
        print(f"Sprints: {len(sprints_df)} rows")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main()