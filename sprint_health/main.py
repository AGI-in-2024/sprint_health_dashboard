from pathlib import Path
from data.data_processor import DataProcessor
from analysis.sprint_analyzer import SprintAnalyzer
from datetime import datetime
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        # Load data from the correct path
        data_dir = Path("/home/dukhanin/agile_new/sprint_health/data_for_spb_hakaton_entities")
        logger.info(f"Loading data from {data_dir}")
        
        tasks_df, history_df, sprints_df = DataProcessor.load_data(data_dir)
        
        # Initialize analyzer
        analyzer = SprintAnalyzer(tasks_df, history_df, sprints_df)
        
        # Get all available sprints
        available_sprints = sprints_df['sprint_id'].tolist()
        logger.info(f"Available sprints: {available_sprints}")
        
        # Analyze all sprints
        results = {}
        for sprint_id in available_sprints:
            logger.info(f"Analyzing sprint {sprint_id}")
            health_metrics = analyzer.get_sprint_health(sprint_id)
            results[sprint_id] = health_metrics
            
            # Print results for this sprint
            print(f"\nSprint Health Analysis for {sprint_id}")
            print("-" * 50)
            print(f"Health Score: {health_metrics['health_score']:.1f}%")
            print(f"To Do Tasks: {health_metrics['todo_percentage']:.1f}%")
            print(f"Removed Tasks: {health_metrics['removed_percentage']:.1f}%")
            print(f"Backlog Change: {health_metrics['backlog_change']:.1f}%")
            print(f"Blocked Tasks: {health_metrics['blocked_tasks']['count']}")
        
        # Save results
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        
        with open(results_dir / "sprint_health_analysis.json", "w", encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            
        logger.info("Analysis completed successfully")
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        raise

if __name__ == "__main__":
    main() 