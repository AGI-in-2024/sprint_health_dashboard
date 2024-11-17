import pandas as pd
from datetime import datetime
import json
import os
import logging
import warnings

class DataLoader:
    def __init__(self):
        self.tasks = pd.DataFrame()
        self.sprints = pd.DataFrame()
        self.history = pd.DataFrame()
        
        # Add data_dir attribute
        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')
        
        # Add error state tracking
        self.is_loaded = False
        self.load_errors = []
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('app.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _parse_dates(self, df, date_columns, date_format=None):
        """Parse date columns with proper format"""
        for col in date_columns:
            if col in df.columns:
                try:
                    if date_format:
                        df[col] = pd.to_datetime(df[col], format=date_format, errors='coerce')
                    else:
                        # Suppress warnings for date parsing
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            df[col] = pd.to_datetime(df[col], errors='coerce')
                except Exception as e:
                    self.logger.error(f"Error converting dates for column {col}: {str(e)}")
        return df

    def parse_entity_ids(self, x):
        """Parse entity_ids string into a set of integers"""
        if pd.isna(x):
            return set()
        if isinstance(x, str):
            try:
                # Remove any whitespace and quotes
                x = x.strip().strip('"\'')
                if not x:
                    return set()
                # Handle both {} and [] formats
                x = x.replace('{', '[').replace('}', ']')
                # Handle potential comma issues
                x = x.replace(' ', '')
                if x.startswith('['):
                    try:
                        ids = json.loads(x)
                    except:
                        # Fallback for malformed JSON
                        ids = [int(id_.strip()) for id_ in x.strip('[]').split(',') if id_.strip()]
                else:
                    ids = [int(id_.strip()) for id_ in x.split(',') if id_.strip()]
                return set(ids)
            except Exception as e:
                print(f"Error parsing entity_ids '{x[:100]}...': {e}")
                return set()
        elif isinstance(x, (list, set)):
            return set(x)
        return set()

    def load_data(self):
        """Load data with better error handling and validation"""
        try:
            # Load data
            self._load_tasks()
            self._load_sprints()
            self._load_history()
            
            # Validate loaded data
            if self._validate_loaded_data():
                self.is_loaded = True
                self.logger.info("Data loaded and validated successfully")
            else:
                self.is_loaded = False
                error_msg = "Data validation failed"
                self.load_errors.append(error_msg)
                self.logger.error(error_msg)
                
        except Exception as e:
            self.is_loaded = False
            self.load_errors.append(str(e))
            self.logger.error(f"Failed to load data: {e}")
            raise

    def _load_tasks(self):
        data_dir = os.path.join(os.path.dirname(__file__), 'data')

        # Load tasks data
        tasks_path = os.path.join(data_dir, 'data_for_spb_hakaton_entities1-Table 1.csv')
        self.logger.info(f"Loading tasks from {tasks_path}")
        
        tasks_df = pd.read_csv(tasks_path, sep=';', encoding='utf-8')
        
        # If the data is in MultiIndex format, reset it
        if isinstance(tasks_df.index, pd.MultiIndex):
            tasks_df = tasks_df.reset_index()
            column_names = tasks_df.iloc[0]
            tasks_df = tasks_df.iloc[1:].reset_index(drop=True)
            tasks_df.columns = column_names
        
        # Remove duplicate columns
        tasks_df = tasks_df.loc[:, ~tasks_df.columns.duplicated()]
        
        # Ensure 'entity_id' column is properly formatted
        if 'entity_id' in tasks_df.columns:
            tasks_df['entity_id'] = pd.to_numeric(tasks_df['entity_id'], errors='coerce').astype('Int64')
        
        # Parse 'links' field if present
        if 'links' in tasks_df.columns:
            tasks_df['links'] = tasks_df['links'].astype(str)
        
        # Parse dates for tasks
        tasks_date_cols = ['create_date', 'update_date', 'due_date']
        tasks_df = self._parse_dates(tasks_df, tasks_date_cols)
        
        # After loading and processing the data
        self.logger.info(f"Tasks DataFrame shape: {tasks_df.shape}")
        self.logger.info(f"Tasks columns: {tasks_df.columns.tolist()}")
        
        # Ensure area column is properly formatted
        if 'area' in tasks_df.columns:
            if isinstance(tasks_df['area'], pd.DataFrame):
                self.logger.warning("Area column is a DataFrame, converting to Series")
                tasks_df['area'] = tasks_df['area'].iloc[:, 0]
        
        self.tasks = tasks_df

    def _load_sprints(self):
        """Load and process sprints data with better error handling"""
        try:
            # First try to load from tasks data
            if not self.tasks.empty:
                # Get unique areas
                areas = self.tasks['area'].unique()
                
                # Generate synthetic sprints from task creation dates for each area
                synthetic_sprints = []
                
                for area in areas:
                    area_tasks = self.tasks[self.tasks['area'] == area]
                    if area_tasks.empty:
                        continue
                    
                    start_date = area_tasks['create_date'].min()
                    end_date = area_tasks['create_date'].max()
                    
                    # Create 2-week sprints
                    sprint_dates = pd.date_range(start=start_date, end=end_date, freq='2W')
                    
                    for i in range(len(sprint_dates) - 1):
                        sprint_start = sprint_dates[i]
                        sprint_end = sprint_dates[i + 1]
                        
                        # Get tasks created during this sprint for this area
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
                                'area': area  # Add area to sprint data
                            })
                
                self.sprints = pd.DataFrame(synthetic_sprints)
                self.logger.info(f"Generated {len(synthetic_sprints)} synthetic sprints across {len(areas)} areas")
                return
            
            # If no tasks data or synthetic sprint generation fails, try loading from file
            sprints_path = os.path.join(self.data_dir, 'sprints.csv')
            if os.path.exists(sprints_path):
                # Try different delimiters
                for delimiter in [',', ';', '\t']:
                    try:
                        self.sprints = pd.read_csv(sprints_path, delimiter=delimiter)
                        if not self.sprints.empty:
                            break
                    except:
                        continue
            
            # If still empty, create empty DataFrame with required columns
            if self.sprints.empty:
                self.sprints = pd.DataFrame(columns=[
                    'sprint_name', 'sprint_start_date', 'sprint_end_date', 'entity_ids'
                ])
                self.logger.warning("Created empty sprints DataFrame with required columns")
            
            # Process dates if we have data
            if not self.sprints.empty:
                if 'sprint_start_date' in self.sprints.columns:
                    self.sprints['sprint_start_date'] = pd.to_datetime(
                        self.sprints['sprint_start_date'], errors='coerce'
                    )
                if 'sprint_end_date' in self.sprints.columns:
                    self.sprints['sprint_end_date'] = pd.to_datetime(
                        self.sprints['sprint_end_date'], errors='coerce'
                    )
                
                # Convert entity_ids to list if needed
                if 'entity_ids' in self.sprints.columns:
                    self.sprints['entity_ids'] = self.sprints['entity_ids'].apply(
                        lambda x: eval(x) if isinstance(x, str) else ([] if pd.isna(x) else x)
                    )
            
            self.logger.info(f"Sprints DataFrame shape: {self.sprints.shape}")
            self.logger.info(f"Sprints columns: {self.sprints.columns.tolist()}")
            
        except Exception as e:
            self.logger.error(f"Error loading sprints data: {str(e)}")
            # Create empty DataFrame with required columns
            self.sprints = pd.DataFrame(columns=[
                'sprint_name', 'sprint_start_date', 'sprint_end_date', 'entity_ids'
            ])

    def _load_history(self):
        data_dir = os.path.join(os.path.dirname(__file__), 'data')

        # Load history data
        history_path = os.path.join(data_dir, 'history-Table 1.csv')
        self.logger.info(f"Loading history from {history_path}")
        
        history_df = pd.read_csv(history_path, sep=';', encoding='utf-8')
        
        if isinstance(history_df.index, pd.MultiIndex):
            historyu_df = history_df.reset_index()
            column_names = history_df.iloc[0]
            history_df = history_df.iloc[1:].reset_index(drop=True)
            history_df.columns = column_names
        
        # Parse dates for history
        history_date_cols = ['history_date']
        history_df = self._parse_dates(history_df, history_date_cols)

        # Ensure 'history_change' is a string and fill NaN values
        if 'history_change' in history_df.columns:
            history_df['history_change'] = history_df['history_change'].astype(str).fillna('')

        self.history = history_df

    def print_data_info(self):
        """Print information about loaded data for debugging"""
        self.logger.info("\nData Loading Information:")
        
        self.logger.info("\nTasks DataFrame:")
        self.logger.info(f"Shape: {self.tasks.shape}")
        self.logger.info(f"Columns: {self.tasks.columns.tolist()}")
        if not self.tasks.empty:
            first_row_sample = {k: self.tasks.iloc[0][k] for k in list(self.tasks.columns)[:5]}
            self.logger.info(f"\nFirst row sample (first 5 columns):\n{first_row_sample}")
        
        self.logger.info("\nSprints DataFrame:")
        self.logger.info(f"Shape: {self.sprints.shape}")
        self.logger.info(f"Columns: {self.sprints.columns.tolist()}")
        if not self.sprints.empty:
            first_row_sample = {k: self.sprints.iloc[0][k] for k in list(self.sprints.columns)[:4]}
            self.logger.info(f"\nFirst row sample (first 4 columns):\n{first_row_sample}")
        
        self.logger.info("\nHistory DataFrame:")
        self.logger.info(f"Shape: {self.history.shape}")
        self.logger.info(f"Columns: {self.history.columns.tolist()}")
        if not self.history.empty:
            first_row_sample = {k: self.history.iloc[0][k] for k in list(self.history.columns)[:4]}
            self.logger.info(f"\nFirst row sample (first 4 columns):\n{first_row_sample}")

        self.logger.info("\nUnique entity_ids in Tasks DataFrame:")
        self.logger.info(f"Count: {self.tasks['entity_id'].nunique()}")
        self.logger.info(f"Sample: {self.tasks['entity_id'].dropna().unique()[:5]}")

        self.logger.info("\nSample of entity_ids in Sprints DataFrame:")
        self.logger.info(f"First sprint's entity_ids: {list(self.sprints.iloc[0]['entity_ids'])[:5]}")

    def print_unique_values(self):
        """Print unique values of key columns for debugging"""
        self.logger.info("\nUnique values in key columns:")
        self.logger.info("\nStatus values:")
        self.logger.info(sorted(self.tasks['status'].unique()))
        
        self.logger.info("\nResolution values:")
        self.logger.info(sorted(self.tasks['resolution'].dropna().unique()))
        
        self.logger.info("\nWorkgroup values:")
        self.logger.info(sorted(self.tasks['workgroup'].dropna().unique()))
        
        # Print some statistics
        self.logger.info("\nEstimation statistics:")
        self.logger.info(self.tasks['estimation'].describe())

    def _validate_loaded_data(self):
        """Validate loaded data for completeness and correctness"""
        try:
            # Add detailed data validation logging
            self.logger.info("\nValidating loaded data:")
            
            # Check DataFrames
            self.logger.info("Checking DataFrame sizes:")
            self.logger.info(f"Tasks: {self.tasks.shape}")
            self.logger.info(f"Sprints: {self.sprints.shape}")
            self.logger.info(f"History: {self.history.shape}")
            
            if self.tasks.empty:
                self.logger.error("Tasks DataFrame is empty")
                return False
            if self.sprints.empty:
                self.logger.error("Sprints DataFrame is empty")
                return False
            if self.history.empty:
                self.logger.error("History DataFrame is empty")
                return False

            # Log status distribution
            self.logger.info("\nStatus Distribution:")
            status_counts = self.tasks['status'].value_counts()
            for status, count in status_counts.items():
                self.logger.info(f"{status}: {count}")

            # Log resolution distribution
            self.logger.info("\nResolution Distribution:")
            resolution_counts = self.tasks['resolution'].value_counts(dropna=False)
            for resolution, count in resolution_counts.items():
                self.logger.info(f"{resolution}: {count}")

            # Validate required columns in tasks
            required_task_columns = ['entity_id', 'status', 'area', 'estimation']
            if not all(col in self.tasks.columns for col in required_task_columns):
                self.logger.error(f"Missing required columns in tasks: {set(required_task_columns) - set(self.tasks.columns)}")
                return False

            # Validate required columns in sprints
            required_sprint_columns = ['sprint_name', 'sprint_start_date', 'sprint_end_date', 'entity_ids']
            if not all(col in self.sprints.columns for col in required_sprint_columns):
                self.logger.error(f"Missing required columns in sprints: {set(required_sprint_columns) - set(self.sprints.columns)}")
                return False

            # Validate required columns in history
            required_history_columns = ['entity_id', 'history_property_name', 'history_date', 'history_change']
            if not all(col in self.history.columns for col in required_history_columns):
                self.logger.error(f"Missing required columns in history: {set(required_history_columns) - set(self.history.columns)}")
                return False

            # Validate entity_ids in sprints
            for _, row in self.sprints.iterrows():
                if not isinstance(row['entity_ids'], set):
                    self.logger.error(f"Invalid entity_ids format in sprint {row['sprint_name']}")
                    return False

            # Validate date formats
            if not pd.api.types.is_datetime64_any_dtype(self.sprints['sprint_start_date']):
                self.logger.error("Invalid sprint_start_date format")
                return False
            if not pd.api.types.is_datetime64_any_dtype(self.sprints['sprint_end_date']):
                self.logger.error("Invalid sprint_end_date format")
                return False

            # Additional validations can be added here

            self.logger.info("Data validation completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error during data validation: {str(e)}")
            return False

    def check_data_quality(self):
        """Perform detailed data quality checks"""
        try:
            self.logger.info("\nPerforming data quality checks:")
            
            # Check for missing values
            self.logger.info("\nMissing values in Tasks:")
            missing_tasks = self.tasks.isnull().sum()
            for col, count in missing_tasks[missing_tasks > 0].items():
                self.logger.info(f"{col}: {count} missing values")
            
            # Check date ranges
            self.logger.info("\nDate ranges:")
            if 'create_date' in self.tasks.columns:
                self.logger.info(f"Tasks create_date range: "
                               f"{self.tasks['create_date'].min()} to "
                               f"{self.tasks['create_date'].max()}")
            
            # Check estimation values
            self.logger.info("\nEstimation statistics:")
            # Convert estimation to numeric, coercing errors to NaN
            estimation_numeric = pd.to_numeric(self.tasks['estimation'], errors='coerce')
            self.logger.info(estimation_numeric.describe())
            
            # Check status transitions in history
            status_changes = self.history[
                self.history['history_property_name'] == 'Статус'
            ]
            self.logger.info("\nStatus changes statistics:")
            self.logger.info(f"Total status changes: {len(status_changes)}")
            
            # Check for potential data anomalies
            self.logger.info("\nChecking for anomalies:")
            
            # Tasks without status
            tasks_no_status = self.tasks['status'].isnull().sum()
            self.logger.info(f"Tasks without status: {tasks_no_status}")
            
            # Tasks with future dates
            future_tasks = self.tasks[
                self.tasks['create_date'] > pd.Timestamp.now()
            ]
            self.logger.info(f"Tasks with future dates: {len(future_tasks)}")
            
            # Tasks with negative estimation
            negative_est = estimation_numeric[estimation_numeric < 0]
            self.logger.info(f"Tasks with negative estimation: {len(negative_est)}")
            
            # Additional checks for estimation values
            self.logger.info("\nEstimation value distribution:")
            value_counts = estimation_numeric.value_counts().sort_index()
            self.logger.info("Most common estimation values:")
            self.logger.info(value_counts.head())
            
            # Check for unusually high estimations
            high_est_threshold = estimation_numeric.quantile(0.95)  # 95th percentile
            high_est = estimation_numeric[estimation_numeric > high_est_threshold]
            self.logger.info(f"\nTasks with unusually high estimation (>{high_est_threshold:.0f}):")
            self.logger.info(f"Count: {len(high_est)}")
            
            # Log summary statistics
            self.logger.info("\nData Quality Summary:")
            self.logger.info(f"Total tasks: {len(self.tasks)}")
            self.logger.info(f"Tasks with estimation: {estimation_numeric.notna().sum()}")
            self.logger.info(f"Tasks without estimation: {estimation_numeric.isna().sum()}")
            self.logger.info(f"Average estimation: {estimation_numeric.mean():.2f}")
            self.logger.info(f"Median estimation: {estimation_numeric.median():.2f}")
            
        except Exception as e:
            self.logger.error(f"Error in data quality check: {str(e)}")
            self.logger.error("Continuing despite data quality check error")
            # Don't raise the exception, just log it and continue