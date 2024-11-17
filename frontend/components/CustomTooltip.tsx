import React from 'react';

type CustomTooltipProps = {
  active?: boolean;
  payload?: any;
  label?: any;
};

export const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-2 border rounded shadow-lg">
        <p className="font-bold">Day {label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={`item-${index}`} style={{ color: entry.color }}>
            {entry.name}: {entry.value} Ч/Д
          </p>
        ))}
      </div>
    );
  }

  return null;
}; 