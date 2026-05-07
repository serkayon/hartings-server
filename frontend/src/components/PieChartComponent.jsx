import React from 'react';
import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer } from 'recharts';

const PieChartComponent = ({
  title,
  data,
  colors = ['#16a34a', '#d6dde8']
}) => {
  return (
    <div
      className="
        bg-[#f5f7fb]
        rounded-[32px]
        p-6
        border border-[#d9e1ec]
        shadow-[0_10px_30px_rgba(15,45,107,0.08)]
      "
    >
      <h3
        className="
          text-sm
          font-semibold
          text-[#0f2d6b]
          mb-4
          tracking-[0.15em]
          uppercase
        "
      >
        {title}
      </h3>

      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, value }) => `${name}: ${value}%`}
            outerRadius={80}
            fill="#0f2d6b"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={colors[index % colors.length]}
                stroke="#f5f7fb"
                strokeWidth={4}
              />
            ))}
          </Pie>

          <Tooltip
            contentStyle={{
              backgroundColor: '#ffffff',
              border: '1px solid #d9e1ec',
              borderRadius: '20px',
              boxShadow: '0 10px 30px rgba(15,45,107,0.12)',
              color: '#0f2d6b',
              fontSize: '13px'
            }}
            labelStyle={{
              color: '#0f2d6b',
              fontWeight: 600
            }}
            itemStyle={{
              color: '#6b7a99'
            }}
            cursor={{ fill: 'rgba(15,45,107,0.04)' }}
          />

          <Legend
            wrapperStyle={{
              color: '#0f2d6b',
              fontSize: '13px',
              paddingTop: '12px',
              letterSpacing: '0.03em'
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PieChartComponent;