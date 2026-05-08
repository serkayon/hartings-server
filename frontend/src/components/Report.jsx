import React, { useEffect, useState } from "react";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import {
  CalendarDays,
  Filter,
  AlertTriangle,
  FileText,
  Activity,
  Clock3,
} from "lucide-react";
import "./ReportDatePicker.css";
const RaisedCard = ({ children, className = "" }) => {
  return (
    <div
      className={`w-full overflow-hidden rounded-[24px] border border-[#d9e1ec] bg-white shadow-[0_10px_30px_rgba(15,23,42,0.06)] ${className}`}
    >
      {children}
    </div>
  );
};

const SHIFT_DURATION_SECONDS = 8 * 60 * 60;
const clamp = (value) => Math.max(0, Math.min(100, value));
const PAD = (value) => String(value).padStart(2, "0");

const parseLocalDateTime = (value) => {
  if (!value) return null;
  const dt = new Date(value);
  return Number.isNaN(dt.getTime()) ? null : dt;
};

const formatLocalDateTime = (value) => {
  if (!(value instanceof Date) || Number.isNaN(value.getTime())) return "";
  return value.getFullYear() + "-" + PAD(value.getMonth() + 1) + "-" + PAD(value.getDate()) + "T" + PAD(value.getHours()) + ":" + PAD(value.getMinutes());
};

const parseDurationToSeconds = (value) => {
  const parts = String(value || "00:00:00").split(":").map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) {
    return 0;
  }
  const [hours, minutes, seconds] = parts;
  return hours * 3600 + minutes * 60 + seconds;
};

const buildShiftPercentages = (runtime, idle, breakdown) => {
  const runtimeSeconds = parseDurationToSeconds(runtime);
  const idleSeconds = parseDurationToSeconds(idle);
  const breakdownSeconds = parseDurationToSeconds(breakdown);
  const usedSeconds = Math.min(
    SHIFT_DURATION_SECONDS,
    runtimeSeconds + idleSeconds + breakdownSeconds,
  );
  const remainingSeconds = Math.max(SHIFT_DURATION_SECONDS - usedSeconds, 0);

  return {
    runtimePercentage: clamp((runtimeSeconds / SHIFT_DURATION_SECONDS) * 100),
    breakdownPercentage: clamp((breakdownSeconds / SHIFT_DURATION_SECONDS) * 100),
    idlePercentage: clamp((idleSeconds / SHIFT_DURATION_SECONDS) * 100),
    remainingPercentage: clamp((remainingSeconds / SHIFT_DURATION_SECONDS) * 100),
  };
};

const Report = () => {
  const now = new Date();
  const toLocalDate = (d) => {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  };
  const todayDate = toLocalDate(now);
  const startAtEight = `${todayDate}T08:00`;
  const nextDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  nextDate.setDate(nextDate.getDate() + 1);
  const endAtEight = `${toLocalDate(nextDate)}T08:00`;

  const [mode, setMode] = useState("daily");
  const [filters, setFilters] = useState({
    dateTime: todayDate,
    fromDateTime: startAtEight,
    toDateTime: endAtEight,
    shift: "All",
  });
  const [reportData, setReportData] = useState(null);

  const fetchReportData = async () => {
    try {
      const query = new URLSearchParams({
        mode,
        shift: filters.shift,
        dateTime: filters.dateTime,
        fromDateTime: filters.fromDateTime,
        toDateTime: filters.toDateTime,
      });

      const response = await fetch(`/api/report?${query.toString()}`);
      if (!response.ok) {
        return;
      }

      const data = await response.json();
      setReportData(data);
    } catch (error) {
      // Keep previous report snapshot if API is unavailable.
    }
  };

  useEffect(() => {
    fetchReportData();
    const interval = setInterval(fetchReportData, 3000);
    return () => clearInterval(interval);
  }, [mode, filters.dateTime, filters.fromDateTime, filters.toDateTime, filters.shift]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFilters((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const formatDisplayRange = (value) => {
    if (!value || typeof value !== "string" || !value.includes(" -> ")) {
      return value;
    }
    const [startRaw, endRaw] = value.split(" -> ");
    const formatOne = (raw) => {
      const dt = new Date(raw);
      if (Number.isNaN(dt.getTime())) return raw;
      return dt.toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      });
    };
    return `${formatOne(startRaw)} to ${formatOne(endRaw)}`;
  };

  const handleApplyFilter = async () => {
    fetchReportData();
  };

  const reportProgress = reportData
    ? buildShiftPercentages(reportData.runtime, reportData.idle, reportData.breakdown)
    : null;

  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-[#f4f7fb] p-2 sm:p-4 lg:p-6">
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-[#102a5c] sm:text-3xl">
          Consolidated Report
        </h1>
        <p className="mt-1 text-sm text-[#6d7b94]">
          Machine Runtime & Shift Analytics
        </p>
      </div>

      <RaisedCard className="mb-5 overflow-visible">
        <div className="p-3 sm:p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="text-[10px] uppercase tracking-[0.24em] text-[#6d7b94]">
                Report Filters
              </div>
              <div className="mt-1 text-xl font-bold text-[#102a5c] sm:text-2xl">
                Filter Configuration
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:flex">
              <button
                onClick={() => setMode("daily")}
                className={`rounded-xl px-4 py-2 text-sm font-semibold transition-all ${
                  mode === "daily"
                    ? "bg-[#102a5c] text-white"
                    : "bg-[#eef2f7] text-[#102a5c]"
                }`}
              >
                Daily Mode
              </button>

              <button
                onClick={() => setMode("custom")}
                className={`rounded-xl px-4 py-2 text-sm font-semibold transition-all ${
                  mode === "custom"
                    ? "bg-[#102a5c] text-white"
                    : "bg-[#eef2f7] text-[#102a5c]"
                }`}
              >
                Custom Mode
              </button>
            </div>
          </div>

          {mode === "daily" && (
            <div className="mt-5 grid grid-cols-1 gap-4">
                <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="min-w-0">
                <label className="mb-2 block text-sm font-semibold text-[#102a5c]">
                  Date
                </label>

                <div className="relative">
                  <CalendarDays
                    size={18}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-[#6d7b94]"
                  />

                  <input
                    type="date"
                    name="dateTime"
                    value={filters.dateTime}
                    onChange={handleChange}
                    className="w-full min-w-0 rounded-2xl border border-[#d7dee8] bg-white py-3 pl-11 pr-3 text-sm outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-[#102a5c]">
                  Select Shift
                </label>

                <select
                  name="shift"
                  value={filters.shift}
                  onChange={handleChange}
                  className="w-full rounded-2xl border border-[#d7dee8] bg-white px-4 py-3 text-sm outline-none"
                >
                  <option>All</option>
                  <option>Shift A</option>
                  <option>Shift B</option>
                  <option>Shift C</option>
                </select>
              </div>
</div>
              <button
                onClick={handleApplyFilter}
                className="flex w-full items-center justify-center gap-2 rounded-2xl bg-[#102a5c] px-5 py-3 text-sm font-semibold text-white transition-all"
              >
                <Filter size={18} />
                Apply Filter
              </button>
            </div>
          )}

          {mode === "custom" && (
            <div className="mt-5 grid grid-cols-1 gap-4 ">
                 <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4 ">
              <div className="rounded-2xl border border-[#dbe3ee] bg-[#f8fafc] p-4 ">
             
                <div className="mb-3 text-base font-bold text-[#102a5c] ">From</div>

                <label className="mb-2 block text-sm font-semibold text-[#102a5c]">
                  Date & Time
                </label>

                <div className="report-calendar-shell">
                  <CalendarDays size={16} className="report-calendar-icon" />
                  <DatePicker
                    selected={parseLocalDateTime(filters.fromDateTime)}
                    onChange={(date) => {
                      setFilters((prev) => ({
                        ...prev,
                        fromDateTime: formatLocalDateTime(date),
                      }));
                    }}
                    showTimeSelect
                    timeIntervals={1}
                    timeCaption="Time"
                    dateFormat="MM/dd/yyyy hh:mm aa"
                    className="report-datepicker-input"
                    calendarClassName="report-datepicker-calendar"
                    popperClassName="report-datepicker-popper"
                    wrapperClassName="report-datepicker-wrapper"
                  />
                  <Clock3 size={16} className="report-clock-icon" />
                </div>
              </div>

              <div className="rounded-2xl border border-[#dbe3ee] bg-[#f8fafc] p-4">
                <div className="mb-3 text-base font-bold text-[#102a5c]">To</div>

                <label className="mb-2 block text-sm font-semibold text-[#102a5c]">
                  Date & Time
                </label>

                <div className="report-calendar-shell">
                  <CalendarDays size={16} className="report-calendar-icon" />
                  <DatePicker
                    selected={parseLocalDateTime(filters.toDateTime)}
                    onChange={(date) => {
                      setFilters((prev) => ({
                        ...prev,
                        toDateTime: formatLocalDateTime(date),
                      }));
                    }}
                    showTimeSelect
                    timeIntervals={1}
                    timeCaption="Time"
                    dateFormat="MM/dd/yyyy hh:mm aa"
                    className="report-datepicker-input"
                    calendarClassName="report-datepicker-calendar"
                    popperClassName="report-datepicker-popper"
                    wrapperClassName="report-datepicker-wrapper"
                  />
                  <Clock3 size={16} className="report-clock-icon" />
                </div>
              </div>

</div>
              <button
                onClick={handleApplyFilter}
                className="flex w-full items-center justify-center gap-2 rounded-2xl bg-[#102a5c] px-5 py-3 text-sm font-semibold text-white transition-all"
              >
                <Filter size={18} />
                Apply Custom Filter
              </button>
            </div>
          )}
        </div>
      </RaisedCard>

      {reportData && (
        <div className="grid grid-cols-1 gap-4">
          <RaisedCard>
            <div className="p-3 sm:p-5">
              <div>
                <div className="text-[10px] uppercase tracking-[0.24em] text-[#6d7b94]">
                  Consolidated Overview
                </div>

                <div className="mt-1 text-xl font-bold text-[#102a5c] sm:text-2xl">
                  {mode === "daily"
                    ? "Per Day Report"
                    : "Custom Consolidated Report"}
                </div>

                <div className="mt-1 break-words text-xs text-[#6d7b94] sm:text-sm">
                  {formatDisplayRange(reportData.selectedDate)}
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  <div className="rounded-full bg-[#eef2f7] px-3 py-1 text-xs font-semibold text-[#102a5c]">
                    {filters.shift}
                  </div>
                </div>
              </div>

              <div className="mt-5">
                <div className="flex h-4 overflow-hidden rounded-full bg-[#dfe5ee]">
                  <div
                    className="bg-[#1ba34a]"
                    style={{
                      width: `${reportProgress?.runtimePercentage || 0}%`,
                    }}
                  />

                  <div
                    className="bg-[#ef4444]"
                    style={{
                      width: `${reportProgress?.breakdownPercentage || 0}%`,
                    }}
                  />

                  <div
                    className="bg-[#6082B6]"
                    style={{
                      width: `${reportProgress?.idlePercentage || 0}%`,
                    }}
                  />

                  <div
                    className="bg-[#DFE5EE]"
                    style={{
                      width: `${reportProgress?.remainingPercentage || 0}%`,
                    }}
                  />
                </div>

                <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  <div className="rounded-[18px] bg-[#edf9f0] p-4">
                    <div className="text-[10px] uppercase tracking-[0.18em] text-[#3c7a50]">
                      Runtime
                    </div>

                    <div className="mt-2 text-xl font-bold text-[#14923d] sm:text-2xl">
                      {reportData.runtime}
                    </div>
                  </div>

                  <div className="rounded-[18px] bg-[#fef0f0] p-4">
                    <div className="text-[10px] uppercase tracking-[0.18em] text-[#dc2626]">
                      Breakdown
                    </div>

                    <div className="mt-2 text-xl font-bold text-[#dc2626] sm:text-2xl">
                      {reportData.breakdown}
                    </div>
                  </div>

                  <div className="rounded-[18px] bg-[#f1f5f9] p-4">
                    <div className="text-[10px] uppercase tracking-[0.18em] text-[#64748b]">
                      Idle Time
                    </div>

                    <div className="mt-2 text-xl font-bold text-[#475569] sm:text-2xl">
                      {reportData.idle}
                    </div>
                  </div>
                  
                </div>
              </div>

              

              <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="rounded-[18px] bg-[#eef2f7] p-4">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-[#6d7b94]">
                    Parts Produced
                  </div>

                  <div className="mt-2 text-2xl font-bold text-[#102a5c] sm:text-3xl">
                    {reportData.parts}
                  </div>
                </div>

                <div className="rounded-[18px] bg-[#eef2f7] p-4">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-[#6d7b94]">
                    Power Consumption
                  </div>

                  <div className="mt-2 text-2xl font-bold text-[#102a5c] sm:text-3xl">
                    {reportData.power}
                  </div>
                </div>
              </div>
            </div>
          </RaisedCard>
                        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {/* ALARM LOGS */}
            <RaisedCard>
              <div className="p-3 sm:p-5">
                <div className="mb-4 flex items-center gap-2 text-[#102a43]">
                  <AlertTriangle size={18} />
                  <span className="font-semibold">
                    Alarm Logs
                  </span>
                </div>

             <div className="overflow-x-auto rounded-2xl border border-[#e2e8f0]">
                  <div className="max-h-[420px] overflow-y-auto">
                  <table className="min-w-full text-sm text-[#334155]">
                 <thead className="sticky top-0 z-10 bg-white">
                      <tr className="border-b border-[#dbe4f0] text-left text-[#64748b]">
                        <th className="border-r border-[#dbe4f0] p-3">Timestamp</th>
                        <th className="border-r border-[#dbe4f0] p-3">Alarm Code</th>
                        <th className="p-3">Message</th>
                      </tr>
                    </thead>

                    <tbody>
                      {(reportData.logs?.alarms || []).map(
                        (item, index) => (
                          <tr
                            key={index}
                            className="border-b border-[#eef2f7]"
                          >
                          <td className="border-r border-[#eef2f7] p-3">

                              {item.time}
                            </td>
                           <td className="border-r border-[#eef2f7] p-3 font-semibold">
                              {item.code}
                            </td>
                            <td className="p-3">
                              {item.message}
                            </td>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>
                </div>
                  </div>
              </div>
            </RaisedCard>

            {/* CYCLE LOGS */}
            <RaisedCard>
              <div className="p-3 sm:p-5">
                <div className="mb-4 flex items-center gap-2 text-[#102a43]">
                  <FileText size={18} />
                  <span className="font-semibold">
                    Cycle Logs
                  </span>
                </div>
<div className="overflow-x-auto rounded-2xl border border-[#e2e8f0]">
  <div className="max-h-[420px] overflow-y-auto">
                  <table className="min-w-full text-sm text-[#334155]">
                  <thead className="sticky top-0 z-10 bg-white">
                      <tr className="border-b border-[#dbe4f0] text-left text-[#64748b]">
                        <th className="border-r border-[#dbe4f0] p-3">Program</th>
                        <th className="border-r border-[#dbe4f0] p-3">Cycle Start</th>
                        <th className="border-r border-[#dbe4f0] p-3">Cycle End</th>
                        <th className="border-r border-[#dbe4f0] p-3">Cycle Time</th>
                        <th className="p-3">Parts</th>
                      </tr>
                    </thead>

                    <tbody>
                      {(reportData.logs?.cycles || []).map(
                        (item, index) => (
                          <tr
                            key={index}
                            className="border-b border-[#eef2f7]"
                          >
                           <td className="border-r border-[#eef2f7] p-3 font-semibold">

                              {item.program || "-"}
                            </td>
                            <td className="border-r border-[#eef2f7] p-3">
                              {item.start}
                            </td>
                            <td className="border-r border-[#eef2f7] p-3">
                              {item.end}
                            </td>
                            <td className="border-r border-[#eef2f7] p-3 font-semibold">
                              {item.cycle}
                            </td>
                            <td className="p-3 font-semibold">
                              {item.parts}
                            </td>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>
                </div>
                 </div>
              </div>
            </RaisedCard>
          </div>

          {/* MACHINE STATE */}
          <RaisedCard>
            <div className="p-3 sm:p-5">
              <div className="mb-4 flex items-center gap-2 text-[#102a43]">
                <Activity size={18} />
                <span className="font-semibold">
                  Machine State Logs
                </span>
              </div>
                          <div className="overflow-x-auto rounded-2xl border border-[#e2e8f0]">
                            <div className="max-h-[420px] overflow-y-auto">
                <table className="min-w-full text-sm text-[#334155]">
                <thead className="sticky top-0 z-10 bg-white">
                    <tr className="border-b border-[#dbe4f0] text-left text-[#64748b]">
                   <th className="border-r border-[#dbe4f0] p-3">Timestamp</th>
                      <th className="border-r border-[#dbe4f0] p-3">State</th>
                      <th className="p-3">Duration</th>
                  
                    </tr>
                  </thead>

                  <tbody>
                    {(reportData.logs?.machine || []).map(
                      (item, index) => (
                        <tr
                          key={index}
                          className="border-b border-[#eef2f7]"
                        >
                          <td className="p-3 border-r border-[#dbe4f0]">
                            {item.time}
                          </td>

                          <td
                            className={`p-3 border-r border-[#dbe4f0] font-semibold ${
                              item.state === "Downtime"
                                ? "text-red-500"
                                : "text-[#102a43]"
                            }`}
                          >
                            {item.state}
                          </td>

                          <td className="p-3">
                            {item.duration}
                          </td>

                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>
            </div>
               </div>
          </RaisedCard>
        </div>
      )}
    </div>
  );
};

export default Report;
