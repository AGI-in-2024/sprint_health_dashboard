import React, { useMemo, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { CalendarDays, AlertCircle, CheckCircle2, Clock, Calendar } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

interface SprintTimelineProps {
  currentDay: number;
  totalDays: number;
  timeFramePercentage: number;
  backlogChanges?: number;
  selectedSprints: string[];
  onTimelineChange: (percentage: number, day: number) => void;
}

type TimeRange = 'sprint' | 'quarter' | 'halfYear' | 'year';

type Milestone = {
  id: string;
  day: number;
  label: string;
  icon: React.ReactNode;
  date?: Date;
}

export function SprintTimeline({
  currentDay,
  totalDays,
  timeFramePercentage,
  backlogChanges,
  selectedSprints,
  onTimelineChange
}: SprintTimelineProps) {
  // Add validation for timeline updates
  const handleTimelineUpdate = useCallback((percentage: number, day: number) => {
    // Validate inputs
    if (isNaN(percentage) || isNaN(day)) {
      console.warn('Invalid timeline update values:', { percentage, day });
      return;
    }
    
    // Ensure percentage is within bounds
    const validPercentage = Math.max(0, Math.min(100, percentage));
    
    // Ensure day is within bounds
    const validDay = Math.max(0, Math.min(totalDays, day));
    
    // Only trigger update if values are valid
    onTimelineChange(validPercentage, validDay);
  }, [totalDays, onTimelineChange]);

  // Format day display to handle NaN
  const displayDay = isNaN(currentDay) ? 0 : currentDay;
  const displayTotal = isNaN(totalDays) ? 0 : totalDays;

  // Calculate sprint dates from sprint names
  const sprintDates = useMemo(() => {
    return selectedSprints.map(sprintName => {
      const dateMatch = sprintName.match(/\d{4}\.\d+\.\d+/);
      if (dateMatch) {
        const [year, month, day] = dateMatch[0].split('.');
        return new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
      }
      return null;
    }).filter((date): date is Date => date !== null)
    .sort((a, b) => a.getTime() - b.getTime());
  }, [selectedSprints]);

  // Calculate timeline based on selected sprints
  const timelineInfo = useMemo(() => {
    if (sprintDates.length === 0) return null;

    const firstDate = sprintDates[0];
    const lastDate = sprintDates[sprintDates.length - 1];
    const totalDays = Math.ceil((lastDate.getTime() - firstDate.getTime()) / (1000 * 60 * 60 * 24));
    
    // Generate milestones based on number of sprints
    if (sprintDates.length === 1) {
      // Single sprint view
      const milestones: Milestone[] = [
        { id: 'start', day: 0, label: 'Старт', icon: <Clock className="w-4 h-4" /> },
        { id: 'day2', day: 2, label: '2 дня', icon: <AlertCircle className="w-4 h-4" /> },
        { id: 'middle', day: 7, label: 'Середина', icon: <CalendarDays className="w-4 h-4" /> },
        { id: 'end', day: 14, label: 'Финиш', icon: <CheckCircle2 className="w-4 h-4" /> },
      ];
      return {
        milestones,
        totalDays: 14,
        type: 'sprint' as TimeRange
      };
    } else {
      // Multiple sprints view
      const milestones: Milestone[] = sprintDates.map((date, index) => ({
        id: `sprint${index}`,
        day: Math.ceil((date.getTime() - firstDate.getTime()) / (1000 * 60 * 60 * 24)),
        label: `Спринт ${index + 1}`,
        icon: <Calendar className="w-4 h-4" />,
        date
      }));

      return {
        milestones,
        totalDays,
        type: sprintDates.length <= 6 ? 'quarter' : 'year' as TimeRange
      };
    }
  }, [sprintDates]);

  // Get period description
  const getPeriodDescription = (type: TimeRange) => {
    switch (type) {
      case 'sprint':
        return 'Анализ одного спринта';
      case 'quarter':
        return 'Анализ квартала';
      case 'halfYear':
        return 'Анализ полугодия';
      case 'year':
        return 'Анализ года';
      default:
        return 'Выберите период';
    }
  };

  if (!timelineInfo) return null;

  const { milestones, type } = timelineInfo;

  // Update click handlers to use the new safe update function
  const handleMilestoneClick = (milestone: Milestone) => {
    const percentage = (milestone.day / totalDays) * 100;
    handleTimelineUpdate(
      isNaN(percentage) ? 100 : percentage,
      milestone.day
    );
  };

  return (
    <Card className="mb-4">
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          <span>{getPeriodDescription(type)}</span>
          <span className="text-sm font-normal">
            {selectedSprints.length > 1 
              ? `${selectedSprints.length} спринтов` 
              : `День ${displayDay} из ${displayTotal}`}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Timeline visualization */}
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute h-1 bg-gray-200 w-full top-7">
              <div 
                className="absolute h-full bg-blue-500 transition-all duration-300"
                style={{ width: `${timeFramePercentage}%` }}
              />
            </div>

            {/* Milestone markers */}
            <div className="flex justify-between relative">
              {milestones.map((milestone) => (
                <div 
                  key={milestone.id}
                  className={`flex flex-col items-center relative ${
                    displayDay >= milestone.day ? 'text-blue-500' : 'text-gray-400'
                  }`}
                >
                  <div className="mb-2">
                    {milestone.icon}
                  </div>
                  <div className="text-xs font-medium">
                    {milestone.label}
                  </div>
                  <div className="text-xs mt-1">
                    {milestone.date 
                      ? milestone.date.toLocaleDateString('ru-RU', { 
                          month: 'short', 
                          day: 'numeric' 
                        })
                      : `День ${milestone.day}`
                    }
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Navigation controls */}
          <div className="flex flex-wrap gap-2 justify-center">
            {type === 'sprint' ? (
              // Single sprint navigation
              milestones.map((milestone) => (
                <Button
                  key={milestone.id}
                  variant={currentDay === milestone.day ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleMilestoneClick(milestone)}
                >
                  {milestone.label}
                </Button>
              ))
            ) : (
              // Multiple sprints navigation
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => handleTimelineUpdate(0, 0)}
                >
                  Начало периода
                </Button>
                {sprintDates.map((date, index) => (
                  <Button
                    key={index}
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const percentage = (index / (sprintDates.length - 1)) * 100;
                      const day = Math.floor((percentage / 100) * totalDays);
                      handleTimelineUpdate(percentage, day);
                    }}
                  >
                    Спринт {index + 1}
                  </Button>
                ))}
                <Button
                  variant="outline"
                  onClick={() => handleTimelineUpdate(100, totalDays)}
                >
                  Конец периода
                </Button>
              </div>
            )}
          </div>

          {/* Status information */}
          {type === 'sprint' && displayDay > 0 && (
            <div className="mt-4">
              {displayDay <= 2 ? (
                <Alert>
                  <AlertTitle className="flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    Начальная фаза спринта
                  </AlertTitle>
                  <AlertDescription>
                    В первые два дня спринта команда уточняет бэклог и приоритеты задач
                  </AlertDescription>
                </Alert>
              ) : (
                <Alert variant={backlogChanges && backlogChanges > 20 ? "destructive" : "default"}>
                  <AlertTitle className="flex items-center gap-2">
                    {backlogChanges && backlogChanges > 20 ? (
                      <AlertCircle className="w-4 h-4" />
                    ) : (
                      <CheckCircle2 className="w-4 h-4" />
                    )}
                    Основная фаза спринта
                  </AlertTitle>
                  <AlertDescription>
                    {backlogChanges && backlogChanges > 20 
                      ? `Внимание: значительные изменения бэклога (${backlogChanges}%)`
                      : 'Спринт проходит в штатном режиме'}
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
} 