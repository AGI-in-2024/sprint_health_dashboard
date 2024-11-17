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

// Update the types to match the actual data structure
type SprintMetrics = {
  todo: number;
  in_progress: number;
  done: number;
  removed: number;
  blocked_tasks: number;
  daily_changes: Array<{
    day: number;
    added: number;
    removed: number;
  }>;
  health_percentage: number;
}

type ChartProps = {
  metrics: SprintMetrics | null;
}

const CustomTooltip = ({ active, payload, label }: TooltipProps<number, string>) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-background border rounded-lg shadow-lg p-3">
        <p className="font-semibold">{`Day ${label}`}</p>
        {payload.map((entry, index) => (
          <p key={index} style={{ color: entry.color }}>
            {`${entry.name}: ${entry.value}`}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export function SprintCharts({ metrics }: ChartProps) {
  if (!metrics) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>No data available</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">Please select a sprint to view metrics</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Transform data for the task distribution chart
  const distributionData = [
    { name: 'To Do', value: metrics.todo },
    { name: 'In Progress', value: metrics.in_progress },
    { name: 'Done', value: metrics.done },
    { name: 'Removed', value: metrics.removed }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Task Distribution Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Task Distribution</CardTitle>
        </CardHeader>
        <CardContent className="min-h-[400px] w-full">
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={distributionData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <RechartsTooltip content={CustomTooltip} />
              <Bar dataKey="value" fill="#8884d8" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Daily Changes Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Daily Task Changes</CardTitle>
        </CardHeader>
        <CardContent className="min-h-[400px] w-full">
          <ResponsiveContainer width="100%" height={350}>
            <LineChart 
              data={metrics.daily_changes}
              margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis />
              <RechartsTooltip content={CustomTooltip} />
              <Line 
                type="monotone" 
                dataKey="added" 
                stroke="#4CAF50" 
                name="Added Tasks"
                dot={false}
              />
              <Line 
                type="monotone" 
                dataKey="removed" 
                stroke="#f44336" 
                name="Removed Tasks"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Velocity Trend */}
      <Card>
        <CardHeader>
          <CardTitle>Task Completion Trend</CardTitle>
        </CardHeader>
        <CardContent className="min-h-[400px] w-full">
          <ResponsiveContainer width="100%" height={350}>
            <AreaChart 
              data={metrics.daily_changes}
              margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis />
              <RechartsTooltip content={CustomTooltip} />
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

      {/* Task Status Changes */}
      <Card>
        <CardHeader>
          <CardTitle>Task Status Distribution</CardTitle>
        </CardHeader>
        <CardContent className="min-h-[400px] w-full">
          <ResponsiveContainer width="100%" height={350}>
            <BarChart 
              data={metrics.daily_changes}
              margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis />
              <RechartsTooltip content={CustomTooltip} />
              <Bar dataKey="added" stackId="a" fill="#4CAF50" name="Added" />
              <Bar dataKey="removed" stackId="a" fill="#f44336" name="Removed" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
} 