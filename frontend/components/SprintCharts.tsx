import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip as RechartsTooltip,
  LineChart, 
  Line, 
  AreaChart, 
  Area,
  ResponsiveContainer,
  TooltipProps
} from 'recharts';

type ChartTooltipProps = {
  active?: boolean;
  payload?: Array<{
    value: number | undefined;
    name: string;
    color: string;
    dataKey: string;
    payload: {
      [key: string]: number;
    };
  }>;
  label?: string | number;
}

type ChartProps = {
  metrics: {
    todo?: number;
    in_progress?: number;
    done?: number;
    removed?: number;
    blocked_tasks?: number;
    daily_changes?: Array<{
      day: number;
      added: number;
      removed: number;
      done?: number;
      in_progress?: number;
    }>;
  } | null;
}

export function SprintCharts({ metrics }: ChartProps) {
  if (!metrics) return null;

  const renderTooltip = ({ active, payload, label }: TooltipProps<number, string>) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-2 border rounded shadow-lg">
          <p className="font-bold">{label}</p>
          {payload.map((entry) => (
            <p key={entry.dataKey}>
              {entry.name}: {entry.value}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
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
              <RechartsTooltip content={renderTooltip} />
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
              <RechartsTooltip content={renderTooltip} />
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
              <RechartsTooltip content={renderTooltip} />
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

      {/* Daily Task Changes Chart */}
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
              <RechartsTooltip content={renderTooltip} />
              <Bar dataKey="added" fill="#4CAF50" name="Added Tasks" />
              <Bar dataKey="removed" fill="#f44336" name="Removed Tasks" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
} 