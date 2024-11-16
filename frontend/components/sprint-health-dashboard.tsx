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
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { AlertCircle, FileUp } from 'lucide-react'
import { Progress } from "@/components/ui/progress"

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
}

// Add transformation function
function transformBackendMetrics(data: BackendMetrics): SprintMetrics {
  // Transform daily changes
  const allDates = new Set([
    ...Object.keys(data.excluded_tasks),
    ...Object.keys(data.added_tasks)
  ]);

  const daily_changes = Array.from(allDates).map(dateStr => {
    const added = data.added_tasks[dateStr]?.count || 0;
    const removed = -(data.excluded_tasks[dateStr]?.count || 0);
    
    // Convert date string to day number (assuming ISO date string)
    const date = new Date(dateStr);
    const startDate = new Date(dateStr); // You might need to get this from sprint info
    const day = Math.floor((date.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)) + 1;

    return {
      day,
      added,
      removed
    };
  }).sort((a, b) => a.day - b.day);

  return {
    todo: data.todo,
    in_progress: data.in_progress,
    done: data.done,
    removed: data.removed,
    backlog_changes: data.backlog_changes,
    health_percentage: data.health_score,
    blocked_tasks: data.blocked_tasks,
    daily_changes
  };
}

// Update type validation
function isValidBackendMetrics(data: any): data is BackendMetrics {
  return (
    typeof data === 'object' &&
    data !== null &&
    typeof data.todo === 'number' &&
    typeof data.in_progress === 'number' &&
    typeof data.done === 'number' &&
    typeof data.removed === 'number' &&
    typeof data.backlog_changes === 'number' &&
    typeof data.health_score === 'number' &&
    typeof data.blocked_tasks === 'number' &&
    typeof data.excluded_tasks === 'object' &&
    typeof data.added_tasks === 'object'
  );
}

export function SprintHealthDashboardComponent() {
  // State
  const [sprints, setSprints] = useState<string[]>([]);
  const [teams, setTeams] = useState<string[]>([]);
  const [selectedSprints, setSelectedSprints] = useState<string[]>([]);
  const [selectedTeams, setSelectedTeams] = useState<string[]>([]);
  const [timeFrame, setTimeFrame] = useState<number>(100);
  const [metrics, setMetrics] = useState<SprintMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch available sprints and teams
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [sprintsRes, teamsRes] = await Promise.all([
          fetch(`${API_BASE_URL}/sprints`),
          fetch(`${API_BASE_URL}/teams`)
        ]);
        
        const sprintsData = await sprintsRes.json();
        const teamsData = await teamsRes.json();
        
        setSprints(sprintsData.sprints);
        setTeams(teamsData.teams);
      } catch (err) {
        setError('Failed to load sprints and teams data');
      }
    };
    
    fetchData();
  }, []);

  // Fetch metrics when selection changes
  useEffect(() => {
    const fetchMetrics = async () => {
      if (!selectedSprints.length || !selectedTeams.length) return;
      
      try {
        const queryParams = new URLSearchParams();
        selectedSprints.forEach(sprint => {
          queryParams.append('selected_sprints[]', sprint);
        });
        
        selectedTeams.forEach(team => {
          queryParams.append('selected_teams[]', team);
        });
        
        queryParams.append('time_frame', timeFrame.toString());
        
        const response = await fetch(`${API_BASE_URL}/metrics?${queryParams}`);
        const data = await response.json();
        
        if (!response.ok) {
          throw new Error(data.detail || 'Failed to fetch metrics');
        }
        
        // Validate backend response
        if (!isValidBackendMetrics(data)) {
          throw new Error('Invalid metrics data received from server');
        }
        
        // Transform data to match frontend structure
        const transformedMetrics = transformBackendMetrics(data);
        setMetrics(transformedMetrics);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch metrics');
        setMetrics(null);
      }
    };
    
    fetchMetrics();
  }, [selectedSprints, selectedTeams, timeFrame]);

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
    <div className="container mx-auto p-4">
      {/* Sprint and Team Selection */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        {/* Sprint Selection */}
        <div className="space-y-2">
          <Label>Sprints</Label>
          <Select 
            onValueChange={(value) => {
              setSelectedSprints(current => 
                current.includes(value) 
                  ? current.filter(s => s !== value)
                  : [...current, value]
              );
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder={
                selectedSprints.length === 0 
                  ? "Select sprints..." 
                  : `${selectedSprints.length} sprints selected`
              } />
            </SelectTrigger>
            <SelectContent>
              {sprints.map((sprint) => (
                <SelectItem 
                  key={sprint} 
                  value={sprint}
                >
                  {sprint}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {/* Selected Sprints Display */}
          <div className="flex flex-wrap gap-2 mt-2">
            {selectedSprints.map(sprint => (
              <Button
                key={sprint}
                variant="secondary"
                size="sm"
                onClick={() => setSelectedSprints(current => 
                  current.filter(s => s !== sprint)
                )}
              >
                {sprint} ×
              </Button>
            ))}
          </div>
        </div>

        {/* Team Selection */}
        <div className="space-y-2">
          <Label>Teams</Label>
          <Select
            onValueChange={(value) => {
              setSelectedTeams(current => 
                current.includes(value) 
                  ? current.filter(t => t !== value)
                  : [...current, value]
              );
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder={
                selectedTeams.length === 0 
                  ? "Select teams..." 
                  : `${selectedTeams.length} teams selected`
              } />
            </SelectTrigger>
            <SelectContent>
              {teams.map((team) => (
                <SelectItem 
                  key={team} 
                  value={team}
                >
                  {team}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {/* Selected Teams Display */}
          <div className="flex flex-wrap gap-2 mt-2">
            {selectedTeams.map(team => (
              <Button
                key={team}
                variant="secondary"
                size="sm"
                onClick={() => setSelectedTeams(current => 
                  current.filter(t => t !== team)
                )}
              >
                {team} ×
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Timeline Control */}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <Slider
            defaultValue={[100]}
            max={100}
            step={1}
            onValueChange={(value) => setTimeFrame(value[0])}
          />
        </CardContent>
      </Card>

      {/* Error Display */}
      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Sprint Health Progress */}
      {metrics && (
        <Card className="mb-4">
          <CardHeader>
            <CardTitle>Здоровье спринта</CardTitle>
          </CardHeader>
          <CardContent>
            <Progress 
              value={metrics.health_percentage ?? 0} 
              className="h-4 bg-gray-200"
            />
            <div className="mt-2 text-sm text-gray-600">
              Оценка Ч/Д
            </div>
          </CardContent>
        </Card>
      )}

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <Card>
          <CardHeader>
            <CardTitle>Бэклог изменен с начала спринта на</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-2xl font-bold ${
              metrics?.backlog_changes !== undefined
                ? metrics.backlog_changes > 50
                  ? 'text-red-500'
                  : metrics.backlog_changes > 20
                    ? 'text-yellow-500'
                    : 'text-green-500'
                : ''
            }`}>
              {formatNumber(metrics?.backlog_changes)}%
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Заблокировано задач в Ч/Д</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {formatNumber(metrics?.blocked_tasks)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Daily Changes Table */}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Изменения по дням</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>День</TableHead>
                <TableHead>+/- (Ч/Д)</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {metrics?.daily_changes?.map((change) => (
                <TableRow key={change.day}>
                  <TableCell>{change.day}</TableCell>
                  <TableCell>
                    {change.added > 0 && `+${change.added}`}
                    {change.removed < 0 && ` ${change.removed}`}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Status Distribution */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>К выполнению</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-2xl font-bold ${getColorClass(metrics?.todo, 20)}`}>
              {formatNumber(metrics?.todo)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>В работе</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {formatNumber(metrics?.in_progress)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Сделано</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {formatNumber(metrics?.done)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Снято</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-2xl font-bold ${getColorClass(metrics?.removed, 10)}`}>
              {formatNumber(metrics?.removed)}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}