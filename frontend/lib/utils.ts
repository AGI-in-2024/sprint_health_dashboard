import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import { HealthParameters, SprintMetrics } from "@/types/sprint"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function calculateHealthScore(metrics: SprintMetrics, parameters: HealthParameters): number {
  const {
    uniformity_weight,
    backlog_weight,
    completion_weight,
    quality_weight
  } = parameters;

  const uniformityScore = metrics.health_details.flow_score;
  const backlogScore = Math.max(0, 100 - metrics.backlog_changes);
  const completionScore = metrics.health_details.completion_rate;
  const qualityScore = metrics.health_details.quality_score;

  return (
    uniformityScore * uniformity_weight +
    backlogScore * backlog_weight +
    completionScore * completion_weight +
    qualityScore * quality_weight
  );
}

export function analyzeStatusTransitions(dailyMetrics: SprintMetrics['daily_metrics']): number {
  if (!dailyMetrics) return 0;
  
  const transitions = Object.values(dailyMetrics).map(metrics => ({
    todo: metrics.todo_percentage,
    inProgress: metrics.in_progress_percentage,
    done: metrics.done_percentage
  }));

  let uniformityScore = 100;
  const lastDayCompletion = transitions[transitions.length - 1]?.done || 0;
  const avgDailyCompletion = transitions.reduce((sum, t) => sum + t.done, 0) / transitions.length;

  if (lastDayCompletion > avgDailyCompletion * 2) {
    uniformityScore *= 0.5;
  }

  return uniformityScore;
}
