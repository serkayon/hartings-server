import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

const CircularGauge = ({ label, value, max, unit, color = '#3b82f6' }) => {
  const percentage = (value / max) * 100;
  
  const data = [
    { name: 'value', value: percentage },
    { name: 'empty', value: 100 - percentage }
  ];

  return (
    <div className="flex flex-col items-center justify-center">
      <ResponsiveContainer width={180} height={180}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={90}
            startAngle={180}
            endAngle={0}
            dataKey="value"
          >
            <Cell fill={color} />
            <Cell fill="rgba(255, 255, 255, 0.1)" />
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="absolute flex flex-col items-center justify-center">
        <div className="text-3xl font-bold text-white">{value}{unit || '%'}</div>
        <div className="text-xs text-gray-400 mt-1">{label}</div>
      </div>
    </div>
  );
};

export default CircularGauge;
