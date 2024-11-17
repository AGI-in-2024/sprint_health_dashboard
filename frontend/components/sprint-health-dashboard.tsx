'use client'

import React, { useState, useCallback, useMemo, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"
import { Calendar as CalendarIcon, Layers, Info, ClipboardList, Clock, CheckCircle, XCircle } from 'lucide-react'
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  CartesianGrid, 
  XAxis, 
  YAxis,
  Tooltip as RechartsTooltip
} from 'recharts';
import { motion } from "framer-motion"
import { format } from "date-fns"
import { ru } from "date-fns/locale"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useDropzone } from 'react-dropzone';
import { SprintCharts } from '@/components/SprintCharts'
import { SprintTimeline } from '@/components/sprint-timeline'
import { TooltipProps } from 'recharts'
import { HealthParameters, SprintHealthResponse, SprintMetrics, KeyMetricsData, MetricDetail } from "@/types/sprint";

// API integration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

// Types
type BackendMetrics = {
  todo: number;
  in_progress: number;
  done: number;
  removed: number;
  backlog_changes: number;
  blocked_tasks: number;
  health_score: number;
  health_details: HealthDetails;
  metrics_snapshot: {
    [key: string]: number;
  };
  daily_metrics?: Array<{
    date: string;
    todo_percentage: number;
    in_progress_percentage: number;
    done_percentage: number;
    blocked_tasks: number;
    added_tasks: number;
    removed_tasks: number;
  }>;
  status_distribution?: {
    todo: number;
    in_progress: number;
    done: number;
    removed: number;
  };
  status_transitions?: {
    transition_evenness: number;
  };
  excluded_tasks: {
    [date: string]: { count: number };
  };
  added_tasks: {
    [date: string]: { count: number };
  };
};

type SprintMetrics = {
  todo: number;
  in_progress: number;
  done: number;
  removed: number;
  backlog_changes: number;
  health_score: number;
  blocked_tasks: number;
  daily_changes: Array<{
    day: number;
    added: number;
    removed: number;
  }>;
  todo_trend?: number;
  in_progress_trend?: number;
  done_trend?: number;
  removed_trend?: number;
  status_changes_uniformity?: number;
  health_details: HealthDetails;
}

// Add transformation function
function transformBackendMetrics(data: BackendMetrics, sprintStartDate: string): SprintMetrics {
  const daily_changes = data.daily_metrics 
    ? data.daily_metrics.map((metric) => {
        const date = new Date(metric.date);
        const sprintStart = new Date(sprintStartDate);
        const day = Math.floor((date.getTime() - sprintStart.getTime()) / (1000 * 60 * 60 * 24)) + 1;
        
        return {
          day,
          added: metric.added_tasks,
          removed: -metric.removed_tasks
        };
      })
    : transformLegacyDailyChanges(data, sprintStartDate);

  return {
    todo: data.status_distribution?.todo ?? data.todo,
    in_progress: data.status_distribution?.in_progress ?? data.in_progress,
    done: data.status_distribution?.done ?? data.done,
    removed: data.status_distribution?.removed ?? data.removed,
    backlog_changes: data.backlog_changes,
    health_score: data.health_score ?? 0,
    blocked_tasks: data.blocked_tasks,
    daily_changes,
    todo_trend: 0,
    in_progress_trend: 0,
    done_trend: 0,
    removed_trend: 0,
    status_changes_uniformity: data.status_transitions?.transition_evenness,
    health_details: data.health_details
  };
}

// Helper function to handle legacy data transformation
function transformLegacyDailyChanges(data: BackendMetrics, sprintStartDate: string) {
  const allDates = new Set([
    ...Object.keys(data.excluded_tasks),
    ...Object.keys(data.added_tasks)
  ]);

  const sprintStart = new Date(sprintStartDate);

  return Array.from(allDates)
    .map(dateStr => {
      const added = data.added_tasks[dateStr]?.count || 0;
      const removed = -(data.excluded_tasks[dateStr]?.count || 0);
      const date = new Date(dateStr);
      const day = Math.floor((date.getTime() - sprintStart.getTime()) / (1000 * 60 * 60 * 24)) + 1;

      return { day, added, removed };
    })
    .sort((a, b) => a.day - b.day);
}

// Update type validation
function isValidBackendMetrics(data: any): data is BackendMetrics {
  const baseValidation = (
    typeof data === 'object' &&
    data !== null &&
    typeof data.todo === 'number' &&
    typeof data.in_progress === 'number' &&
    typeof data.done === 'number' &&
    typeof data.removed === 'number' &&
    typeof data.backlog_changes === 'number' &&
    typeof data.health_score === 'number' &&
    typeof data.blocked_tasks === 'number'
  );

  // Optional new fields validation
  if (data.status_distribution) {
    if (typeof data.status_distribution !== 'object') return false;
    // Add validation for status_distribution fields if needed
  }

  if (data.daily_metrics) {
    if (!Array.isArray(data.daily_metrics)) return false;
    // Add validation for daily_metrics array if needed
  }

  return baseValidation;
}

// Update the TimelineControl type
type TimelineControl = {
  currentDay: number;
  totalDays: number;
  timeFramePercentage: number; // Add this to maintain compatibility with API
}

// Add new types for sprint analysis
type SprintPeriod = {
  startDate: Date;
  endDate: Date;
  sprints: string[];
  type: 'sprint' | 'quarter' | 'halfYear' | 'year';
}

type TaskMetrics = {
  hours: number;
  count: number;
}

// Add new types for health details
type HealthDetails = {
  delivery_score: number;
  stability_score: number;
  flow_score: number;
  quality_score: number;
  team_load_score: number;
  completion_rate: number;
  blocked_ratio: number;
  last_day_completion: number;
}

type HealthMetricsSnapshot = {
  completion_score: number;
  stability_score: number;
  distribution_score: number;
  blocked_score: number;
  quality_score: number;
  todo_percentage: number;
  in_progress_percentage: number;
  blocked_percentage: number;
  rework_count: number;
  evenness_score: number;
  last_day_completion_percentage: number;
}

// Add new component for health indicators
function HealthIndicator({ value, threshold, label }: { 
  value: number; 
  threshold: number;
  label: string;
}) {
  const isHealthy = value <= threshold;
  return (
    <div className="flex items-center justify-between p-2 border rounded">
      <span>{label}</span>
      <Badge variant={isHealthy ? "success" : "destructive"}>
        {value.toFixed(1)}% {isHealthy ? "✓" : "!"}
      </Badge>
    </div>
  );
}

function FileUploadZone() {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      const formData = new FormData();
      formData.append('file', file);
      
      fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
      })
      .then(response => response.json())
      .then(data => {
        // Handle successful upload
        console.log('File uploaded successfully:', data);
      })
      .catch(error => {
        console.error('Error uploading file:', error);
      });
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop });

  return (
    <div 
      {...getRootProps()} 
      className={cn(
        "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer",
        isDragActive ? "border-primary" : "border-gray-300"
      )}
    >
      <input {...getInputProps()} />
      {isDragActive ? (
        <p>Перетащите файлы сюда ...</p>
      ) : (
        <p>Перетащите файлы сюда или нажмите для выбора</p>
      )}
    </div>
  );
}

type ChartTooltipProps = {
  active?: boolean;
  payload?: Array<{
    value: number;
    name: string;
    color: string;
  }>;
  label?: string | number;
}

type TooltipEntryType = {
  name: string;
  value: number;
  color: string;
}

// Add new component for detailed health breakdown
function HealthScoreBreakdown({ 
  details, 
  metrics 
}: { 
  details: HealthDetails; 
  metrics: HealthMetricsSnapshot;
}) {
  return (
    <div className="space-y-4">
      {/* Scores Section */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <ScoreCard
          title="Выполнение"
          score={metrics.completion_score}
          weight={30}
        />
        <ScoreCard
          title="Стабильность"
          score={metrics.stability_score}
          weight={25}
        />
        <ScoreCard
          title="Распределение"
          score={metrics.distribution_score}
          weight={20}
        />
        <ScoreCard
          title="Блокировки"
          score={metrics.blocked_score}
          weight={15}
        />
        <ScoreCard
          title="Качество"
          score={metrics.quality_score}
          weight={10}
        />
      </div>

      {/* Penalties and Bonuses */}
      <div className="space-y-2">
        <h4 className="font-semibold">Штрафы и бонусы</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Penalties */}
          <div className="space-y-2">
            {Object.entries(details)
              .filter(([key]) => key.includes('penalty'))
              .map(([key, value]) => (
                <div key={key} className="flex justify-between items-center text-red-500">
                  <span>{formatPenaltyName(key)}</span>
                  <span>-{value.toFixed(1)}</span>
                </div>
              ))}
          </div>
          {/* Bonuses */}
          <div className="space-y-2">
            {Object.entries(details)
              .filter(([key]) => key.includes('bonus'))
              .map(([key, value]) => (
                <div key={key} className="flex justify-between items-center text-green-500">
                  <span>{formatBonusName(key)}</span>
                  <span>+{value.toFixed(1)}</span>
                </div>
              ))}
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <MetricCard
          label="Задачи к выполнению"
          value={`${metrics.todo_percentage.toFixed(1)}%`}
          status={metrics.todo_percentage <= 20 ? 'success' : 'warning'}
        />
        <MetricCard
          label="Задачи в работе"
          value={`${metrics.in_progress_percentage.toFixed(1)}%`}
          status={metrics.in_progress_percentage <= 30 ? 'success' : 'warning'}
        />
        <MetricCard
          label="Заблокированные задачи"
          value={`${metrics.blocked_percentage.toFixed(1)}%`}
          status={metrics.blocked_percentage <= 10 ? 'success' : 'destructive'}
        />
        <MetricCard
          label="Равномерность выполнения"
          value={`${metrics.evenness_score.toFixed(1)}%`}
          status={metrics.evenness_score >= 70 ? 'success' : 'warning'}
        />
        <MetricCard
          label="Завершение в последний день"
          value={`${metrics.last_day_completion_percentage.toFixed(1)}%`}
          status={metrics.last_day_completion_percentage <= 20 ? 'success' : 'destructive'}
        />
        <MetricCard
          label="Количество доработок"
          value={metrics.rework_count.toString()}
          status={metrics.rework_count <= 2 ? 'success' : 'warning'}
        />
      </div>
    </div>
  );
}

// Helper components
function ScoreCard({ title, score, weight }: { title: string; score: number; weight: number }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">
          {score.toFixed(1)}
        </div>
        <p className="text-xs text-muted-foreground">
          Вес: {weight}%
        </p>
      </CardContent>
    </Card>
  );
}

function MetricCard({ 
  label, 
  value, 
  status 
}: { 
  label: string; 
  value: string; 
  status: 'success' | 'warning' | 'destructive' 
}) {
  return (
    <div className="flex justify-between items-center p-2 border rounded">
      <span className="text-sm">{label}</span>
      <Badge variant={status}>{value}</Badge>
    </div>
  );
}

// Helper functions
function formatPenaltyName(key: string): string {
  const names: Record<string, string> = {
    'last_day_rush_penalty': 'Завершение в последний день',
    'uneven_completion_penalty': 'Неравномерное выполнение',
    'backlog_instability_penalty': 'Нестабильность беклога',
    'scope_change_penalty': 'Изменение объема',
    'high_todo_penalty': 'Много задач к выполнению',
    'high_wip_penalty': 'Много задач в работе',
    'blocked_tasks_penalty': 'Заблокированные задачи',
    'rework_penalty': 'Доработки'
  };
  return names[key] || key;
}

function formatBonusName(key: string): string {
  const names: Record<string, string> = {
    'high_uniformity_bonus': 'Равномерное выполнение',
    'low_blocked_bonus': 'Минимум блокировок'
  };
  return names[key] || key;
}

// Add new types for health metrics
type CategoryScore = {
  score: number;
  weight: string;
  description: string;
}

type KeyMetric = {
  value: number;
  unit: string;
  description: string;
}

// Update SprintHealthResponse type to match API
type SprintHealthResponse = {
  health_score: number;
  details: {
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
    delivery_score: number;
    stability_score: number;
    flow_score: number;
    quality_score: number;
    team_load_score: number;
  };
  category_scores: {
    delivery: CategoryScore;
    stability: CategoryScore;
    flow: CategoryScore;
    quality: CategoryScore;
    team_load: CategoryScore;
  };
  key_metrics: {
    completion_rate: MetricDetail;
    scope_changes: MetricDetail;
    blocked_tasks: MetricDetail;
    last_day_completion: MetricDetail;
  };
}

// Add mock data generator for missing metrics
function generateMockMetrics(baseMetrics: any): SprintMetrics {
  return {
    ...baseMetrics,
    todo_trend: Math.random() * 10 - 5,
    in_progress_trend: Math.random() * 10 - 5,
    done_trend: Math.random() * 10 - 5,
    removed_trend: Math.random() * 10 - 5,
    status_changes_uniformity: Math.random() * 100,
    health_details: {
      delivery_score: Math.random() * 100,
      stability_score: Math.random() * 100,
      flow_score: Math.random() * 100,
      quality_score: Math.random() * 100,
      team_load_score: Math.random() * 100,
      completion_rate: Math.random() * 100,
      blocked_ratio: Math.random() * 10,
      last_day_completion: Math.random() * 30
    }
  };
}

// Update API call to use new parameters
const fetchSprintHealth = async (
  sprintIds: string[],
  selectedAreas: string[],
  timeFrame: number
): Promise<SprintHealthResponse> => {
  const queryParams = new URLSearchParams();
  sprintIds.forEach(id => queryParams.append('selected_sprints[]', id));
  selectedAreas.forEach(area => queryParams.append('selected_areas[]', area));
  queryParams.append('time_frame', timeFrame.toString());
  
  const response = await fetch(`${API_BASE_URL}/sprint-health?${queryParams}`);
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to fetch sprint health');
  }
  
  return response.json();
};

// Simplify the health score section component
function HealthScoreSection({ healthMetrics }: { healthMetrics: SprintHealthResponse | null }) {
  if (!healthMetrics) return null;
  
  const { category_scores, key_metrics, health_score } = healthMetrics;

  return (
    <div className="space-y-6">
      {/* Health Score */}
      <div className="flex items-center justify-between">
        <span className="text-4xl font-bold">
          {health_score.toFixed(1)}%
        </span>
        <Badge variant={
          health_score >= 80 ? "success" :
          health_score >= 60 ? "warning" : "destructive"
        }>
          {health_score >= 80 ? "Здоровый" :
           health_score >= 60 ? "Требует внимания" : "Критический"}
        </Badge>
      </div>

      {/* Category Scores */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {Object.entries(category_scores).map(([key, { score, weight, description }]) => (
          <Card key={key}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                {formatCategoryName(key)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{score.toFixed(1)}</div>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <p className="text-xs text-muted-foreground">
                      Вес: {weight}
                    </p>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{description}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {Object.entries(key_metrics).map(([key, { value, unit, description }]) => (
          <div key={key} className="flex justify-between items-center p-2 border rounded">
            <span>{formatMetricName(key)}</span>
            <Badge variant={getMetricVariant(key, value)}>
              {value.toFixed(1)}{unit}
            </Badge>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Info className="h-4 w-4 text-muted-foreground" />
                </TooltipTrigger>
                <TooltipContent>
                  <p>{description}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        ))}
      </div>
    </div>
  );
}

// Add helper function for metric variant
function getMetricVariant(key: string, value: number): "success" | "warning" | "destructive" {
  const thresholds = {
    completion_rate: { success: 80, warning: 60 },
    blocked_tasks: { success: 10, warning: 20 },
    scope_changes: { success: 20, warning: 30 },
    last_day_completion: { success: 20, warning: 30 }
  };

  const threshold = thresholds[key as keyof typeof thresholds];
  if (!threshold) return "warning";

  if (key === "completion_rate") {
    return value >= threshold.success ? "success" :
           value >= threshold.warning ? "warning" : "destructive";
  }

  return value <= threshold.success ? "success" :
         value <= threshold.warning ? "warning" : "destructive";
}

// Move helper functions before component
function formatCategoryName(key: string): string {
  const names: Record<string, string> = {
    delivery: 'Доставка',
    stability: 'Стабильность',
    flow: 'Поток',
    quality: 'Качество',
    team_load: 'Нагрузка',
    delivery_score: 'Доставка',
    stability_score: 'Стабильность',
    flow_score: 'Поток',
    quality_score: 'Качество',
    team_load_score: 'Нагрузка'
  };
  return names[key] || key;
}

function formatMetricName(key: string): string {
  const names: Record<string, string> = {
    completion_rate: 'Завершение',
    scope_changes: 'Изменения',
    blocked_tasks: 'Блокировки',
    rework: 'Доработки',
    tech_debt: 'Тех. долг',
    flow_evenness: 'Равномерность',
    last_day_completion: 'Последний день',
    backlog_changes: 'Изменения беклога',
    health_score: 'Оценка здо��овья',
    status_changes_uniformity: 'Равномерность изменений'
  };
  return names[key] || key;
}

// Add multi-sprint health calculation
async function calculateMultiSprintHealth(sprints: string[]): Promise<SprintHealthResponse> {
  const healthMetrics = await Promise.all(
    sprints.map(sprint => 
      fetch(`${API_BASE_URL}/sprint-health?sprint_id=${sprint}`).then(res => res.json())
    )
  );

  // Aggregate health metrics
  const aggregatedHealth = healthMetrics.reduce((acc, curr) => ({
    health_score: acc.health_score + curr.health_score,
    details: {
      delivery_score: acc.details.delivery_score + curr.details.delivery_score,
      stability_score: acc.details.stability_score + curr.details.stability_score,
      flow_score: acc.details.flow_score + curr.details.flow_score,
      quality_score: acc.details.quality_score + curr.details.quality_score,
      team_load_score: acc.details.team_load_score + curr.details.team_load_score,
      completion_rate: acc.details.completion_rate + curr.details.completion_rate,
      blocked_ratio: acc.details.blocked_ratio + curr.details.blocked_ratio,
      last_day_completion: acc.details.last_day_completion + curr.details.last_day_completion,
    },
    metrics_snapshot: Object.entries(curr.metrics_snapshot).reduce((snapAcc, [key, value]) => ({
      ...snapAcc,
      [key]: (snapAcc[key] || 0) + value
    }), acc.metrics_snapshot)
  }));

  // Calculate averages
  const count = healthMetrics.length;
  return {
    ...aggregatedHealth,
    health_score: aggregatedHealth.health_score / count,
    details: Object.entries(aggregatedHealth.details).reduce((acc, [key, value]) => ({
      ...acc,
      [key]: value / count
    }), {} as SprintHealthResponse['details']),
    metrics_snapshot: Object.entries(aggregatedHealth.metrics_snapshot).reduce((acc, [key, value]) => ({
      ...acc,
      [key]: value / count
    }), {} as SprintHealthResponse['metrics_snapshot'])
  };
}

export function SprintHealthDashboardComponent() {
  // State
  const [sprints, setSprints] = useState<string[]>([]);
  const [areas, setAreas] = useState<string[]>([]);
  const [selectedSprints, setSelectedSprints] = useState<string[]>([]);
  const [selectedAreas, setSelectedAreas] = useState<string[]>([]);
  const [timeFrame, setTimeFrame] = useState<number>(100);
  const [metrics, setMetrics] = useState<SprintMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sprintStartDate, setSprintStartDate] = useState<string>('');
  const [timeline, setTimeline] = useState<TimelineControl>({
    currentDay: 0,
    totalDays: 14,
    timeFramePercentage: 100
  });

  // Add new state for sprint period
  const [sprintPeriod, setSprintPeriod] = useState<SprintPeriod | null>(null);

  // Add new state for health metrics
  const [healthMetrics, setHealthMetrics] = useState<SprintHealthResponse | null>(null);

  // Move calculateSprintPeriod inside component
  const calculateSprintPeriod = useCallback((selectedSprints: string[]): SprintPeriod | null => {
    if (!selectedSprints.length) return null;

    const sprintDates = selectedSprints
      .map(sprintName => {
        const dateMatch = sprintName.match(/\d{4}\.\d+\.\d+/);
        if (dateMatch) {
          const [year, month, day] = dateMatch[0].split('.');
          return new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
        }
        return null;
      })
      .filter((date): date is Date => date !== null)
      .sort((a, b) => a.getTime() - b.getTime());

    if (!sprintDates.length) return null;

    const startDate = sprintDates[0];
    const endDate = sprintDates[sprintDates.length - 1];
    const diffMonths = (endDate.getFullYear() - startDate.getFullYear()) * 12 
      + endDate.getMonth() - startDate.getMonth();

    let type: SprintPeriod['type'] = 'sprint';
    if (sprintDates.length > 1) {
      if (diffMonths <= 3) type = 'quarter';
      else if (diffMonths <= 6) type = 'halfYear';
      else type = 'year';
    }

    return {
      startDate,
      endDate,
      sprints: selectedSprints,
      type
    };
  }, []);

  // Update sprint selection handler
  const handleSprintSelection = useCallback((sprintName: string) => {
    setSelectedSprints(current => {
      const newSelection = current.includes(sprintName)
        ? current.filter(s => s !== sprintName)
        : [...current, sprintName];
      
      // Calculate sprint period
      const period = calculateSprintPeriod(newSelection);
      setSprintPeriod(period);

      if (period) {
        const totalDays = Math.ceil(
          (period.endDate.getTime() - period.startDate.getTime()) / (1000 * 60 * 60 * 24)
        );
        
        // Update timeline with new period information
        setTimeline({
          currentDay: totalDays, // Start at the end
          totalDays: totalDays,
          timeFramePercentage: 100 // Show full timeline initially
        });

        // Set sprint start date for single sprint view
        if (newSelection.length === 1) {
          setSprintStartDate(period.startDate.toISOString());
        }
      } else {
        // Reset timeline when no sprints selected
        setTimeline({
          currentDay: 0,
          totalDays: 14, // Default sprint length
          timeFramePercentage: 100
        });
        setSprintStartDate('');
      }

      return newSelection;
    });
  }, [calculateSprintPeriod]);

  // Fetch available sprints and areas
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [sprintsRes, areasRes] = await Promise.all([
          fetch(`${API_BASE_URL}/sprints`),
          fetch(`${API_BASE_URL}/areas`)
        ]);
        
        if (!sprintsRes.ok || !areasRes.ok) {
          throw new Error('Failed to fetch data');
        }
        
        const sprintsData = await sprintsRes.json();
        const areasData = await areasRes.json();
        
        setSprints(sprintsData.sprints);
        setAreas(areasData.areas);
      } catch (err) {
        console.error('Error fetching data:', err);
        setError('Failed to load sprints and areas data');
      }
    };
    
    fetchData();
  }, []);

  // Add timeline calculation helper
  function calculateSprintDuration(startDate: string): number {
    const start = new Date(startDate);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - start.getTime());
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  }

  // Add timeline handler
  const handleTimelineChange = useCallback((percentage: number, day: number) => {
    // Preserve current selections before timeline update
    setTimeline(current => {
      // Only update if we have valid selections
      if (selectedSprints.length === 0 || selectedAreas.length === 0) {
        return current;
      }
      
      return {
        ...current,
        timeFramePercentage: percentage,
        currentDay: day
      };
    });
  }, [selectedSprints.length, selectedAreas.length]);

  // Update the useEffect hook that fetches metrics
  useEffect(() => {
    const fetchMetrics = async () => {
      if (!selectedSprints.length || !selectedAreas.length) {
        setMetrics(null);
        setHealthMetrics(null);
        return;
      }

      try {
        const queryParams = new URLSearchParams();
        selectedSprints.forEach(sprint => queryParams.append('selected_sprints[]', sprint));
        selectedAreas.forEach(area => queryParams.append('selected_areas[]', area));
        queryParams.append('time_frame', timeline.timeFramePercentage.toString());

        // Fetch health metrics for all selected sprints
        const response = await fetch(`${API_BASE_URL}/sprint-health?${queryParams}`);
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch sprint health');
        }

        const healthData = await response.json();

        // Validate the response structure
        if (!healthData || typeof healthData.health_score === 'undefined') {
          throw new Error('Invalid response format from server');
        }

        setHealthMetrics(healthData);
        
        // Also fetch and set regular metrics if needed
        const metricsResponse = await fetch(`${API_BASE_URL}/metrics?${queryParams}`);
        if (!metricsResponse.ok) {
          throw new Error('Failed to fetch metrics');
        }
        
        const metricsData = await metricsResponse.json();
        setMetrics(transformBackendMetrics(metricsData, sprintStartDate));

      } catch (err) {
        console.error('Error fetching data:', err);
        setError(err instanceof Error ? err.message : String(err));
        setHealthMetrics(null);
        setMetrics(null);
      }
    };

    fetchMetrics();
  }, [selectedSprints, selectedAreas, timeline.timeFramePercentage, sprintStartDate]);

  // Add helper function for aggregating multiple sprint metrics
  function aggregateMultipleSprintMetrics(metricsData: BackendMetrics, sprints: string[]): SprintMetrics {
    // If metricsData is already aggregated from backend, just transform it
    if (!Array.isArray(metricsData)) {
      return transformBackendMetrics(metricsData, '');
    }

    // If we have an array of metrics (one per sprint), aggregate them
    const aggregated = {
      todo: 0,
      in_progress: 0,
      done: 0,
      removed: 0,
      backlog_changes: 0,
      blocked_tasks: 0,
      health_score: 0,
      health_details: {
        delivery_score: 0,
        stability_score: 0,
        flow_score: 0,
        quality_score: 0,
        team_load_score: 0,
        completion_rate: 0,
        blocked_ratio: 0,
        last_day_completion: 0
      }
    };

    // Calculate averages
    metricsData.forEach((sprintMetrics: BackendMetrics) => {
      aggregated.todo += sprintMetrics.todo;
      aggregated.in_progress += sprintMetrics.in_progress;
      aggregated.done += sprintMetrics.done;
      aggregated.removed += sprintMetrics.removed;
      aggregated.backlog_changes += sprintMetrics.backlog_changes;
      aggregated.blocked_tasks += sprintMetrics.blocked_tasks;
      aggregated.health_score += sprintMetrics.health_score;

      // Aggregate health details
      Object.keys(aggregated.health_details).forEach(key => {
        aggregated.health_details[key as keyof typeof aggregated.health_details] += 
          sprintMetrics.health_details[key as keyof typeof sprintMetrics.health_details];
      });
    });

    // Calculate averages
    const count = metricsData.length;
    aggregated.health_score /= count;
    aggregated.backlog_changes /= count;
    
    Object.keys(aggregated.health_details).forEach(key => {
      aggregated.health_details[key as keyof typeof aggregated.health_details] /= count;
    });

    return {
      ...aggregated,
      todo_trend: 0,
      in_progress_trend: 0,
      done_trend: 0,
      removed_trend: 0,
      status_changes_uniformity: 0,
      daily_changes: [] // Could be aggregated if needed
    };
  }

  // Add helper function to compare arrays
  function arraysEqual<T>(a: T[], b: T[]): boolean {
    if (a.length !== b.length) return false;
    return a.every((val, index) => val === b[index]);
  }

  // Helper function for safe number formatting
  const formatNumber = (value: number | undefined): string => {
    return value?.toFixed(1) ?? '0.0';
  };

  // Helper function for color classes
  const getColorClass = (value: number | undefined, threshold: number, highThreshold?: number): string => {
    if (value === undefined) return '';
    if (highThreshold && value > highThreshold) return 'text-red-500';
    return value > threshold ? 'text-red-500' : 'text-green-500';
  };

  // Add new component for category scores
  function CategoryScores({ categories }: { categories: SprintHealthResponse['category_scores'] }) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {Object.entries(categories).map(([key, category]) => (
          <Card key={key}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                {formatCategoryName(key)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {category.score.toFixed(1)}
              </div>
              <Tooltip>
                <TooltipTrigger>
                  <p className="text-xs text-muted-foreground">
                    Вес: {category.weight}
                  </p>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{category.description}</p>
                </TooltipContent>
              </Tooltip>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  // Add new component for key metrics
  function KeyMetrics({ metrics }: { metrics: KeyMetricsData }) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Object.entries(metrics).map(([key, metric]) => (
          <Card key={key}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                {formatMetricName(key)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {metric.value.toFixed(1)}{metric.unit}
              </div>
              <Tooltip>
                <TooltipTrigger>
                  <Info className="h-4 w-4 text-muted-foreground" />
                </TooltipTrigger>
                <TooltipContent>
                  <p>{metric.description}</p>
                </TooltipContent>
              </Tooltip>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <TooltipProvider>
      <div className="container mx-auto p-4 space-y-6">
        {/* Header Section */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Панель здоровья спринта</h1>
            <p className="text-muted-foreground">
              Мониторинг и анализ метрик эффективности спринта
            </p>
          </div>
          
          {sprintPeriod && (
            <Badge variant="outline" className="text-lg">
              {sprintPeriod.type === 'sprint' 
                ? 'Анализ спринта' 
                : sprintPeriod.type === 'quarter'
                  ? 'Квартальный анализ'
                  : sprintPeriod.type === 'halfYear'
                    ? 'Полугодовой анализ'
                    : 'Годовой анализ'}
            </Badge>
          )}
        </div>

        {!metrics && (
          <Card className="mb-4">
            <CardHeader>
              <CardTitle>Загрузить данные спринта</CardTitle>
            </CardHeader>
            <CardContent>
              <FileUploadZone />
            </CardContent>
          </Card>
        )}

        {/* Main Tabs */}
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList>
            <TabsTrigger value="overview">Обзор</TabsTrigger>
            <TabsTrigger value="details">Детальный анализ</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            {/* Selection Controls */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Sprint Selection */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CalendarIcon />
                    Выбор спринта
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Select onValueChange={handleSprintSelection}>
                    <SelectTrigger>
                      <SelectValue placeholder="Выберите спринты..." />
                    </SelectTrigger>
                    <SelectContent>
                      {sprints.map((sprint) => (
                        <SelectItem key={sprint} value={sprint}>
                          {sprint}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <div className="flex flex-wrap gap-2 mt-4">
                    {selectedSprints.map(sprint => (
                      <motion.div
                        key={sprint}
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                      >
                        <Badge 
                          variant="secondary"
                          className="cursor-pointer hover:bg-secondary/80"
                          onClick={() => handleSprintSelection(sprint)}
                        >
                          {sprint} ×
                        </Badge>
                      </motion.div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Area Selection */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Layers />
                    Выбор области
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Select
                    onValueChange={(value) => {
                      setSelectedAreas(current => 
                        current.includes(value) 
                          ? current.filter(a => a !== value)
                          : [...current, value]
                      );
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Выберите области..." />
                    </SelectTrigger>
                    <SelectContent>
                      {areas.map((area) => (
                        <SelectItem key={area} value={area}>
                          {area}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <div className="flex flex-wrap gap-2 mt-4">
                    {selectedAreas.map(area => (
                      <motion.div
                        key={area}
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                      >
                        <Badge 
                          variant="outline"
                          className="cursor-pointer hover:bg-secondary/80"
                          onClick={() => setSelectedAreas(current => 
                            current.filter(a => a !== area)
                          )}
                        >
                          {area} ×
                        </Badge>
                      </motion.div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Add Timeline Component here, right after selection controls */}
            {metrics && sprintPeriod && (
              <SprintTimeline
                currentDay={timeline.currentDay}
                totalDays={timeline.totalDays}
                timeFramePercentage={timeline.timeFramePercentage}
                backlogChanges={metrics.backlog_changes}
                selectedSprints={selectedSprints}
                onTimelineChange={handleTimelineChange}
              />
            )}

            {/* Health Score Card */}
            {metrics && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <Card className="bg-gradient-to-br from-background to-secondary/10">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>Оценка здоровья спринта</span>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger>
                            <Info />
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Комплексная оценка здоровья спринта</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <HealthScoreSection healthMetrics={healthMetrics} />
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Key Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatusCard 
                title="К выполнению"
                value={metrics?.todo}
                icon={<ClipboardList />}
                trend={metrics?.todo_trend}
                timeframe={timeline.timeFramePercentage}
              />
              <StatusCard 
                title="В работе"
                value={metrics?.in_progress}
                icon={<Clock />}
                trend={metrics?.in_progress_trend}
                timeframe={timeline.timeFramePercentage}
              />
              <StatusCard 
                title="Завершено"
                value={metrics?.done}
                icon={<CheckCircle />}
                trend={metrics?.done_trend}
                timeframe={timeline.timeFramePercentage}
              />
              <StatusCard 
                title="Удалено"
                value={metrics?.removed}
                icon={<XCircle />}
                trend={metrics?.removed_trend}
                timeframe={timeline.timeFramePercentage}
              />
            </div>

            {/* Health Indicators Section */}
            {metrics && (
              <Card>
                <CardHeader>
                  <CardTitle>Индикаторы здоровья спринта</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <HealthIndicator 
                    value={(metrics.todo / (metrics.todo + metrics.in_progress + metrics.done)) * 100}
                    threshold={20}
                    label="Задачи к выполнению (долно быть <20%)"
                  />
                  <HealthIndicator 
                    value={(metrics.removed / (metrics.todo + metrics.in_progress + metrics.done + metrics.removed)) * 100}
                    threshold={10}
                    label="Удаленные задачи (должно быть <10%)"
                  />
                  <HealthIndicator 
                    value={metrics.backlog_changes}
                    threshold={20}
                    label="Изменения в бэклое (должно быть <20%)"
                  />
                  {metrics.status_changes_uniformity && (
                    <HealthIndicator 
                      value={metrics.status_changes_uniformity}
                      threshold={80}
                      label="Равномерность изменений статуса"
                    />
                  )}
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="details" className="space-y-4">
            <SprintCharts metrics={metrics} />
            
            {/* Blocked Tasks Analysis */}
            <Card>
              <CardHeader>
                <CardTitle>Анализ заблокированных задач</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span>Текущие заблокированные задачи</span>
                    <Badge variant={metrics?.blocked_tasks ? "destructive" : "success"}>
                      {metrics?.blocked_tasks || 0}
                    </Badge>
                  </div>
                  <Progress 
                    value={metrics?.blocked_tasks 
                      ? (metrics.blocked_tasks / (metrics.todo + metrics.in_progress)) * 100 
                      : 0
                    } 
                    className="h-2"
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </TooltipProvider>
  );
}

function StatusCard({ title, value, icon, trend, timeframe }: {
  title: string;
  value?: number;
  icon: React.ReactNode;
  trend?: number;
  timeframe?: number;
}) {
  // Calculate the value based on timeframe percentage
  const adjustedValue = useMemo(() => {
    if (value === undefined || timeframe === undefined) return value;
    return value * (timeframe / 100);
  }, [value, timeframe]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">
          {title}
        </CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">
          {adjustedValue?.toFixed(1) ?? <div className="h-6 w-12 bg-gray-200 animate-pulse rounded" />}
        </div>
        {trend !== undefined && (
          <p className={cn(
            "text-xs",
            trend > 0 ? "text-green-500" : 
            trend < 0 ? "text-red-500" : 
            "text-muted-foreground"
          )}>
            {trend > 0 ? "+" : ""}{trend}% from last period
          </p>
        )}
      </CardContent>
    </Card>
  );
}