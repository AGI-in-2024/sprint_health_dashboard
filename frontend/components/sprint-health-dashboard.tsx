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
  excluded_tasks: Record<string, { hours: number; count: number }>;
  added_tasks: Record<string, { hours: number; count: number }>;
  sprint_start_date?: string;
  status_distribution?: {
    todo: number;
    in_progress: number;
    done: number;
    removed: number;
  };
  daily_metrics?: Array<{
    date: string;
    added_tasks: number;
    removed_tasks: number;
    blocked_tasks: number;
  }>;
  status_transitions?: {
    last_day_completion_percentage: number;
    daily_distribution: Record<string, any>;
    transition_evenness: number;
  };
  health_details: HealthDetails;
  health_metrics: HealthMetricsSnapshot;
  category_scores?: SprintHealthResponse['category_scores'];
  key_metrics?: SprintHealthResponse['key_metrics'];
}

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
    ? data.daily_metrics.map(metric => {
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

type SprintHealthResponse = {
  health_score: number;
  details: HealthDetails;
  metrics_snapshot: HealthMetricsSnapshot;
  category_scores: {
    delivery: CategoryScore;
    stability: CategoryScore;
    flow: CategoryScore;
    quality: CategoryScore;
    team_load: CategoryScore;
  };
  key_metrics: {
    completion_rate: KeyMetric;
    scope_changes: KeyMetric;
    blocked_tasks: KeyMetric;
    rework: KeyMetric;
    tech_debt: KeyMetric;
    flow_evenness: KeyMetric;
    last_day_completion: KeyMetric;
  };
}

// Simplify the health score section component
function HealthScoreSection({ metrics }: { metrics: SprintMetrics }) {
  if (!metrics) return null;

  const scores = [
    { name: 'Доставка', score: metrics.health_details.delivery_score, weight: '25%' },
    { name: 'Стабильность', score: metrics.health_details.stability_score, weight: '20%' },
    { name: 'Поток', score: metrics.health_details.flow_score, weight: '20%' },
    { name: 'Качество', score: metrics.health_details.quality_score, weight: '20%' },
    { name: 'Нагрузка', score: metrics.health_details.team_load_score, weight: '15%' }
  ];

  const keyMetrics = [
    { name: 'Завершение', value: metrics.health_details.completion_rate, unit: '%' },
    { name: 'Блокировки', value: metrics.health_details.blocked_ratio, unit: '%' },
    { name: 'Последний день', value: metrics.health_details.last_day_completion, unit: '%' }
  ];

  return (
    <div className="space-y-6">
      {/* Health Score */}
      <div className="flex items-center justify-between">
        <span className="text-4xl font-bold">
          {metrics.health_score.toFixed(1)}%
        </span>
        <Badge variant={
          metrics.health_score >= 80 ? "success" :
          metrics.health_score >= 60 ? "warning" : "destructive"
        }>
          {metrics.health_score >= 80 ? "Здоровый" :
           metrics.health_score >= 60 ? "Требует внимания" : "Критический"}
        </Badge>
      </div>

      {/* Category Scores */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {scores.map(({ name, score, weight }) => (
          <Card key={name}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">{name}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{score.toFixed(1)}</div>
              <p className="text-xs text-muted-foreground">Вес: {weight}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {keyMetrics.map(({ name, value, unit }) => (
          <div key={name} className="flex justify-between items-center p-2 border rounded">
            <span>{name}</span>
            <Badge variant={value > 80 ? "success" : "warning"}>
              {value.toFixed(1)}{unit}
            </Badge>
          </div>
        ))}
      </div>
    </div>
  );
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

  // Update the fetchMetrics function to also fetch health metrics
  useEffect(() => {
    const fetchMetrics = async () => {
      if (!selectedSprints.length || !selectedAreas.length) {
        setMetrics(null);
        setHealthMetrics(null);
        return;
      }
      
      const currentSprints = [...selectedSprints];
      const currentAreas = [...selectedAreas];
      
      try {
        const queryParams = new URLSearchParams();
        currentSprints.forEach(sprint => {
          queryParams.append('selected_sprints[]', sprint);
        });
        
        currentAreas.forEach(area => {
          queryParams.append('selected_areas[]', area);
        });
        
        queryParams.append('time_frame', timeline.timeFramePercentage.toString());
        
        // Fetch both metrics and health metrics in parallel
        const [metricsResponse, healthResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/metrics?${queryParams}`),
          fetch(`${API_BASE_URL}/sprint-health?${queryParams}`)
        ]);
        
        if (!arraysEqual(currentSprints, selectedSprints) || 
            !arraysEqual(currentAreas, selectedAreas)) {
          return;
        }
        
        if (!metricsResponse.ok || !healthResponse.ok) {
          const errorData = await (metricsResponse.ok ? healthResponse : metricsResponse).json();
          throw new Error(errorData.detail || 'Failed to fetch data');
        }
        
        const [metricsData, healthData] = await Promise.all([
          metricsResponse.json(),
          healthResponse.json()
        ]);
        
        if (!isValidBackendMetrics(metricsData)) {
          throw new Error('Invalid metrics data received from server');
        }
        
        const transformedMetrics = transformBackendMetrics(metricsData, sprintStartDate);
        setMetrics(transformedMetrics);
        setHealthMetrics(healthData);
        setError(null);
        
      } catch (err) {
        console.error('Error fetching data:', err);
        setError(err instanceof Error ? err.message : String(err));
        setMetrics(null);
        setHealthMetrics(null);
      }
    };
    
    fetchMetrics();
  }, [selectedSprints, selectedAreas, timeline.timeFramePercentage, sprintStartDate]);

  // Helper function for array comparison
  const arraysEqual = (a: string[], b: string[]) => {
    if (a.length !== b.length) return false;
    return a.every((val, index) => val === b[index]);
  };

  // Helper function to determine sprint period
  const calculateSprintPeriod = useCallback((selectedSprints: string[]) => {
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
      
      // Update sprint period
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
      }

      return newSelection;
    });
  }, [calculateSprintPeriod]);

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
  function KeyMetrics({ metrics }: { metrics: SprintHealthResponse['key_metrics'] }) {
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

  // Add helper function for formatting names
  function formatCategoryName(key: string): string {
    const names: Record<string, string> = {
      delivery: 'Доставка',
      stability: 'Стабильность',
      flow: 'Поток',
      quality: 'Качество',
      team_load: 'Нагрузка'
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
      last_day_completion: 'Последний день'
    };
    return names[key] || key;
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
                    <HealthScoreSection metrics={metrics} />
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
                    label="Задачи к выполнению (должно быть <20%)"
                  />
                  <HealthIndicator 
                    value={(metrics.removed / (metrics.todo + metrics.in_progress + metrics.done + metrics.removed)) * 100}
                    threshold={10}
                    label="Удаленные задачи (должно быть <10%)"
                  />
                  <HealthIndicator 
                    value={metrics.backlog_changes}
                    threshold={20}
                    label="Изменения в бэклоге (должно быть <20%)"
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