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
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend, ResponsiveContainer, LineChart, Line, AreaChart, Area } from 'recharts'
import { AlertCircle, FileUp, Calendar as CalendarIcon, Layers, Info, ClipboardList, Clock, CheckCircle, XCircle } from 'lucide-react'
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"
import { SprintCharts } from "@/components/SprintCharts"
import { SprintTimeline } from "@/components/sprint-timeline"
import { motion } from "framer-motion"
import { format } from "date-fns"
import { ru } from "date-fns/locale"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useDropzone } from 'react-dropzone';

// Import CustomTooltip as ChartTooltip to avoid naming conflict
import { CustomTooltip as ChartTooltip } from './CustomTooltip'

// API integration
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api';

// Types
type Metrics = {
  todo: number;
  in_progress: number;
  done: number;
  removed: number;
  backlog_changes: number;
}

type DailyChanges = {
  day: number;
  added: number;
  removed: number;
}

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
  status_changes_uniformity?: number;
}

type SprintMetrics = {
  todo: number;
  in_progress: number;
  done: number;
  removed: number;
  backlog_changes: number;
  health_percentage: number;
  blocked_tasks: number;
  daily_changes: DailyChanges[];
  todo_trend?: number;
  in_progress_trend?: number;
  done_trend?: number;
  removed_trend?: number;
  status_changes_uniformity?: number;
}

// Add transformation function
function transformBackendMetrics(data: BackendMetrics, sprintStartDate: string): SprintMetrics {
  // Use daily_metrics if available, otherwise fallback to current logic
  const daily_changes = data.daily_metrics 
    ? data.daily_metrics.map(metric => {
        const date = new Date(metric.date);
        const sprintStart = new Date(sprintStartDate);
        const day = Math.floor((date.getTime() - sprintStart.getTime()) / (1000 * 60 * 60 * 24)) + 1;
        
        return {
          day,
          added: metric.added_tasks,
          removed: -metric.removed_tasks // Keep negative for removed tasks
        };
      })
    : transformLegacyDailyChanges(data, sprintStartDate);

  return {
    todo: data.status_distribution?.todo ?? data.todo,
    in_progress: data.status_distribution?.in_progress ?? data.in_progress,
    done: data.status_distribution?.done ?? data.done,
    removed: data.status_distribution?.removed ?? data.removed,
    backlog_changes: data.backlog_changes,
    health_percentage: data.health_score,
    blocked_tasks: data.blocked_tasks,
    daily_changes
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
        <p>Drop the files here ...</p>
      ) : (
        <p>Drag 'n' drop files here, or click to select files</p>
      )}
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
    totalDays: 0,
    timeFramePercentage: 100
  });

  // Add new state for sprint period
  const [sprintPeriod, setSprintPeriod] = useState<SprintPeriod | null>(null);

  // Fetch available sprints and areas
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [sprintsRes, areasRes] = await Promise.all([
          fetch(`${API_BASE_URL}/sprints`),
          fetch(`${API_BASE_URL}/areas`)
        ]);
        
        const sprintsData = await sprintsRes.json();
        const areasData = await areasRes.json();
        
        setSprints(sprintsData.sprints);
        setAreas(areasData.areas);
      } catch (err) {
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

  // Fetch metrics when selection changes
  useEffect(() => {
    const fetchMetrics = async () => {
      if (!selectedSprints.length || !selectedAreas.length) return;
      
      try {
        const queryParams = new URLSearchParams();
        selectedSprints.forEach(sprint => {
          queryParams.append('selected_sprints[]', sprint);
        });
        
        selectedAreas.forEach(area => {
          queryParams.append('selected_areas[]', area);
        });
        
        // Ensure we always send a valid number between 0 and 100
        const safeTimeFrame = isNaN(timeline.timeFramePercentage) ? 
          100 : 
          Math.min(100, Math.max(0, timeline.timeFramePercentage));
        
        queryParams.append('time_frame', safeTimeFrame.toString());
        
        console.debug('Fetching metrics with params:', queryParams.toString());
        
        const response = await fetch(`${API_BASE_URL}/metrics?${queryParams}`);
        const data = await response.json();
        
        if (!response.ok) {
          throw new Error(data.detail || 'Failed to fetch metrics');
        }
        
        // Validate backend response
        if (!isValidBackendMetrics(data)) {
          throw new Error('Invalid metrics data received from server');
        }
        
        const transformedMetrics = transformBackendMetrics(data, sprintStartDate);
        setMetrics(transformedMetrics);
        setError(null);
        
      } catch (err) {
        console.error('Error fetching metrics:', err);
        setError(err instanceof Error ? err.message : String(err));
        setMetrics(null);
      }
    };
    
    fetchMetrics();
  }, [selectedSprints, selectedAreas, timeFrame, timeline]);

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

      // Update timeline based on period
      if (period) {
        const totalDays = Math.ceil((period.endDate.getTime() - period.startDate.getTime()) 
          / (1000 * 60 * 60 * 24));
        
        setTimeline({
          currentDay: totalDays,
          totalDays,
          timeFramePercentage: 100
        });

        // Set sprint start date for single sprint view
        if (newSelection.length === 1) {
          setSprintStartDate(period.startDate.toISOString());
        }
      } else {
        // Reset timeline when no sprints selected
        setTimeline({
          currentDay: 0,
          totalDays: 14,
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

  return (
    <div className="container mx-auto p-4 space-y-6">
      {/* Header Section */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Sprint Health Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor and analyze sprint performance metrics
          </p>
        </div>
        
        {sprintPeriod && (
          <Badge variant="outline" className="text-lg">
            {sprintPeriod.type === 'sprint' 
              ? 'Sprint Analysis' 
              : sprintPeriod.type === 'quarter'
                ? 'Quarterly Analysis'
                : sprintPeriod.type === 'halfYear'
                  ? 'Half-Year Analysis'
                  : 'Yearly Analysis'}
          </Badge>
        )}
      </div>

      {!metrics && (
        <Card className="mb-4">
          <CardHeader>
            <CardTitle>Upload Sprint Data</CardTitle>
          </CardHeader>
          <CardContent>
            <FileUploadZone />
          </CardContent>
        </Card>
      )}

      {/* Main Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="details">Detailed Analysis</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {/* Selection Controls */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Sprint Selection */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CalendarIcon className="h-4 w-4" />
                  Sprint Selection
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Select onValueChange={handleSprintSelection}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select sprints..." />
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
                  <Layers className="h-4 w-4" />
                  Area Selection
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
                    <SelectValue placeholder="Select areas..." />
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

          {/* Health Score and Timeline Row */}
          {metrics && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Health Score Card */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <Card className="bg-gradient-to-br from-background to-secondary/10">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>Sprint Health Score</span>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger>
                            <Info className="h-4 w-4" />
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Overall health score based on multiple metrics</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-4xl font-bold">
                          {metrics.health_percentage.toFixed(1)}%
                        </span>
                        <Badge variant={
                          metrics.health_percentage >= 80 ? "success" :
                          metrics.health_percentage >= 50 ? "warning" : "destructive"
                        }>
                          {metrics.health_percentage >= 80 ? "Healthy" :
                           metrics.health_percentage >= 50 ? "At Risk" : "Critical"}
                        </Badge>
                      </div>
                      
                      <Progress 
                        value={metrics.health_percentage} 
                        className={cn(
                          "h-2",
                          metrics.health_percentage >= 80 ? "bg-green-500" :
                          metrics.health_percentage >= 50 ? "bg-yellow-500" : "bg-red-500"
                        )}
                      />
                      
                      <p className="text-sm text-muted-foreground">
                        {metrics.health_percentage >= 80 ? 
                          'Sprint is progressing well with minimal issues.' :
                          metrics.health_percentage >= 50 ?
                            'Some attention required to keep sprint on track.' :
                            'Critical issues detected. Immediate action needed.'}
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {/* Timeline Component */}
                <SprintTimeline
                  currentDay={timeline.currentDay}
                  totalDays={timeline.totalDays}
                  dailyChanges={metrics.daily_changes || []}
                />
              </motion.div>
            </div>
          )}

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatusCard 
              title="To Do"
              value={metrics?.todo}
              icon={<ClipboardList className="h-4 w-4" />}
              trend={metrics?.todo_trend}
            />
            <StatusCard 
              title="In Progress"
              value={metrics?.in_progress}
              icon={<Clock className="h-4 w-4" />}
              trend={metrics?.in_progress_trend}
            />
            <StatusCard 
              title="Done"
              value={metrics?.done}
              icon={<CheckCircle className="h-4 w-4" />}
              trend={metrics?.done_trend}
            />
            <StatusCard 
              title="Removed"
              value={metrics?.removed}
              icon={<XCircle className="h-4 w-4" />}
              trend={metrics?.removed_trend}
            />
          </div>

          {/* Add Health Indicators Section */}
          {metrics && (
            <Card>
              <CardHeader>
                <CardTitle>Sprint Health Indicators</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <HealthIndicator 
                  value={(metrics.todo / (metrics.todo + metrics.in_progress + metrics.done)) * 100}
                  threshold={20}
                  label="To Do Tasks (should be <20%)"
                />
                <HealthIndicator 
                  value={(metrics.removed / (metrics.todo + metrics.in_progress + metrics.done + metrics.removed)) * 100}
                  threshold={10}
                  label="Removed Tasks (should be <10%)"
                />
                <HealthIndicator 
                  value={metrics.backlog_changes}
                  threshold={20}
                  label="Backlog Changes (should be <20%)"
                />
                {metrics.status_changes_uniformity && (
                  <HealthIndicator 
                    value={metrics.status_changes_uniformity}
                    threshold={80}
                    label="Status Changes Uniformity"
                  />
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="details" className="space-y-4">
          {/* Detailed Analysis Content */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Task Distribution Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Task Distribution</CardTitle>
              </CardHeader>
              <CardContent className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={[
                    { name: 'To Do', value: metrics?.todo || 0 },
                    { name: 'In Progress', value: metrics?.in_progress || 0 },
                    { name: 'Done', value: metrics?.done || 0 },
                    { name: 'Removed', value: metrics?.removed || 0 }
                  ]}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-white p-2 border rounded shadow-lg">
                            <p className="font-bold">{label}</p>
                            <p>{`Value: ${payload[0].value}`}</p>
                          </div>
                        );
                      }
                      return null;
                    }} />
                    <Bar dataKey="value" fill="#8884d8" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Backlog Changes Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Backlog Changes Over Time</CardTitle>
              </CardHeader>
              <CardContent className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={metrics?.daily_changes || []}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="day" />
                    <YAxis />
                    <Tooltip content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-white p-2 border rounded shadow-lg">
                            <p className="font-bold">Day {label}</p>
                            {payload.map((entry, index) => (
                              <p key={index} style={{ color: entry.color }}>
                                {entry.name}: {entry.value}
                              </p>
                            ))}
                          </div>
                        );
                      }
                      return null;
                    }} />
                    <Line type="monotone" dataKey="added" stroke="#4CAF50" name="Added" />
                    <Line type="monotone" dataKey="removed" stroke="#f44336" name="Removed" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Velocity Trend */}
            <Card>
              <CardHeader>
                <CardTitle>Velocity Trend</CardTitle>
              </CardHeader>
              <CardContent className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={metrics?.daily_changes || []}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="day" />
                    <YAxis />
                    <Tooltip content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-white p-2 border rounded shadow-lg">
                            <p className="font-bold">Day {label}</p>
                            <p>{`Completed Tasks: ${payload[0]?.value || 0}`}</p>
                          </div>
                        );
                      }
                      return null;
                    }} />
                    <Area 
                      type="monotone" 
                      dataKey="done" 
                      stroke="#2196F3" 
                      fill="#2196F3" 
                      fillOpacity={0.3}
                      name="Completed Tasks"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Blocked Tasks Analysis */}
            <Card>
              <CardHeader>
                <CardTitle>Blocked Tasks Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span>Currently Blocked Tasks</span>
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

            {/* Add Task Changes Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Daily Task Changes</CardTitle>
              </CardHeader>
              <CardContent className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={metrics?.daily_changes || []}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="day" />
                    <YAxis />
                    <Tooltip content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-white p-2 border rounded shadow-lg">
                            <p className="font-bold">Day {label}</p>
                            <p className="text-green-500">Added: {payload[0].value} tasks</p>
                            <p className="text-red-500">Removed: {Math.abs(payload[1].value)} tasks</p>
                          </div>
                        );
                      }
                      return null;
                    }} />
                    <Bar dataKey="added" fill="#4CAF50" name="Added Tasks" />
                    <Bar dataKey="removed" fill="#f44336" name="Removed Tasks" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="timeline" className="space-y-4">
          {/* Timeline Content */}
          <Card>
            <CardHeader>
              <CardTitle>Sprint Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-8">
                {/* Sprint Progress */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">Sprint Progress</span>
                    <span className="text-sm text-muted-foreground">
                      Day {timeline.currentDay} of {timeline.totalDays}
                    </span>
                  </div>
                  <Progress 
                    value={(timeline.currentDay / timeline.totalDays) * 100} 
                    className="h-2"
                  />
                </div>

                {/* Timeline Events */}
                <div className="space-y-4">
                  {metrics?.daily_changes?.map((change, index) => (
                    <div key={index} className="flex items-start space-x-4">
                      <div className="min-w-[100px] text-sm text-muted-foreground">
                        Day {change.day}
                      </div>
                      <div>
                        {change.added > 0 && (
                          <div className="flex items-center text-green-500">
                            <FileUp className="h-4 w-4 mr-2" />
                            Added {change.added} tasks
                          </div>
                        )}
                        {change.removed < 0 && (
                          <div className="flex items-center text-red-500">
                            <XCircle className="h-4 w-4 mr-2" />
                            Removed {Math.abs(change.removed)} tasks
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function StatusCard({ title, value, icon, trend }: {
  title: string;
  value?: number;
  icon: React.ReactNode;
  trend?: number;
}) {
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
          {value?.toFixed(1) ?? <div className="h-6 w-12 bg-gray-200 animate-pulse rounded" />}
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