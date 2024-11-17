import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ResponsiveContainer,
  LineChart,
  BarChart,
  AreaChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  Line,
  Bar,
  Area,
} from 'recharts';
import { CustomTooltip } from "@/components/CustomTooltip"; // Ensure this path is correct
import { cn } from "@/lib/utils";

// Define the props type
type SprintMetrics = {
  todo: number;
  in_progress: number;
  done: number;
  removed: number;
  backlog_changes: number;
  health_percentage: number;
  blocked_tasks: number;
  daily_changes: DailyChanges[];
};

type DailyChanges = {
  day: number;
  added: number;
  removed: number;
};

type SprintChartsProps = {
  metrics: SprintMetrics;
};

export const SprintCharts: React.FC<SprintChartsProps> = ({ metrics }) => {
  return (
    <>
      {/* Burndown Chart */}
      <Card className="mb-4 shadow-lg rounded-lg">
        <CardHeader>
          <CardTitle>Burndown Chart</CardTitle>
        </CardHeader>
        <CardContent className="min-h-[400px]">
          <ResponsiveContainer width="100%" height={350}>
            <LineChart
              data={metrics.daily_changes}
              margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" label={{ value: 'Day', position: 'insideBottomRight', offset: 0 }} />
              <YAxis label={{ value: 'Hours', angle: -90, position: 'insideLeft' }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Line type="monotone" dataKey="added" stroke="#8884d8" name="Added" />
              <Line type="monotone" dataKey="removed" stroke="#82ca9d" name="Removed" />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Velocity Chart */}
      <Card className="mb-4 shadow-lg rounded-lg">
        <CardHeader>
          <CardTitle>Velocity Chart</CardTitle>
        </CardHeader>
        <CardContent className="min-h-[400px]">
          <ResponsiveContainer width="100%" height={350}>
            <BarChart
              data={metrics.daily_changes}
              margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" label={{ value: 'Day', position: 'insideBottomRight', offset: 0 }} />
              <YAxis label={{ value: 'Hours', angle: -90, position: 'insideLeft' }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Bar dataKey="added" fill="#8884d8" name="Added" />
              <Bar dataKey="removed" fill="#82ca9d" name="Removed" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Cumulative Flow Diagram */}
      <Card className="mb-4 shadow-lg rounded-lg">
        <CardHeader>
          <CardTitle>Cumulative Flow Diagram</CardTitle>
        </CardHeader>
        <CardContent className="min-h-[400px]">
          <ResponsiveContainer width="100%" height={350}>
            <AreaChart
              data={metrics.daily_changes}
              margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
            >
              <defs>
                <linearGradient id="colorAdded" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#8884d8" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorRemoved" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#82ca9d" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#82ca9d" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" label={{ value: 'Day', position: 'insideBottomRight', offset: 0 }} />
              <YAxis label={{ value: 'Hours', angle: -90, position: 'insideLeft' }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Area
                type="monotone"
                dataKey="added"
                stroke="#8884d8"
                fillOpacity={1}
                fill="url(#colorAdded)"
                name="Added"
              />
              <Area
                type="monotone"
                dataKey="removed"
                stroke="#82ca9d"
                fillOpacity={1}
                fill="url(#colorRemoved)"
                name="Removed"
              />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </>
  );
}; 