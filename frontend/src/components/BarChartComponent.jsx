import React from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';

const BarChartComponent = ({ 
  title, 
  data, 
  dataKey, 
  color = '#0f2d6b', 
  unit = '' 
}) => {
  return (
    <div
      className="
        relative
        bg-[#f5f6f8]
        rounded-[32px]
        p-5 sm:p-6
        border border-[#d9dee8]
        shadow-[0_10px_30px_rgba(15,23,42,0.10)]
        overflow-hidden
      "
    >
      {/* TOP HEADER */}
      <div className="flex items-center justify-between mb-5">
        
        {/* TITLE */}
        <div
          className="
            bg-[#0f2d6b]
            text-white
            px-5 sm:px-7
            py-3
            rounded-[20px]
            shadow-md
            tracking-[3px]
            uppercase
            text-[10px] sm:text-xs
            font-bold
            whitespace-nowrap
          "
        >
          {title}
        </div>

        {/* STATUS BADGE */}
        <div
          className="
            bg-[#eef3fb]
            text-[#3b5fb8]
            px-4 py-2
            rounded-2xl
            text-xs sm:text-sm
            font-semibold
            shadow-sm
          "
        >
          {unit}
        </div>
      </div>

      {/* CHART */}
      <ResponsiveContainer width="100%" height={220}>
        <BarChart
          data={data}
          margin={{
            top: 10,
            right: 10,
            left: -20,
            bottom: 0
          }}
        >
          <CartesianGrid
            strokeDasharray="4 4"
            stroke="rgba(148,163,184,0.25)"
          />

          <XAxis
            stroke="#7b88a8"
            tick={{ 
              fill: '#7b88a8', 
              fontSize: 11,
              fontWeight: 500
            }}
            axisLine={false}
            tickLine={false}
          />

          <YAxis
            stroke="#7b88a8"
            tick={{ 
              fill: '#7b88a8', 
              fontSize: 11,
              fontWeight: 500
            }}
            axisLine={false}
            tickLine={false}
          />

          <Tooltip
            cursor={{ fill: 'rgba(15,45,107,0.05)' }}
            contentStyle={{
              backgroundColor: '#ffffff',
              border: '1px solid #d9dee8',
              borderRadius: '18px',
              boxShadow: '0 10px 30px rgba(15,23,42,0.12)',
              padding: '10px'
            }}
            labelStyle={{
              color: '#0f2d6b',
              fontWeight: 700,
              fontSize: '12px'
            }}
            itemStyle={{
              color: '#0f2d6b',
              fontSize: '12px'
            }}
            formatter={(value) => [`${value.toFixed(0)} ${unit}`, 'Value']}
          />

          <Bar
            dataKey={dataKey}
            fill={color}
            radius={[12, 12, 0, 0]}
            barSize={28}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default BarChartComponent;