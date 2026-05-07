import React, { useState, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import LineChartComponent from './LineChartComponent';
import BarChartComponent from './BarChartComponent';
import PieChartComponent from './PieChartComponent';
import Navbar from './NavBar';
const PerformanceAnalytics = () => {
  const [filters, setFilters] = useState({
    dateRange: 'Last 30 Days',
    shift: 'All Shifts',
    machine: 'CNC-02'
  });
  const [analyticsData, setAnalyticsData] = useState({
    spindleLoadData: [
      { date: '7 Mar', load: 65 },
      { date: '8 Mar', load: 72 },
      { date: '9 Mar', load: 68 },
      { date: '10 Mar', load: 75 },
      { date: '11 Mar', load: 70 },
      { date: '12 Mar', load: 78 },
      { date: '13 Mar', load: 73 },
      { date: '14 Mar', load: 80 },
      { date: '15 Mar', load: 76 },
      { date: '16 Mar', load: 82 },
    ],
    feedRateData: [
      { date: '7 Mar', rate: 850 },
      { date: '8 Mar', rate: 920 },
      { date: '9 Mar', rate: 880 },
      { date: '10 Mar', rate: 950 },
      { date: '11 Mar', rate: 900 },
      { date: '12 Mar', rate: 980 },
      { date: '13 Mar', rate: 920 },
      { date: '14 Mar', rate: 1000 },
      { date: '15 Mar', rate: 950 },
      { date: '16 Mar', rate: 1050 },
    ],
    spindleSpeedData: [
      { date: '7 Mar', speed: 3200 },
      { date: '8 Mar', speed: 3400 },
      { date: '9 Mar', speed: 3100 },
      { date: '10 Mar', speed: 3500 },
      { date: '11 Mar', speed: 3300 },
      { date: '12 Mar', speed: 3600 },
      { date: '13 Mar', speed: 3400 },
      { date: '14 Mar', speed: 3700 },
      { date: '15 Mar', speed: 3500 },
      { date: '16 Mar', speed: 3800 },
    ],
    cycleTimeData: [
      { date: '7 Mar', avg: 22, max: 25 },
      { date: '8 Mar', avg: 24, max: 27 },
      { date: '9 Mar', avg: 21, max: 24 },
      { date: '10 Mar', avg: 25, max: 29 },
      { date: '11 Mar', avg: 23, max: 26 },
      { date: '12 Mar', avg: 26, max: 30 },
      { date: '13 Mar', avg: 24, max: 27 },
      { date: '14 Mar', avg: 27, max: 31 },
      { date: '15 Mar', avg: 25, max: 28 },
      { date: '16 Mar', avg: 28, max: 32 },
    ],
    partsProducedData: [
      { date: '7 Mar', parts: 45 },
      { date: '8 Mar', parts: 52 },
      { date: '9 Mar', parts: 48 },
      { date: '10 Mar', parts: 58 },
      { date: '11 Mar', parts: 50 },
      { date: '12 Mar', parts: 62 },
      { date: '13 Mar', parts: 55 },
      { date: '14 Mar', parts: 68 },
      { date: '15 Mar', parts: 60 },
      { date: '16 Mar', parts: 75 },
    ],
    machineUtilizationData: [
      { date: '7 Mar', utilization: 72, target: 80 },
      { date: '8 Mar', utilization: 75, target: 80 },
      { date: '9 Mar', utilization: 70, target: 80 },
      { date: '10 Mar', utilization: 78, target: 80 },
      { date: '11 Mar', utilization: 73, target: 80 },
      { date: '12 Mar', utilization: 81, target: 80 },
      { date: '13 Mar', utilization: 76, target: 80 },
      { date: '14 Mar', utilization: 84, target: 80 },
      { date: '15 Mar', utilization: 79, target: 80 },
      { date: '16 Mar', utilization: 87, target: 80 },
    ],
    downtimeData: [
      { name: 'Running', value: 68 },
      { name: 'Idle', value: 32 }
    ],
    alarmDistributionData: [
      { type: 'Overheat', count: 48 },
      { type: 'Low Air Pressure', count: 38 },
      { type: 'Axis Fault', count: 28 },
      { type: 'Power Failure', count: 18 },
      { type: 'Other', count: 8 }
    ]
  });

  const fetchData = async () => {
    try {
      const query = new URLSearchParams({
        dateRange: filters.dateRange,
        shift: filters.shift,
        machine: filters.machine,
      });
      const response = await fetch(`/api/analytics?${query.toString()}`);
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      setAnalyticsData(prev => ({ ...prev, ...data }));
    } catch (error) {
      // Keep showing the latest successful payload if API fails temporarily.
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [filters.dateRange, filters.shift, filters.machine]);

  return (
    <div className="w-full min-h-screen bg-[#f4f5f7] p-3 text-[#102c67]">
      <Navbar />
 <div className="flex flex-col gap-4 mb-5">

  {/* TOP ANALYTICS BAR */}
  <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-3 rounded-[24px] border border-[#e2e8f0] bg-white px-4 py-3 shadow-[0_10px_24px_rgba(15,23,42,0.05)]">

    {/* TITLE */}
    <div className="min-w-fit">
      <h1 className="text-lg md:text-xl font-bold text-[#102c67] whitespace-nowrap">
        CNC Machine Performance Analytics
      </h1>
    </div>

    {/* FILTERS */}
    <div className="flex flex-col sm:flex-row flex-wrap xl:flex-nowrap items-stretch xl:items-center gap-2 w-full xl:w-auto">

      <button className="bg-[#f8fafc] text-[#102c67] px-4 py-2 rounded-xl text-xs flex items-center justify-between gap-2 border border-[#d7deea] shadow-sm hover:shadow-md transition-all whitespace-nowrap">
        <span>Date Range: {filters.dateRange}</span>
        <ChevronDown size={14} />
      </button>

      <button className="bg-[#f8fafc] text-[#102c67] px-4 py-2 rounded-xl text-xs flex items-center justify-between gap-2 border border-[#d7deea] shadow-sm hover:shadow-md transition-all whitespace-nowrap">
        <span>Shift: {filters.shift}</span>
        <ChevronDown size={14} />
      </button>

      <button className="bg-[#f8fafc] text-[#102c67] px-4 py-2 rounded-xl text-xs flex items-center justify-between gap-2 border border-[#d7deea] shadow-sm hover:shadow-md transition-all whitespace-nowrap">
        <span>Machine: {filters.machine}</span>
        <ChevronDown size={14} />
      </button>

      <button
        onClick={fetchData}
        className="bg-[#102c67] hover:bg-[#163c8f] text-white px-5 py-2 rounded-xl text-xs font-semibold shadow-md transition-all whitespace-nowrap"
      >
        APPLY FILTERS
      </button>

    </div>
  </div>
</div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 mb-6">

        <div className="bg-white rounded-[30px] p-6 border border-[#dce2ec] shadow-xl">
          <h3 className="text-sm font-semibold text-[#102c67] mb-4 tracking-wide">
            Spindle Load Over Time
          </h3>

          <LineChartComponent
            title=""
            data={analyticsData.spindleLoadData}
            dataKey="load"
            color="#3b82f6"
            unit="%"
          />
        </div>

        <div className="bg-white rounded-[30px] p-6 border border-[#dce2ec] shadow-xl">
          <h3 className="text-sm font-semibold text-[#102c67] mb-4 tracking-wide">
            Feed Rate Trend
          </h3>

          <LineChartComponent
            title=""
            data={analyticsData.feedRateData}
            dataKey="rate"
            color="#f59e0b"
            unit="IPM"
          />
        </div>

        <div className="bg-white rounded-[30px] p-6 border border-[#dce2ec] shadow-xl">
          <h3 className="text-sm font-semibold text-[#102c67] mb-4 tracking-wide">
            Spindle Speed History
          </h3>

          <LineChartComponent
            title=""
            data={analyticsData.spindleSpeedData}
            dataKey="speed"
            color="#22c55e"
            unit="RPM"
          />
        </div>

      </div>

      {/* Row 2 */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 mb-6">

        <div className="bg-white rounded-[30px] p-6 border border-[#dce2ec] shadow-xl">
          <h3 className="text-sm font-semibold text-[#102c67] mb-4">
            Cycle Time Analysis
          </h3>

          <div className="bg-[#f6f8fc] rounded-2xl p-4 mb-4 border border-[#e3e8f0]">
            <div className="flex justify-between gap-4 mb-2 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-[#0f2d6b]"></div>
                <span className="text-[#6b7a99]">Avg. Cycle Time</span>
              </div>

              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-[#f59e0b]"></div>
                <span className="text-[#6b7a99]">Max Cycle Time</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-5 gap-2 text-center text-xs">
            {analyticsData.cycleTimeData.map((item, idx) => (
              <div key={idx} className="flex flex-col items-center">

                <div className="mb-2 space-y-1">
                  <div
                    className="w-4 bg-[#0f2d6b] rounded-sm mx-auto"
                    style={{ height: `${(item.avg / 30) * 60}px` }}
                  ></div>

                  <div
                    className="w-4 bg-[#f59e0b] rounded-sm mx-auto"
                    style={{ height: `${(item.max / 35) * 60}px` }}
                  ></div>
                </div>

                <span className="text-[#6b7a99] text-xs mt-1">
                  {item.date.split(' ')[0]}
                </span>

              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-[30px] p-6 border border-[#dce2ec] shadow-xl">
          <h3 className="text-sm font-semibold text-[#102c67] mb-4">
            Parts Produced
          </h3>

          <BarChartComponent
            title=""
            data={analyticsData.partsProducedData}
            dataKey="parts"
            color="#0f2d6b"
          />
        </div>

        <div className="bg-white rounded-[30px] p-6 border border-[#dce2ec] shadow-xl">
          <h3 className="text-sm font-semibold text-[#102c67] mb-4">
            Machine Utilization
          </h3>

          <div className="space-y-4">
            {analyticsData.machineUtilizationData.slice(-5).map((item, idx) => (
              <div key={idx}>

                <div className="flex justify-between mb-2 text-xs">
                  <span className="text-[#6b7a99]">{item.date}</span>

                  <div className="flex gap-3">
                    <span className="text-[#0f2d6b] font-semibold">
                      Utilization
                    </span>

                    <span className="text-[#f59e0b] font-semibold">
                      Target
                    </span>
                  </div>
                </div>

                <div className="relative h-3 bg-[#dbe2ec] rounded-full overflow-hidden">

                  <div
                    className="h-full bg-[#0f2d6b] rounded-full"
                    style={{ width: `${item.utilization}%` }}
                  ></div>

                  <div
                    className="absolute top-1/2 h-full w-1 bg-[#f59e0b]"
                    style={{
                      left: `${item.target}%`,
                      transform: 'translateX(-50%)'
                    }}
                  ></div>

                </div>

              </div>
            ))}
          </div>
        </div>

      </div>

      {/* Row 3 */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

        <div className="bg-white rounded-[30px] p-6 border border-[#dce2ec] shadow-xl">
          <h3 className="text-sm font-semibold text-[#102c67] mb-6">
            Downtime Analysis
          </h3>

          <div className="grid grid-cols-2 gap-6">

            <div className="flex flex-col items-center justify-center">
              <svg viewBox="0 0 200 200" className="w-40 h-40">

                <circle
                  cx="100"
                  cy="100"
                  r="80"
                  fill="#22c55e"
                  opacity="0.9"
                />

                <path
                  d="M 100 100 L 100 20 A 80 80 0 0 1 156.6 156.6 Z"
                  fill="#d1d5db"
                  opacity="0.9"
                />

                <text
                  x="65"
                  y="120"
                  fontSize="28"
                  fontWeight="bold"
                  fill="#102c67"
                >
                  68%
                </text>

                <text
                  x="50"
                  y="145"
                  fontSize="12"
                  fill="#6b7a99"
                >
                  Running
                </text>

              </svg>
            </div>

            <div className="flex flex-col justify-center gap-4">

              <div className="bg-[#f6f8fc] rounded-2xl p-4 border border-[#e3e8f0]">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-green-500"></div>

                  <div>
                    <div className="text-[#102c67] font-semibold text-sm">
                      Running
                    </div>

                    <div className="text-[#6b7a99] text-xs">
                      68% - Active operation
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-[#f6f8fc] rounded-2xl p-4 border border-[#e3e8f0]">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-gray-400"></div>

                  <div>
                    <div className="text-[#102c67] font-semibold text-sm">
                      Idle
                    </div>

                    <div className="text-[#6b7a99] text-xs">
                      32% - Waiting time
                    </div>
                  </div>
                </div>
              </div>

            </div>

          </div>
        </div>

        <div className="bg-white rounded-[30px] p-6 border border-[#dce2ec] shadow-xl">

          <h3 className="text-sm font-semibold text-[#102c67] mb-6">
            Alarm Distribution
          </h3>

          <div className="grid grid-cols-3 gap-4">

            <div className="col-span-2 flex items-end justify-center gap-2 h-48">

              {analyticsData.alarmDistributionData.map((item, idx) => {
                const maxCount = 48;
                const heights = [48, 38, 28, 18, 8];

                return (
                  <div key={idx} className="flex flex-col items-center flex-1 gap-2">

                    <div
                      className="w-full bg-[#0f2d6b] rounded-t-xl"
                      style={{
                        height: `${(heights[idx] / maxCount) * 180}px`,
                        minHeight: '8px'
                      }}
                    ></div>

                    <span className="text-xs text-[#6b7a99] font-semibold">
                      {heights[idx]}
                    </span>

                  </div>
                );
              })}

            </div>

            <div className="flex flex-col justify-start gap-3 text-sm">

              {analyticsData.alarmDistributionData.map((item, idx) => (
                <div
                  key={idx}
                  className="bg-[#f6f8fc] rounded-2xl p-3 border border-[#e3e8f0]"
                >
                  <div className="text-[#102c67] font-semibold text-xs">
                    {item.type}
                  </div>

                  <div className="text-[#6b7a99] text-xs mt-1">
                    {[48, 38, 28, 18, 8][idx]} occurrences
                  </div>
                </div>
              ))}

            </div>

          </div>

        </div>

      </div>

    </div>
  );
};

export default PerformanceAnalytics;
