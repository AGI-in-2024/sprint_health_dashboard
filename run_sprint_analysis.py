from analysis.sprint_health import SprintHealthAnalyzer
import logging
from pathlib import Path

def setup_logging():
    """Configure logging for the application"""
    log_dir = Path('analysis/logs')
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'sprint_analysis.log'),
            logging.StreamHandler()  # Also print to console
        ]
    )

def analyze_single_sprint(sprint_id: str):
    """Analyze a single sprint and generate reports"""
    try:
        # Initialize the analyzer
        analyzer = SprintHealthAnalyzer()
        
        # Load the data
        logging.info("Loading data...")
        analyzer.load_data()
        
        # Set history DataFrame for metrics calculator
        analyzer.metrics_calculator.set_history_df(analyzer.history_df)
        
        # Run analysis for specific sprint
        logging.info(f"\nAnalyzing sprint: {sprint_id}")
        sprint_metrics = analyzer.analyze_sprint_health(sprint_id)
        
        # Print summary results
        print("\nSprint Health Analysis Results:")
        print(f"Overall Health Score: {sprint_metrics['health_score']:.2f}")
        print("\nComponent Scores:")
        for component, score in sprint_metrics['health_scores']['components'].items():
            print(f"{component}: {score:.2f}")
        
        # Print output location
        print(f"\nDetailed results saved in: analysis/results/sprint_health/{sprint_id}/")
        print("Generated files:")
        print("- daily_status_distribution.png")
        print("- health_score.png")
        print("- health_components.png")
        print("- metrics.json")
        
    except ValueError as e:
        logging.error(str(e))
        available_sprints = analyzer.sprints_df['sprint_name'].tolist()
        logging.info(f"Available sprints: {available_sprints}")
        
    except Exception as e:
        logging.error(f"Error analyzing sprint: {str(e)}")
        raise

def main():
    """Main entry point"""
    try:
        # Setup logging
        setup_logging()
        
        # Get sprint ID (could be modified to accept command line arguments)
        sprint_id = "Sprint 1"  # Replace with desired sprint ID
        
        # Run analysis
        analyze_single_sprint(sprint_id)
        
    except Exception as e:
        logging.error(f"Application error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 