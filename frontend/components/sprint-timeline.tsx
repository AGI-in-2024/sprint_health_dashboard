import React from 'react';
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface SprintTimelineProps {
  currentDay: number;
  totalDays: number;
  dailyChanges: Array<{
    day: number;
    added: number;
    removed: number;
  }>;
}

export function SprintTimeline({ currentDay, totalDays, dailyChanges }: SprintTimelineProps) {
  const progress = (currentDay / totalDays) * 100;

  return (
    <Card className="flex-1">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Sprint Timeline</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-muted-foreground">
            <span>Day {currentDay}</span>
            <span>{totalDays} Days Total</span>
          </div>
          <Progress value={progress} className="h-2" />
          
          {/* Optional: Show daily changes below the progress bar */}
          <div className="mt-4 space-y-1 text-sm">
            {dailyChanges.map((change, idx) => (
              <div key={idx} className="flex justify-between">
                <span>Day {change.day}</span>
                <div className="space-x-2">
                  {change.added > 0 && (
                    <span className="text-green-500">+{change.added}</span>
                  )}
                  {change.removed < 0 && (
                    <span className="text-red-500">{change.removed}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
} 