export interface HealthParameters {
  max_todo_percentage: number;
  max_removed_percentage: number;
  max_backlog_change: number;
  uniformity_weight: number;
  backlog_weight: number;
  completion_weight: number;
  quality_weight: number;
}

export interface SprintMetrics {
  todo: number;
  in_progress: number;
  done: number;
  removed: number;
  backlog_changes: number;
  health_score: number;
  blocked_tasks: number;
  health_details: {
    delivery_score: number;
    stability_score: number;
    flow_score: number;
    quality_score: number;
    team_load_score: number;
    completion_rate: number;
    blocked_ratio: number;
    last_day_completion: number;
  };
  daily_metrics?: DailyMetricsData;
}

export interface SprintHealthResponse {
  sprints: {
    [sprintId: string]: SprintData;
  };
  aggregated: {
    health_score: number;
    metrics: Record<string, any>;
  };
}

export interface SprintData {
  health_score: number;
  category_scores: CategoryScores;
  key_metrics: KeyMetricsData;
  daily_metrics: DailyMetricsData;
}

export interface CategoryScores {
  delivery: CategoryScore;
  stability: CategoryScore;
  flow: CategoryScore;
  quality: CategoryScore;
  team_load: CategoryScore;
}

export interface CategoryScore {
  score: number;
  weight: string;
  description: string;
}

export interface KeyMetricsData {
  [key: string]: {
    value: number;
    unit: string;
    description: string;
  };
}

export interface DailyMetricsData {
  [date: string]: {
    todo_percentage: number;
    in_progress_percentage: number;
    done_percentage: number;
    blocked_tasks: number;
    added_tasks: number;
    removed_tasks: number;
  };
}

export interface MetricDetail {
  value: number;
  unit: string;
  description: string;
}

export interface BackendMetrics {
  todo: number;
  in_progress: number;
  done: number;
  removed: number;
  backlog_changes: number;
  health_score: number;
  blocked_tasks: number;
  health_details: {
    delivery_score: number;
    stability_score: number;
    flow_score: number;
    quality_score: number;
    team_load_score: number;
    completion_rate: number;
    blocked_ratio: number;
    last_day_completion: number;
  };
  metrics_snapshot: {
    [key: string]: number;
  };
  daily_metrics?: DailyMetricsData;
}

export type SprintPeriod = {
  startDate: Date;
  endDate: Date;
  sprints: string[];
  type: 'sprint' | 'quarter' | 'halfYear' | 'year';
}; 