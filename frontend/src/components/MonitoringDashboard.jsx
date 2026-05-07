import React, { useEffect, useMemo, useState } from "react";
import Navbar from "./NavBar";
import {
  AlertTriangle,
  ChevronLeft,
  Cpu,
  Gauge,
  Radio,
  ShieldAlert,
  TimerReset,
  Wrench,
} from "lucide-react";
import LineChartComponent from "./LineChartComponent";
const defaultData = {
  machineStatus: "ACTIVE",
  controllerMode: "AUTO",
  currentProgram: "Part_12345.NC",
  currentTool: "#08",
  totalParts: 1847,
  cuttingStatus: "CUTTING",
  coordinates: { x: 125.45, y: 200.32, z: -50.1 },
  spindleSpeed: 3500,
  feedRate: 42,
  feedOutput: 900,
  feedOverride: 95,
  alarmActive: true,
  alarmCode: "T0125",
  alarmMessage: "SPINDLE OVERLOAD DETECTED",
  alarmTime: "08:52:31",
  spindleLoadData: [],
  feedRateData: [],
  cuttingTime: "00:15:32",
  idleTime: "00:05:20",
  breakdownTime: "00:00:00",
  shiftSummaries: [],
  consolidatedSummary: {
    name: "Per Day",
    start: "00:00",
    end: "24:00",
    remainingTime: "00:00:00",
    runtime: "00:00:00",
    idle: "00:00:00",
    breakdown: "00:00:00",
    runtimePercentage: 0,
    idlePercentage: 0,
    breakdownPercentage: 0,
    parts: 0,
    power: "0 kWh",
  },
};

const fallbackSpindleLoad = [
  { time: "00:10", load: 65 },
  { time: "00:12", load: 68 },
  { time: "00:14", load: 72 },
  { time: "00:16", load: 75 },
  { time: "00:18", load: 78 },
];

const fallbackFeedSeries = [
  { time: "00:10", rate: 620 },
  { time: "00:12", rate: 710 },
  { time: "00:14", rate: 780 },
  { time: "00:16", rate: 860 },
  { time: "00:18", rate: 920 },
];

const parseDurationToSeconds = (value) => {
  const parts = value.split(":").map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) {
    return 0;
  }

  const [hours, minutes, seconds] = parts;
  return hours * 3600 + minutes * 60 + seconds;
};

const clamp = (value) => Math.max(0, Math.min(100, value));

const outerCardClass =
  "rounded-[30px] bg-[#d9dee8] p-[2px] shadow-[0_20px_40px_rgba(15,23,42,0.14),0_8px_14px_rgba(15,23,42,0.08)]";
const innerCardClass =
  "rounded-[28px] bg-[linear-gradient(180deg,#ffffff_0%,#f6f7fb_100%)] shadow-[inset_0_1px_0_rgba(255,255,255,0.85),inset_0_-10px_24px_rgba(148,163,184,0.10)]";

function RaisedCard({ children, className = "", innerClassName = "" }) {
  return (
    <div className={`${outerCardClass} ${className}`}>
      <div className={`${innerCardClass} ${innerClassName}`}>{children}</div>
    </div>
  );
}

function HeaderTag({ label, value, tone = "navy" }) {
  const tones = {
    navy: "bg-[#102a5c] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.18)]",
    green:
      "bg-[#14923d] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.18)]",
    orange:
      "bg-[#ff9500] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.18)]",
    white: "bg-white text-[#102a5c] border border-[#d6dce8]",
  };

  return (
    <div
      className={`flex items-center justify-between gap-3 rounded-full px-4 py-2.5 text-sm font-semibold ${tones[tone]}`}
    >
      <span className="text-xs uppercase tracking-[0.2em] opacity-80">
        {label}
      </span>
      <span>{value}</span>
    </div>
  );
}

function SectionPill({ children, className = "" }) {
  return (
    <div
      className={`inline-flex items-center rounded-full bg-[#102a5c] px-5 py-3 text-sm font-bold tracking-[0.04em] text-white shadow-[0_12px_20px_rgba(16,42,92,0.18)] ${className}`}
    >
      {children}
    </div>
  );
}

function StatCard({ label, value, subtext }) {
  return (
    <RaisedCard>
      <div className="px-5 py-5">
        <div className="text-[11px] uppercase tracking-[0.24em] text-[#6d7b94]">
          {label}
        </div>
        <div className="mt-3 text-4xl font-bold text-[#12284c]">{value}</div>
        <div className="mt-2 text-sm text-[#7b879b]">{subtext}</div>
      </div>
    </RaisedCard>
  );
}

function MetricCard({ title, value, unit, percent, detail, tone = "blue" }) {
  const fills = {
    blue: "from-[#2d6cdf] to-[#80c3ff]",
    green: "from-[#1f9d43] to-[#84d79b]",
    orange: "from-[#f78a10] to-[#ffd47a]",
  };

  return (
    <RaisedCard innerClassName="h-full">
      <div className="px-5 py-5">
        <div className="flex items-center justify-between gap-3">
          <div className="text-sm font-semibold text-[#12284c]">{title}</div>
          <div className="rounded-full bg-[#eef3fb] px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-[#6d7b94]">
            Now
          </div>
        </div>
        <div className="mt-5 flex items-end gap-2">
          <div className="text-5xl font-bold leading-none text-[#102a5c]">
            {value}
          </div>
          <div className="pb-1 text-sm font-medium uppercase tracking-[0.12em] text-[#6c7b93]">
            {unit}
          </div>
        </div>
        <div className="mt-5 rounded-full bg-[#dfe7f2] p-1 shadow-[inset_0_2px_4px_rgba(15,23,42,0.08)]">
          <div
            className={`h-3 rounded-full bg-gradient-to-r ${fills[tone]} shadow-[0_4px_10px_rgba(15,23,42,0.14)]`}
            style={{ width: `${clamp(percent)}%` }}
          />
        </div>
        <div className="mt-3 text-sm text-[#738299]">{detail}</div>
      </div>
    </RaisedCard>
  );
}

function AxisCard({ axis, value }) {
  return (
    <RaisedCard>
      <div className="px-5 py-4">
        <div className="text-[11px] uppercase tracking-[0.24em] text-[#6d7b94]">
          {axis} Axis
        </div>
        <div className="mt-3 font-mono text-3xl font-bold text-[#12284c]">
          {value.toFixed(3)}
        </div>
        <div className="mt-1 text-sm text-[#7b879b]">Position</div>
      </div>
    </RaisedCard>
  );
}

const MonitoringDashboard = () => {
  const [dashboardData, setDashboardData] = useState(defaultData);
  useEffect(() => {
    let mounted = true;

    const fetchData = async () => {
      try {
        const response = await fetch("/api/dashboard");
        if (!response.ok) {
          return;
        }

        const liveData = await response.json();
        if (mounted) {
          setDashboardData(liveData);
        }
      } catch (error) {
        // Keep rendering the last known value when backend is temporarily unavailable.
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 2000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const spindleSeries =
    dashboardData.spindleLoadData.length > 0
      ? dashboardData.spindleLoadData
      : fallbackSpindleLoad;
  const feedSeries =
    dashboardData.feedRateData.length > 0
      ? dashboardData.feedRateData
      : fallbackFeedSeries;

  const latestSpindleLoad = spindleSeries.at(-1)?.load ?? 0;
  const spindleCapacity = Math.round((dashboardData.spindleSpeed / 6000) * 100);
  const cuttingSeconds = parseDurationToSeconds(dashboardData.cuttingTime);
  const idleSeconds = parseDurationToSeconds(dashboardData.idleTime);
  const totalSeconds = cuttingSeconds + idleSeconds;
  const utilization =
    totalSeconds > 0 ? Math.round((cuttingSeconds / totalSeconds) * 100) : 0;

  const productionStrip = useMemo(
    () => [
      {
        label: "Program",
        value: dashboardData.currentProgram,
        subtext: "Running file",
      },
      {
        label: "Mode",
        value: dashboardData.controllerMode,
        subtext: "Controller state",
      },
      {
        label: "Tool",
        value: dashboardData.currentTool,
        subtext: "Current offset",
      },
      {
        label: "Parts",
        value: dashboardData.totalParts.toLocaleString(),
        subtext: "Total produced",
      },
    ],
    [
      dashboardData.controllerMode,
      dashboardData.currentProgram,
      dashboardData.currentTool,
      dashboardData.totalParts,
    ],
  );

  const shiftSummaries =
    Array.isArray(dashboardData.shiftSummaries) &&
    dashboardData.shiftSummaries.length > 0
      ? dashboardData.shiftSummaries
      : [
          {
            name: "Shift A",
            start: "08:00",
            end: "16:00",
            runtime: dashboardData.cuttingTime,
            idle: dashboardData.idleTime,
            breakdown: dashboardData.breakdownTime || "00:00:00",
            remainingTime: "00:00:00",
            runtimePercentage: utilization,
            idlePercentage: clamp(100 - utilization),
            breakdownPercentage: 0,
            parts: dashboardData.totalParts,
            power: `${Math.max(1, Math.round(dashboardData.spindleSpeed / 1000))} kWh`,
          },
          {
            name: "Shift B",
            start: "16:00",
            end: "00:00",
            runtime: "00:00:00",
            idle: "00:00:00",
            breakdown: "00:00:00",
            remainingTime: "00:00:00",
            runtimePercentage: 0,
            idlePercentage: 0,
            breakdownPercentage: 0,
            parts: 0,
            power: "0 kWh",
          },
          {
            name: "Shift C",
            start: "00:00",
            end: "08:00",
            runtime: "00:00:00",
            idle: "00:00:00",
            breakdown: "00:00:00",
            remainingTime: "00:00:00",
            runtimePercentage: 0,
            idlePercentage: 0,
            breakdownPercentage: 0,
            parts: 0,
            power: "0 kWh",
          },
        ];

  const consolidatedSummary = dashboardData.consolidatedSummary || {
    name: "Per Day",
    start: "00:00",
    end: "24:00",
    remainingTime: "00:00:00",
    runtime: dashboardData.cuttingTime,
    idle: dashboardData.idleTime,
    breakdown: dashboardData.breakdownTime || "00:00:00",
    runtimePercentage: utilization,
    idlePercentage: clamp(100 - utilization),
    breakdownPercentage: 0,
    parts: dashboardData.totalParts,
    power: `${Math.max(1, Math.round(dashboardData.spindleSpeed / 1000))} kWh`,
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#ffffff_0%,_#f4f5f8_42%,_#eceef2_100%)] px-2 py-3 text-[#12284c] sm:px-3">
      <Navbar></Navbar>
      <div className="mx-auto max-w-[2800px] space-y-3">
  {/* entire dashboard */}

<div className="relative">
  <div className="pointer-events-none absolute left-1/2 top-1/2 hidden h-32 w-32 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,_rgba(16,42,92,0.06)_0%,_rgba(16,42,92,0.01)_55%,_transparent_75%)] lg:block" />

  {/* OUTER HOLDER CARD */}
  <div className="rounded-[24px] bg-white border border-[#e2e8f0] p-2.5 md:p-3 shadow-[0_8px_18px_rgba(15,23,42,0.04)]">


    {/* INNER GRID */}
    <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 xl:grid-cols-5">

      {/* MACHINE STATUS */}
      <div className="rounded-[22px] border border-[#e4eaf2] bg-[linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)] shadow-[0_4px_10px_rgba(15,23,42,0.04)]">
        <div className="px-3 py-3">

          <div className="text-[8px] uppercase tracking-[0.22em] text-[#6d7b94]">
            Machine Status
          </div>

          <div className="mt-2 flex items-center gap-2">

            <div className="h-2.5 w-2.5 rounded-full bg-[#1bb34a] shadow-[0_0_6px_rgba(34,197,94,0.5)]" />

            <div className="text-xl md:text-[24px] font-bold text-[#14923d]">
              {dashboardData.machineStatus}
            </div>
          </div>

          <div className="mt-1.5 text-[11px] text-[#7b879b]">
            Running condition
          </div>

        </div>
      </div>

      {/* MODE */}
      <div className="rounded-[22px] border border-[#e4eaf2] bg-[linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)] shadow-[0_4px_10px_rgba(15,23,42,0.04)]">
        <div className="px-3 py-3">

          <div className="text-[8px] uppercase tracking-[0.22em] text-[#6d7b94]">
            Mode
          </div>

          <div className="mt-2 text-xl md:text-[24px] font-bold text-[#102a5c]">
            {dashboardData.controllerMode}
          </div>

          <div className="mt-1.5 text-[11px] text-[#7b879b]">
            Controller state
          </div>

        </div>
      </div>

      {/* CURRENT PROGRAM */}
      <div className="rounded-[22px] border border-[#e4eaf2] bg-[linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)] shadow-[0_4px_10px_rgba(15,23,42,0.04)]">
        <div className="px-3 py-3">

          <div className="text-[8px] uppercase tracking-[0.22em] text-[#6d7b94]">
            Current Program
          </div>

          <div className="mt-2 break-words text-lg md:text-[22px] font-bold leading-tight text-[#102a5c]">
            {dashboardData.currentProgram}
          </div>

          <div className="mt-1.5 text-[11px] text-[#7b879b]">
            Active CNC file
          </div>

        </div>
      </div>

      {/* TOOL */}
      <div className="rounded-[22px] border border-[#e4eaf2] bg-[linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)] shadow-[0_4px_10px_rgba(15,23,42,0.04)]">
        <div className="px-3 py-3">

          <div className="text-[8px] uppercase tracking-[0.22em] text-[#6d7b94]">
            Tool
          </div>

          <div className="mt-2 text-xl md:text-[24px] font-bold text-[#102a5c]">
            {dashboardData.currentTool}
          </div>

          <div className="mt-1.5 text-[11px] text-[#7b879b]">
            Active tool offset
          </div>

        </div>
      </div>

      {/* CURRENT POSITION */}
      <div className="rounded-[22px] border border-[#e4eaf2] bg-[linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)] shadow-[0_4px_10px_rgba(15,23,42,0.04)]">
        <div className="px-2.5 py-2.5 h-full">

          <div className="text-[8px] uppercase tracking-[0.20em] text-[#6d7b94]">
            Current Position
          </div>

          <div className="mt-2 grid grid-cols-3 gap-1.5">

            {/* X */}
            <div className="rounded-[12px] border border-[#dbe3ee] bg-[#eef2f7] px-2 py-2 flex flex-col justify-between">

              <div className="text-[7px] uppercase tracking-[0.15em] text-[#6d7b94]">
                X Axis
              </div>

              <div className="font-mono text-[15px] xl:text-base font-bold leading-none text-[#102a5c]">
                {dashboardData.coordinates.x.toFixed(2)}
              </div>

              <div className="text-[8px] text-[#7b879b]">
                Position
              </div>
            </div>

            {/* Y */}
            <div className="rounded-[12px] border border-[#dbe3ee] bg-[#eef2f7] px-2 py-2 flex flex-col justify-between">

              <div className="text-[7px] uppercase tracking-[0.15em] text-[#6d7b94]">
                Y Axis
              </div>

              <div className="font-mono text-[15px] xl:text-base font-bold leading-none text-[#102a5c]">
                {dashboardData.coordinates.y.toFixed(2)}
              </div>

              <div className="text-[8px] text-[#7b879b]">
                Position
              </div>
            </div>

            {/* Z */}
            <div className="rounded-[12px] border border-[#dbe3ee] bg-[#eef2f7] px-2 py-2 flex flex-col justify-between">

              <div className="text-[7px] uppercase tracking-[0.15em] text-[#6d7b94]">
                Z Axis
              </div>

              <div className="font-mono text-[15px] xl:text-base font-bold leading-none text-[#102a5c]">
                {dashboardData.coordinates.z.toFixed(2)}
              </div>

              <div className="text-[8px] text-[#7b879b]">
                Position
              </div>
            </div>

          </div>
        </div>
      </div>

    </div>
  </div>
</div>

      <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
        {shiftSummaries.map((shiftCard) => (
          <RaisedCard key={shiftCard.name}>
            <div className="px-5 py-5">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="mt-1 text-2xl font-bold text-[#102a5c]">
                    {shiftCard.name}
                  </div>
                  <div className="text-[11px] uppercase tracking-[0.24em] text-[#6d7b94]">
                    {shiftCard.start} - {shiftCard.end}
                  </div>
                </div>
                <div className="rounded-full bg-[#eef2f7] px-4 py-2 text-sm font-semibold text-[#102a5c]">
                  Remaining : {shiftCard.remainingTime || "00:00:00"}
                </div>
              </div>

              <div className="mt-3">
                <div className="flex overflow-hidden rounded-full h-4 bg-[#dfe5ee]">
                  <div
                    className="bg-[#1ba34a]"
                    style={{ width: `${shiftCard.runtimePercentage}%` }}
                  />
                  <div
                    className="bg-[#cbd5e1]"
                    style={{ width: `${shiftCard.idlePercentage}%` }}
                  />
                  <div
                    className="bg-[#ef4444]"
                    style={{ width: `${shiftCard.breakdownPercentage}%` }}
                  />
                </div>

                <div className="mt-4 grid grid-cols-3 gap-3">
                  <div className="rounded-[18px] bg-[#edf9f0] px-3 py-3">
                    <div className="text-[10px] uppercase tracking-[0.18em] text-[#3c7a50]">
                      Runtime
                    </div>
                    <div className="mt-2 text-lg font-bold text-[#14923d]">
                      {shiftCard.runtime}
                    </div>
                  </div>

                  <div className="rounded-[18px] bg-[#f1f5f9] px-3 py-3">
                    <div className="text-[10px] uppercase tracking-[0.18em] text-[#64748b]">
                      Idle Time
                    </div>
                    <div className="mt-2 text-lg font-bold text-[#475569]">
                      {shiftCard.idle}
                    </div>
                  </div>

                  <div className="rounded-[18px] bg-[#fef0f0] px-3 py-3">
                    <div className="text-[10px] uppercase tracking-[0.18em] text-[#dc2626]">
                      Breakdown
                    </div>
                    <div className="mt-2 text-lg font-bold text-[#dc2626]">
                      {shiftCard.breakdown}
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-3 grid grid-cols-2 gap-3">
                <div className="rounded-[18px] bg-[#eef2f7] px-4 py-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-[#6d7b94]">
                    Parts
                  </div>
                  <div className="mt-2 text-2xl font-bold text-[#102a5c]">
                    {shiftCard.parts}
                  </div>
                </div>

                <div className="rounded-[18px] bg-[#eef2f7] px-4 py-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-[#6d7b94]">
                    Power Consume
                  </div>
                  <div className="mt-2 text-2xl font-bold text-[#102a5c]">
                    {shiftCard.power}
                  </div>
                </div>
              </div>
            </div>
          </RaisedCard>
        ))}
      </div>


         <div className="grid gap-3 grid-cols-1 xl:grid-cols-[2fr_0.9fr] items-start">
            <RaisedCard>
  <div className="px-5 py-5">

    {/* HEADER */}
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">

      <div>
        <div className="text-[11px] uppercase tracking-[0.24em] text-[#6d7b94]">
      
            Consolidated Overview
        </div>

        <div className="mt-1 text-2xl font-bold text-[#102a5c]">
             Per Day
        </div>
      </div>

      <div className="rounded-full bg-[#eef2f7] px-4 py-2 text-sm font-semibold text-[#102a5c]">
        Remaining : {consolidatedSummary.remainingTime || "00:00:00"}
      </div>
    </div>

    {/* PROGRESS BAR */}
    <div className="mt-3">

      <div className="flex overflow-hidden rounded-full h-4 bg-[#dfe5ee]">
        <div className="bg-[#1ba34a]" style={{ width: `${consolidatedSummary.runtimePercentage}%` }} />
        <div className="bg-[#cbd5e1]" style={{ width: `${consolidatedSummary.idlePercentage}%` }} />
        <div className="bg-[#ef4444]" style={{ width: `${consolidatedSummary.breakdownPercentage}%` }} />
      </div>

      {/* STATUS CARDS */}
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">

        {/* Runtime */}
        <div className="rounded-[18px] bg-[#edf9f0] px-4 py-3">
          
          <div className="text-[10px] uppercase tracking-[0.18em] text-[#3c7a50]">
            Runtime
          </div>

          <div className="mt-1 text-xl font-bold text-[#14923d]">
            {consolidatedSummary.runtime}
          </div>
        </div>

        {/* Idle */}
        <div className="rounded-[18px] bg-[#f1f5f9] px-4 py-3">
          
          <div className="text-[10px] uppercase tracking-[0.18em] text-[#64748b]">
            Idle Time
          </div>

          <div className="mt-2 text-xl font-bold text-[#475569]">
            {consolidatedSummary.idle}
          </div>
        </div>

        {/* Breakdown */}
        <div className="rounded-[18px] bg-[#fef0f0] px-4 py-3">
          
          <div className="text-[10px] uppercase tracking-[0.18em] text-[#dc2626]">
            Breakdown
          </div>

          <div className="mt-2 text-xl font-bold text-[#dc2626]">
            {consolidatedSummary.breakdown}
          </div>
        </div>

      </div>
    </div>

    {/* FOOTER */}
    <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">

      {/* Parts */}
      <div className="rounded-[18px] bg-[#eef2f7] px-4 py-3">

        <div className="text-[10px] uppercase tracking-[0.18em] text-[#6d7b94]">
          Parts
        </div>

        <div className="mt-2 text-2xl font-bold text-[#102a5c]">
          {consolidatedSummary.parts}
        </div>
      </div>

      {/* Power */}
      <div className="rounded-[18px] bg-[#eef2f7] px-4 py-3">

        <div className="text-[10px] uppercase tracking-[0.18em] text-[#6d7b94]">
          Power Consume
        </div>

        <div className="mt-2 text-2xl font-bold text-[#102a5c]">
          {consolidatedSummary.power}
        </div>
      </div>

    </div>
  </div>
</RaisedCard>
           <RaisedCard className="w-full">
  <div className="px-3 py-4 sm:px-5 sm:py-5 h-[305px]">
    
    {/* Header */}
    <div className="flex items-center justify-between gap-2 sm:gap-3">
      <SectionPill className="px-3 py-1.5 text-[10px] sm:px-4 sm:py-2 sm:text-xs tracking-[0.18em] sm:tracking-[0.22em]">
        Alarm Console
      </SectionPill>

      <div className="flex h-11 w-11 sm:h-14 sm:w-14 flex-shrink-0 items-center justify-center rounded-[16px] sm:rounded-[20px] bg-[linear-gradient(180deg,#fff0dc_0%,#ffe0b7_100%)] text-[#ff8e00] shadow-[0_8px_18px_rgba(255,149,0,0.14)]">
        <ShieldAlert size={18} className="sm:hidden" />
        <ShieldAlert size={22} className="hidden sm:block" />
      </div>
    </div>

    {/* Alarm Body */}
    <div className="mt-4 rounded-[22px] sm:rounded-[28px] bg-[linear-gradient(180deg,#ffffff_0%,#fff6eb_100%)] px-4 py-4 sm:px-5 sm:py-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.9),0_10px_22px_rgba(15,23,42,0.06)]">
      
      {/* Top Section */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        
        <div className="min-w-0">
          <div className="text-[10px] sm:text-[11px] uppercase tracking-[0.18em] sm:tracking-[0.24em] text-[#9a7237]">
            Alarm Code
          </div>

          <div className="mt-2 break-words text-3xl sm:text-5xl font-bold leading-none text-[#102a5c]">
            {dashboardData.alarmCode}
          </div>
        </div>

        <div className="self-start sm:self-auto">
          <HeaderTag
            label="Status"
            value={dashboardData.alarmActive ? "Active" : "Clear"}
            tone="orange"
          />
        </div>
      </div>

      {/* Message */}
      <div className="mt-4 text-xs sm:text-sm leading-5 sm:leading-6 text-[#5b667a] break-words">
        {dashboardData.alarmMessage}
      </div>

      {/* Footer Info */}
      <div className="mt-4 grid grid-cols-1 gap-2 text-xs sm:text-sm text-[#6d7b94] sm:grid-cols-2">
        <div className="break-words">
          Last seen: {dashboardData.alarmTime}
        </div>

        <div className="sm:text-right">
          Intervention required
        </div>
      </div>
    </div>
  </div>
</RaisedCard>
          </div>
      </div>
    </div>
  );
};

export default MonitoringDashboard;
