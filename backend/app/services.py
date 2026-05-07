from __future__ import annotations

import os
import random
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo


def _plant_tz():
    tz_name = os.getenv("PLANT_TZ", "Asia/Kolkata")
    try:
        return ZoneInfo(tz_name)
    except Exception:
        # Fallback for Windows environments without IANA tz database installed.
        return timezone(timedelta(hours=5, minutes=30))


def _to_hhmmss(total_seconds: int) -> str:
    if total_seconds < 0:
        total_seconds = 0
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _coerce_status(status: str) -> str:
    normalized = (status or "").strip().lower()
    mapping = {
        "running": "Running",
        "active": "Running",
        "idle": "Idle",
        "breakdown": "Breakdown",
        "break down": "Breakdown",
        "alarm": "Breakdown",
    }
    return mapping.get(normalized, "Running")


def _to_aware(iso_value: str | None, fallback: datetime) -> datetime:
    if not iso_value:
        return fallback
    try:
        dt = datetime.fromisoformat(iso_value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=fallback.tzinfo or _plant_tz())
        return dt
    except Exception:
        return fallback


def _parse_hhmm(value: str | None, default_hour: int, default_minute: int) -> time:
    if not value:
        return time(hour=default_hour, minute=default_minute)
    try:
        parsed = datetime.strptime(value, "%H:%M")
        return time(hour=parsed.hour, minute=parsed.minute)
    except Exception:
        return time(hour=default_hour, minute=default_minute)


def _iter_shift_configs(state: dict) -> list[dict[str, Any]]:
    shifts = state.get("settings", {}).get("shifts", [])
    fallback = [
        {"name": "Shift A", "start": "08:00", "end": "16:00"},
        {"name": "Shift B", "start": "16:00", "end": "00:00"},
        {"name": "Shift C", "start": "00:00", "end": "08:00"},
    ]

    configs = []
    source = shifts if shifts else fallback
    for idx, shift in enumerate(source):
        name = (shift.get("name") or f"Shift {idx + 1}").strip() or f"Shift {idx + 1}"
        start = _parse_hhmm(shift.get("start"), 8 if idx == 0 else (16 if idx == 1 else 0), 0)
        end = _parse_hhmm(shift.get("end"), 16 if idx == 0 else (0 if idx == 1 else 8), 0)
        configs.append({"name": name, "start": start, "end": end})

    return configs


def _shift_window_for_day(anchor_day: date, shift_cfg: dict[str, Any]) -> tuple[datetime, datetime]:
    start_t = shift_cfg["start"]
    end_t = shift_cfg["end"]

    tz = _plant_tz()
    start_dt = datetime.combine(anchor_day, start_t, tzinfo=tz)
    end_dt = datetime.combine(anchor_day, end_t, tzinfo=tz)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)

    return start_dt, end_dt


def _production_day_window(now: datetime, shift_configs: list[dict[str, Any]]) -> tuple[datetime, datetime]:
    if shift_configs:
        day_start_time = shift_configs[0]["start"]
    else:
        day_start_time = time(8, 0)

    day_start = datetime.combine(now.date(), day_start_time, tzinfo=now.tzinfo or _plant_tz())
    if now < day_start:
        day_start -= timedelta(days=1)
    return day_start, day_start + timedelta(days=1)


def _shift_window_in_production_day(
    production_start: datetime, shift_cfg: dict[str, Any]
) -> tuple[datetime, datetime]:
    production_end = production_start + timedelta(days=1)
    shift_start = datetime.combine(production_start.date(), shift_cfg["start"], tzinfo=production_start.tzinfo or _plant_tz())
    while shift_start < production_start:
        shift_start += timedelta(days=1)
    while shift_start >= production_end:
        shift_start -= timedelta(days=1)

    shift_end = datetime.combine(shift_start.date(), shift_cfg["end"], tzinfo=shift_start.tzinfo or _plant_tz())
    if shift_end <= shift_start:
        shift_end += timedelta(days=1)
    return shift_start, shift_end


def _resolve_effective_now(state: dict, fallback_now: datetime | None = None) -> datetime:
    now = fallback_now or datetime.now(_plant_tz())
    meta = state.get("meta", {})
    if meta.get("simClockMode") == "manual_shift":
        cursor = _to_aware(meta.get("simClockCursor"), now)
        return cursor
    return now


def _resolve_timeline_window(state: dict, real_now: datetime, elapsed_seconds: float) -> tuple[datetime, datetime]:
    meta = state.setdefault("meta", {})
    start_default = _to_aware(meta.get("lastTick"), real_now)
    start = start_default
    end = real_now

    if meta.get("simClockMode") != "manual_shift":
        return start, end

    shift_name = (meta.get("manualShiftName") or "Shift A").strip()
    shift_configs = _iter_shift_configs(state)
    target_shift = next((row for row in shift_configs if row["name"] == shift_name), None)
    if not target_shift:
        return start, end

    cursor = _to_aware(meta.get("simClockCursor"), real_now)
    candidates: list[tuple[datetime, datetime]] = []
    for day_offset in (-1, 0, 1):
        day = cursor.date() + timedelta(days=day_offset)
        candidates.append(_shift_window_for_day(day, target_shift))

    containing = [rng for rng in candidates if rng[0] <= cursor < rng[1]]
    if containing:
        shift_start, shift_end = containing[0]
    else:
        future_candidates = [rng for rng in candidates if rng[0] >= cursor]
        if future_candidates:
            shift_start, shift_end = min(future_candidates, key=lambda rng: (rng[0] - cursor).total_seconds())
        else:
            shift_start, shift_end = min(candidates, key=lambda rng: abs((rng[0] - cursor).total_seconds()))
    if cursor < shift_start or cursor >= shift_end:
        cursor = shift_start

    sim_start = cursor
    sim_end = sim_start + timedelta(seconds=elapsed_seconds)
    if sim_end > shift_end:
        sim_end = shift_start + (sim_end - shift_end)
    if sim_end <= sim_start:
        sim_end = sim_start + timedelta(seconds=max(0.1, elapsed_seconds))
    if sim_end > shift_end:
        sim_end = shift_end

    meta["simClockCursor"] = sim_end.isoformat()
    return sim_start, sim_end


def _record_timeline(
    meta: dict,
    start: datetime,
    end: datetime,
    status: str,
    parts_delta: int,
    power_wh: float,
    program: str,
    alarm_code: str,
    alarm_message: str,
) -> None:
    if end <= start:
        return

    timeline = meta.setdefault("statusTimeline", [])
    timeline.append(
        {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "status": _coerce_status(status),
            "partsDelta": int(max(0, parts_delta)),
            "powerWh": float(max(0.0, power_wh)),
            "program": (program or "").strip(),
            "alarmCode": alarm_code or "-",
            "alarmMessage": alarm_message or "No active alarm",
        }
    )

    cutoff = end - timedelta(days=8)
    trimmed = []
    for row in timeline[-600000:]:
        row_end = _to_aware(row.get("end"), cutoff)
        if row_end >= cutoff:
            trimmed.append(row)
    meta["statusTimeline"] = trimmed


def _summarize_timeline(timeline: list[dict[str, Any]], window_start: datetime, window_end: datetime) -> dict[str, float]:
    summary = {
        "runtimeSeconds": 0.0,
        "idleSeconds": 0.0,
        "breakdownSeconds": 0.0,
        "parts": 0.0,
        "powerWh": 0.0,
    }

    for row in timeline:
        seg_start = _to_aware(row.get("start"), window_start)
        seg_end = _to_aware(row.get("end"), window_start)
        if seg_end <= seg_start:
            continue
        if seg_end <= window_start or seg_start >= window_end:
            continue

        overlap_start = max(seg_start, window_start)
        overlap_end = min(seg_end, window_end)
        overlap_seconds = (overlap_end - overlap_start).total_seconds()
        if overlap_seconds <= 0:
            continue

        seg_seconds = (seg_end - seg_start).total_seconds()
        ratio = overlap_seconds / seg_seconds if seg_seconds > 0 else 0.0

        status = _coerce_status(row.get("status", "Running"))
        if status == "Running":
            summary["runtimeSeconds"] += overlap_seconds
        elif status == "Idle":
            summary["idleSeconds"] += overlap_seconds
        else:
            summary["breakdownSeconds"] += overlap_seconds

        summary["parts"] += max(0.0, float(row.get("partsDelta", 0))) * ratio
        summary["powerWh"] += max(0.0, float(row.get("powerWh", 0.0))) * ratio

    return summary


def _merge_summary(target: dict[str, float], part: dict[str, float]) -> None:
    for key in ("runtimeSeconds", "idleSeconds", "breakdownSeconds", "parts", "powerWh"):
        target[key] += part[key]


def _summary_payload(name: str, start_label: str, end_label: str, data: dict[str, float]) -> dict[str, Any]:
    runtime_seconds = int(round(data["runtimeSeconds"]))
    idle_seconds = int(round(data["idleSeconds"]))
    breakdown_seconds = int(round(data["breakdownSeconds"]))
    total_seconds_raw = runtime_seconds + idle_seconds + breakdown_seconds
    if total_seconds_raw <= 0:
        runtime_percentage = 0
        idle_percentage = 0
        breakdown_percentage = 0
    else:
        runtime_percentage = int(round((runtime_seconds / total_seconds_raw) * 100))
        idle_percentage = int(round((idle_seconds / total_seconds_raw) * 100))
        breakdown_percentage = max(0, 100 - runtime_percentage - idle_percentage)

    return {
        "name": name,
        "start": start_label,
        "end": end_label,
        "runtime": _to_hhmmss(runtime_seconds),
        "idle": _to_hhmmss(idle_seconds),
        "breakdown": _to_hhmmss(breakdown_seconds),
        "runtimePercentage": runtime_percentage,
        "idlePercentage": idle_percentage,
        "breakdownPercentage": breakdown_percentage,
        "parts": int(round(data["parts"])),
        "power": f"{(data['powerWh'] / 1000.0):.3f} kWh",
    }


def _remaining_time_label(now: datetime, shift_start: datetime, shift_end: datetime) -> str:
    if now < shift_start:
        remaining = shift_end - shift_start
    elif now >= shift_end:
        remaining = timedelta(0)
    else:
        remaining = shift_end - now
    return _to_hhmmss(int(max(0, remaining.total_seconds())))


def _build_shift_summaries(state: dict, reference_dt: datetime | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    machine = state["machine"]
    meta = state.get("meta", {})
    timeline = meta.get("statusTimeline", [])
    now = reference_dt or datetime.now(timezone.utc)

    shift_configs = _iter_shift_configs(state)
    production_start, production_end = _production_day_window(now, shift_configs)

    shift_summaries: list[dict[str, Any]] = []
    consolidated = _summarize_timeline(timeline, production_start, min(now, production_end))

    for shift_cfg in shift_configs:
        start_dt, end_dt = _shift_window_in_production_day(production_start, shift_cfg)
        shift_data = _summarize_timeline(timeline, start_dt, min(now, end_dt, production_end))

        shift_payload = _summary_payload(
            shift_cfg["name"],
            shift_cfg["start"].strftime("%H:%M"),
            shift_cfg["end"].strftime("%H:%M"),
            shift_data,
        )
        shift_payload["remainingTime"] = _remaining_time_label(now, start_dt, end_dt)
        shift_summaries.append(shift_payload)

    if not timeline:
        fallback = {
            "runtimeSeconds": float(machine.get("cuttingTimeSeconds", 0)),
            "idleSeconds": float(machine.get("idleTimeSeconds", 0)),
            "breakdownSeconds": float(machine.get("breakdownTimeSeconds", 0)),
            "parts": float(machine.get("totalParts", 0)),
            "powerWh": float(max(0, int(machine.get("spindleSpeed", 0) / 40))),
        }
        consolidated = fallback

    consolidated_summary = _summary_payload(
        "Per Day",
        production_start.strftime("%H:%M"),
        (production_end - timedelta(minutes=1)).strftime("%H:%M"),
        consolidated,
    )
    consolidated_summary["remainingTime"] = _remaining_time_label(now, production_start, production_end)
    return shift_summaries, consolidated_summary


def _compute_report_summary(
    state: dict,
    mode: str,
    shift: str,
    from_dt: str | None,
    to_dt: str | None,
    date_time: str | None,
) -> dict[str, Any]:
    now = _resolve_effective_now(state, datetime.now(timezone.utc))
    shift_configs = _iter_shift_configs(state)
    timeline = state.get("meta", {}).get("statusTimeline", [])

    if mode == "custom":
        range_start = _to_aware(from_dt, now - timedelta(hours=8))
        range_end = _to_aware(to_dt, now)
        if range_end <= range_start:
            range_end = range_start + timedelta(days=1)
    else:
        anchor = _to_aware(date_time, now)
        if date_time and len(date_time) <= 10:
            range_start = datetime.combine(anchor.date(), time(0, 0), tzinfo=_plant_tz())
            range_end = range_start + timedelta(days=1)
        else:
            range_start, range_end = _production_day_window(anchor, shift_configs)

    if range_end <= range_start:
        range_end = range_start + timedelta(minutes=1)

    summary = {
        "runtimeSeconds": 0.0,
        "idleSeconds": 0.0,
        "breakdownSeconds": 0.0,
        "parts": 0.0,
        "powerWh": 0.0,
    }

    if shift != "All":
        target_shift = next((row for row in shift_configs if row["name"] == shift), None)
        if target_shift:
            day = range_start.date() - timedelta(days=1)
            while day <= range_end.date() + timedelta(days=1):
                shift_start, shift_end = _shift_window_for_day(day, target_shift)
                if shift_end <= range_start or shift_start >= range_end:
                    day += timedelta(days=1)
                    continue
                part = _summarize_timeline(
                    timeline,
                    max(range_start, shift_start),
                    min(range_end, shift_end),
                )
                _merge_summary(summary, part)
                day += timedelta(days=1)
        else:
            summary = _summarize_timeline(timeline, range_start, range_end)
    else:
        summary = _summarize_timeline(timeline, range_start, range_end)

    return {
        "summary": summary,
        "selectedDate": f"{range_start.isoformat()} -> {range_end.isoformat()}",
        "rangeStart": range_start,
        "rangeEnd": range_end,
    }


def _format_log_time(dt: datetime) -> str:
    local_dt = dt.astimezone(_plant_tz()) if dt.tzinfo else dt
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")


def _report_log_windows(
    shift_configs: list[dict[str, Any]],
    shift: str,
    range_start: datetime,
    range_end: datetime,
) -> list[tuple[datetime, datetime]]:
    if shift == "All":
        return [(range_start, range_end)]

    target_shift = next((row for row in shift_configs if row["name"] == shift), None)
    if not target_shift:
        return [(range_start, range_end)]

    windows: list[tuple[datetime, datetime]] = []
    day = range_start.date() - timedelta(days=1)
    while day <= range_end.date() + timedelta(days=1):
        shift_start, shift_end = _shift_window_for_day(day, target_shift)
        overlap_start = max(range_start, shift_start)
        overlap_end = min(range_end, shift_end)
        if overlap_end > overlap_start:
            windows.append((overlap_start, overlap_end))
        day += timedelta(days=1)
    return windows


def _build_report_logs(state: dict, shift: str, range_start: datetime, range_end: datetime) -> dict[str, list[dict[str, Any]]]:
    timeline = state.get("meta", {}).get("statusTimeline", [])
    machine = state.get("machine", {})
    shift_configs = _iter_shift_configs(state)
    windows = _report_log_windows(shift_configs, shift, range_start, range_end)
    rows: list[dict[str, Any]] = []
    for row in timeline[-400:]:
        seg_start = _to_aware(row.get("start"), range_start)
        seg_end = _to_aware(row.get("end"), range_start)
        if seg_end <= seg_start:
            continue
        for win_start, win_end in windows:
            if seg_end <= win_start or seg_start >= win_end:
                continue

            overlap_start = max(seg_start, win_start)
            overlap_end = min(seg_end, win_end)
            duration_seconds = int(max(0, (overlap_end - overlap_start).total_seconds()))
            rows.append(
                {
                    "status": _coerce_status(row.get("status", "Running")),
                    "start": overlap_start,
                    "end": overlap_end,
                    "duration": _to_hhmmss(duration_seconds),
                    "parts": int(max(0, round(float(row.get("partsDelta", 0))))),
                    "program": (row.get("program") or "").strip() or machine.get("currentProgram", "PROGRAM-001"),
                    "alarmCode": row.get("alarmCode", machine.get("alarmCode", "-")) or "-",
                    "alarmMessage": row.get("alarmMessage", machine.get("alarmMessage", "No active alarm"))
                    or "No active alarm",
                }
            )

    rows.sort(key=lambda item: item["start"])

    # Merge contiguous slices that represent the same logical state.
    merged: list[dict[str, Any]] = []
    for row in rows:
        if not merged:
            merged.append(dict(row))
            continue

        prev = merged[-1]
        is_contiguous = row["start"] <= prev["end"]
        same_key = (
            prev["status"] == row["status"]
            and prev["program"] == row["program"]
            and prev["alarmCode"] == row["alarmCode"]
        )

        if is_contiguous and same_key:
            prev["end"] = max(prev["end"], row["end"])
            prev["parts"] += row["parts"]
            continue

        merged.append(dict(row))

    alarms: list[dict[str, Any]] = []
    cycles: list[dict[str, Any]] = []
    machine_states: list[dict[str, Any]] = []

    # Machine state logs: only when state changes, duration until next state change.
    merged_state: list[dict[str, Any]] = []
    for row in merged:
        if not merged_state:
            merged_state.append(dict(row))
            continue
        prev = merged_state[-1]
        if row["status"] == prev["status"] and row["start"] <= prev["end"]:
            prev["end"] = max(prev["end"], row["end"])
            continue
        merged_state.append(dict(row))

    for idx, row in enumerate(merged_state):
        next_start = merged_state[idx + 1]["start"] if idx + 1 < len(merged_state) else row["end"]
        duration_seconds = int(max(0, (next_start - row["start"]).total_seconds()))
        machine_states.append(
            {
                "time": _format_log_time(row["start"]),
                "state": "Downtime" if row["status"] == "Breakdown" else row["status"],
                "duration": _to_hhmmss(duration_seconds),
            }
        )

    # Alarm logs: only when alarm starts or alarm code changes.
    prev_breakdown = False
    prev_alarm_code = "-"
    for row in merged:
        if row["status"] != "Breakdown":
            prev_breakdown = False
            prev_alarm_code = "-"
            continue

        alarm_code = row["alarmCode"] or "-"
        if (not prev_breakdown) or (alarm_code != prev_alarm_code):
            alarms.append(
                {
                    "time": _format_log_time(row["start"]),
                    "code": alarm_code,
                    "message": row["alarmMessage"] or "Breakdown detected",
                }
            )
        prev_breakdown = True
        prev_alarm_code = alarm_code

    # Cycle logs: one cycle per running block of a program (new cycle when program changes).
    active_cycle: dict[str, Any] | None = None
    for row in merged:
        if row["status"] != "Running":
            if active_cycle:
                duration_seconds = int(max(0, (active_cycle["end"] - active_cycle["start"]).total_seconds()))
                cycles.append(
                    {
                        "program": active_cycle["program"],
                        "start": _format_log_time(active_cycle["start"]),
                        "end": _format_log_time(active_cycle["end"]),
                        "cycle": _to_hhmmss(duration_seconds),
                        "parts": int(active_cycle["parts"]),
                    }
                )
                active_cycle = None
            continue

        if not active_cycle:
            active_cycle = {
                "program": row["program"],
                "start": row["start"],
                "end": row["end"],
                "parts": row["parts"],
            }
            continue

        if row["program"] == active_cycle["program"] and row["start"] <= active_cycle["end"]:
            active_cycle["end"] = max(active_cycle["end"], row["end"])
            active_cycle["parts"] += row["parts"]
            continue

        duration_seconds = int(max(0, (active_cycle["end"] - active_cycle["start"]).total_seconds()))
        cycles.append(
            {
                "program": active_cycle["program"],
                "start": _format_log_time(active_cycle["start"]),
                "end": _format_log_time(active_cycle["end"]),
                "cycle": _to_hhmmss(duration_seconds),
                "parts": int(active_cycle["parts"]),
            }
        )
        active_cycle = {
            "program": row["program"],
            "start": row["start"],
            "end": row["end"],
            "parts": row["parts"],
        }

    if active_cycle:
        duration_seconds = int(max(0, (active_cycle["end"] - active_cycle["start"]).total_seconds()))
        cycles.append(
            {
                "program": active_cycle["program"],
                "start": _format_log_time(active_cycle["start"]),
                "end": _format_log_time(active_cycle["end"]),
                "cycle": _to_hhmmss(duration_seconds),
                "parts": int(active_cycle["parts"]),
            }
        )

    return {
        "alarms": list(reversed(alarms[-25:])),
        "cycles": list(reversed(cycles[-25:])),
        "machine": list(reversed(machine_states[-50:])),
    }


def _tick_machine(state: dict) -> None:
    machine = state["machine"]
    meta = state["meta"]

    real_now = datetime.now(timezone.utc)
    last_tick = _to_aware(meta.get("lastTick"), real_now)

    elapsed = max(0.0, min((real_now - last_tick).total_seconds(), 5.0))
    sim_speed = float(meta.get("simSpeed", 1.0))
    scaled_elapsed = elapsed * sim_speed
    timeline_start, timeline_end = _resolve_timeline_window(state, real_now, scaled_elapsed)
    display_now = timeline_end if meta.get("simClockMode") == "manual_shift" else real_now

    status = _coerce_status(machine.get("machineStatus", "Running"))
    machine["machineStatus"] = status

    parts_before = int(machine.get("totalParts", 0))
    spindle_before = int(machine.get("spindleSpeed", 0))

    if status == "Running":
        machine["cuttingTimeSeconds"] = int(machine.get("cuttingTimeSeconds", 0) + scaled_elapsed)
        interval_seconds = float(machine.get("partIntervalSeconds", 60) or 60)
        interval_seconds = max(1.0, interval_seconds)
        part_accumulator = float(meta.get("partAccumulatorSeconds", 0.0)) + scaled_elapsed
        produced_parts = int(part_accumulator // interval_seconds)
        if produced_parts > 0:
            machine["totalParts"] = int(machine.get("totalParts", 0) + produced_parts)
            part_accumulator -= produced_parts * interval_seconds
        meta["partAccumulatorSeconds"] = part_accumulator
        machine["spindleSpeed"] = int(max(1200, min(5500, machine.get("spindleSpeed", 3200) + random.randint(-80, 110))))
        machine["feedRate"] = int(max(20, min(100, machine.get("feedRate", 40) + random.randint(-2, 3))))
        machine["cuttingStatus"] = "CUTTING"
        if not machine.get("alarmActive"):
            machine["alarmCode"] = "-"
            machine["alarmMessage"] = "No active alarm"
            machine["alarmTime"] = "--:--:--"

    elif status == "Idle":
        machine["idleTimeSeconds"] = int(machine.get("idleTimeSeconds", 0) + scaled_elapsed)
        machine["spindleSpeed"] = int(max(0, min(800, machine.get("spindleSpeed", 300) + random.randint(-60, 40))))
        machine["feedRate"] = int(max(0, min(10, machine.get("feedRate", 3) + random.randint(-1, 1))))
        machine["cuttingStatus"] = "IDLE"
        machine["alarmActive"] = False
        machine["alarmCode"] = "-"
        machine["alarmMessage"] = "No active alarm"
        machine["alarmTime"] = "--:--:--"

    else:
        machine["breakdownTimeSeconds"] = int(machine.get("breakdownTimeSeconds", 0) + scaled_elapsed)
        machine["spindleSpeed"] = 0
        machine["feedRate"] = 0
        machine["cuttingStatus"] = "STOPPED"
        machine["alarmActive"] = True
        if machine.get("alarmCode", "-") in {"", "-"}:
            machine["alarmCode"] = "T0125"
        if machine.get("alarmMessage", "") in {"", "No active alarm"}:
            machine["alarmMessage"] = "SPINDLE OVERLOAD DETECTED"
        machine["alarmTime"] = display_now.strftime("%H:%M:%S")

    coords = machine.get("coordinates", {})
    jitter = 0.01 if status == "Idle" else (0.04 if status == "Running" else 0.0)
    coords["x"] = round(float(coords.get("x", 0.0)) + random.uniform(-jitter, jitter), 2)
    coords["y"] = round(float(coords.get("y", 0.0)) + random.uniform(-jitter, jitter), 2)
    coords["z"] = round(float(coords.get("z", 0.0)) + random.uniform(-jitter, jitter), 2)
    machine["coordinates"] = coords

    machine["feedOutput"] = int(max(0, machine.get("feedRate", 0) * 20 + random.randint(-50, 50)))
    machine["feedOverride"] = int(max(0, min(120, machine.get("feedOverride", 95) + random.randint(-1, 1))))

    time_label = display_now.strftime("%H:%M:%S")
    spindle_load = int(max(0, min(100, round(machine["spindleSpeed"] / 55 + random.uniform(-6, 6)))))

    spindle_series = machine.setdefault("spindleLoadData", [])
    feed_series = machine.setdefault("feedRateData", [])

    spindle_series.append({"time": time_label, "load": spindle_load})
    feed_series.append({"time": time_label, "rate": int(machine["feedOutput"])})

    machine["spindleLoadData"] = spindle_series[-60:]
    machine["feedRateData"] = feed_series[-60:]

    parts_after = int(machine.get("totalParts", 0))
    parts_delta = max(0, parts_after - parts_before)
    avg_spindle = (spindle_before + int(machine.get("spindleSpeed", 0))) / 2.0
    est_power_watts = max(0.0, avg_spindle * 0.03 + float(machine.get("feedRate", 0)) * 2.5)
    power_wh = est_power_watts * scaled_elapsed / 3600.0

    _record_timeline(
        meta,
        timeline_start,
        timeline_end,
        status,
        parts_delta,
        power_wh,
        machine.get("currentProgram", "PROGRAM-001"),
        machine.get("alarmCode", "-"),
        machine.get("alarmMessage", "No active alarm"),
    )
    meta["lastTick"] = real_now.isoformat()


def build_dashboard_payload(state: dict) -> dict:
    machine = state["machine"]
    shift_summaries, consolidated_summary = _build_shift_summaries(state, _resolve_effective_now(state))

    return {
        "machineStatus": machine.get("machineStatus", "Running"),
        "controllerMode": machine.get("controllerMode", "AUTO"),
        "currentProgram": machine.get("currentProgram", "PROGRAM-001"),
        "currentTool": machine.get("currentTool", "#08"),
        "totalParts": int(machine.get("totalParts", 0)),
        "cuttingStatus": machine.get("cuttingStatus", "CUTTING"),
        "coordinates": machine.get("coordinates", {"x": 0.0, "y": 0.0, "z": 0.0}),
        "spindleSpeed": int(machine.get("spindleSpeed", 0)),
        "feedRate": int(machine.get("feedRate", 0)),
        "feedOutput": int(machine.get("feedOutput", 0)),
        "feedOverride": int(machine.get("feedOverride", 0)),
        "alarmActive": bool(machine.get("alarmActive", False)),
        "alarmCode": machine.get("alarmCode", "-"),
        "alarmMessage": machine.get("alarmMessage", "No active alarm"),
        "alarmTime": machine.get("alarmTime", "--:--:--"),
        "spindleLoadData": machine.get("spindleLoadData", []),
        "feedRateData": machine.get("feedRateData", []),
        "cuttingTime": _to_hhmmss(int(machine.get("cuttingTimeSeconds", 0))),
        "idleTime": _to_hhmmss(int(machine.get("idleTimeSeconds", 0))),
        "breakdownTime": _to_hhmmss(int(machine.get("breakdownTimeSeconds", 0))),
        "shiftSummaries": shift_summaries,
        "consolidatedSummary": consolidated_summary,
    }


def build_analytics_payload(state: dict) -> dict:
    machine = state["machine"]
    spindle = machine.get("spindleLoadData", [])[-10:]
    feed = machine.get("feedRateData", [])[-10:]

    if not spindle:
        spindle = [{"time": "00:00:00", "load": 0}]
    if not feed:
        feed = [{"time": "00:00:00", "rate": 0}]

    spindle_load_data = [{"date": row["time"], "load": row["load"]} for row in spindle]
    feed_rate_data = [{"date": row["time"], "rate": row["rate"]} for row in feed]

    spindle_speed_data = [
        {"date": row["time"], "speed": int(max(0, row["load"] * 55 + random.randint(-100, 120)))}
        for row in spindle
    ]

    cycle_time_data = [
        {
            "date": row["time"],
            "avg": int(max(12, 30 - row["load"] / 8 + random.randint(-1, 2))),
            "max": int(max(16, 36 - row["load"] / 9 + random.randint(0, 4))),
        }
        for row in spindle
    ]

    parts_base = int(machine.get("totalParts", 0))
    parts_data = []
    for idx, row in enumerate(spindle):
        parts_data.append(
            {
                "date": row["time"],
                "parts": max(0, 35 + int(row["load"] / 2) + idx * 2 + random.randint(-4, 5)),
            }
        )

    cutting = int(machine.get("cuttingTimeSeconds", 0))
    idle = int(machine.get("idleTimeSeconds", 0))
    breakdown = int(machine.get("breakdownTimeSeconds", 0))
    total = max(1, cutting + idle + breakdown)
    utilization = int((cutting / total) * 100)

    utilization_data = []
    for row in spindle[-10:]:
        utilization_data.append(
            {
                "date": row["time"],
                "utilization": max(10, min(98, utilization + random.randint(-6, 6))),
                "target": 80,
            }
        )

    idle_pct = int((idle / total) * 100)
    running_pct = max(0, min(100, 100 - idle_pct))

    alarm_distribution = [
        {"type": "Overheat", "count": 48 if machine.get("alarmActive") else 12},
        {"type": "Low Air Pressure", "count": 38},
        {"type": "Axis Fault", "count": 28},
        {"type": "Power Failure", "count": 18},
        {"type": "Other", "count": 8},
    ]

    return {
        "spindleLoadData": spindle_load_data,
        "feedRateData": feed_rate_data,
        "spindleSpeedData": spindle_speed_data,
        "cycleTimeData": cycle_time_data,
        "partsProducedData": parts_data,
        "machineUtilizationData": utilization_data,
        "downtimeData": [
            {"name": "Running", "value": running_pct},
            {"name": "Idle", "value": idle_pct},
        ],
        "alarmDistributionData": alarm_distribution,
        "kpi": {
            "totalParts": parts_base,
            "utilization": utilization,
            "currentStatus": machine.get("machineStatus", "Running"),
        },
    }


def build_report_payload(state: dict, mode: str, shift: str, from_dt: str | None, to_dt: str | None, date_time: str | None) -> dict:
    machine = state["machine"]
    report_data = _compute_report_summary(state, mode, shift, from_dt, to_dt, date_time)
    summary = report_data["summary"]

    runtime_seconds = int(round(summary["runtimeSeconds"]))
    idle_seconds = int(round(summary["idleSeconds"]))
    breakdown_seconds = int(round(summary["breakdownSeconds"]))
    total_seconds = max(1, runtime_seconds + idle_seconds + breakdown_seconds)

    runtime_pct = int(round((runtime_seconds / total_seconds) * 100))
    idle_pct = int(round((idle_seconds / total_seconds) * 100))
    breakdown_pct = max(0, 100 - runtime_pct - idle_pct)

    logs = _build_report_logs(state, shift, report_data["rangeStart"], report_data["rangeEnd"])

    return {
        "runtime": _to_hhmmss(runtime_seconds),
        "idle": _to_hhmmss(idle_seconds),
        "breakdown": _to_hhmmss(breakdown_seconds),
        "parts": int(round(summary["parts"])),
        "power": f"{(summary['powerWh'] / 1000.0):.3f} kWh",
        "runtimePercentage": runtime_pct,
        "idlePercentage": idle_pct,
        "breakdownPercentage": breakdown_pct,
        "selectedDate": report_data["selectedDate"],
        "machineStatus": machine.get("machineStatus", "Running"),
        "logs": logs,
    }


def merge_machine_patch(machine: dict, patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if key == "coordinates" and isinstance(value, dict):
            machine.setdefault("coordinates", {}).update(value)
        elif key in {"spindleLoadData", "feedRateData"} and isinstance(value, list):
            machine[key] = value
        else:
            machine[key] = value

    machine["machineStatus"] = _coerce_status(machine.get("machineStatus", "Running"))


def tick(state: dict) -> None:
    _tick_machine(state)
