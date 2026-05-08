from __future__ import annotations

import json
import os
import sqlite3
import threading
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from .defaults import initial_state
except ImportError:
    from defaults import initial_state

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_DEFAULT_DB_FILE = _BACKEND_DIR / "app" / "live_state.db"
DB_FILE = Path(os.getenv("LIVE_DB_FILE", str(_DEFAULT_DB_FILE)))
LEGACY_STATE_FILE = Path(os.getenv("LIVE_STATE_FILE", str(_BACKEND_DIR / "simulator" / "live_state.json")))
LOG_RETENTION_DAYS = int(os.getenv("LIVE_LOG_RETENTION_DAYS", "31"))
PRUNE_INTERVAL_SECONDS = int(os.getenv("LIVE_PRUNE_INTERVAL_SECONDS", "600"))
_LOCK = threading.Lock()


def _connect() -> sqlite3.Connection:
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS app_state;

        CREATE TABLE IF NOT EXISTS machine_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            machine_status TEXT,
            controller_mode TEXT,
            current_program TEXT,
            current_tool TEXT,
            total_parts INTEGER,
            cutting_status TEXT,
            coord_x REAL,
            coord_y REAL,
            coord_z REAL,
            spindle_speed INTEGER,
            feed_rate INTEGER,
            feed_output INTEGER,
            feed_override INTEGER,
            part_interval_seconds INTEGER,
            alarm_active INTEGER,
            alarm_code TEXT,
            alarm_message TEXT,
            alarm_time TEXT,
            cutting_time_seconds INTEGER,
            idle_time_seconds INTEGER,
            breakdown_time_seconds INTEGER,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS machine_series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_type TEXT NOT NULL,
            point_index INTEGER NOT NULL,
            time_label TEXT NOT NULL,
            value REAL NOT NULL,
            UNIQUE(series_type, point_index)
        );

        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            is_connected INTEGER NOT NULL DEFAULT 0,
            modbus_ip TEXT,
            modbus_port TEXT,
            modbus_slave_id TEXT,
            modbus_fetch_rate TEXT,
            modbus_graph_rate TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            saved INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS meta (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_tick TEXT,
            sim_speed REAL NOT NULL DEFAULT 1.0,
            sim_clock_mode TEXT NOT NULL DEFAULT 'auto',
            manual_shift_name TEXT NOT NULL DEFAULT 'Shift A',
            sim_clock_cursor TEXT,
            part_accumulator_seconds REAL NOT NULL DEFAULT 0.0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS status_timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            status TEXT NOT NULL,
            parts_delta INTEGER NOT NULL DEFAULT 0,
            power_wh REAL NOT NULL DEFAULT 0.0,
            program TEXT NOT NULL DEFAULT '',
            alarm_code TEXT NOT NULL DEFAULT '-',
            alarm_message TEXT NOT NULL DEFAULT 'No active alarm'
        );

        CREATE TABLE IF NOT EXISTS machine_state_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_time TEXT NOT NULL,
            from_state TEXT NOT NULL,
            to_state TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS alarm_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_time TEXT NOT NULL,
            alarm_code TEXT NOT NULL,
            alarm_message TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cycle_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            cycle_seconds INTEGER NOT NULL DEFAULT 0,
            parts INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_machine_state_log_event_time ON machine_state_log(event_time);
        CREATE INDEX IF NOT EXISTS idx_alarm_log_event_time ON alarm_log(event_time);
        CREATE INDEX IF NOT EXISTS idx_cycle_log_start_end ON cycle_log(start_time, end_time);
        """
    )
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(machine_state)").fetchall()}
    if "part_interval_seconds" not in cols:
        conn.execute("ALTER TABLE machine_state ADD COLUMN part_interval_seconds INTEGER")
    meta_cols = {row["name"] for row in conn.execute("PRAGMA table_info(meta)").fetchall()}
    if "part_accumulator_seconds" not in meta_cols:
        conn.execute("ALTER TABLE meta ADD COLUMN part_accumulator_seconds REAL NOT NULL DEFAULT 0.0")
    if "active_cycle_start" not in meta_cols:
        conn.execute("ALTER TABLE meta ADD COLUMN active_cycle_start TEXT")
    if "active_cycle_program" not in meta_cols:
        conn.execute("ALTER TABLE meta ADD COLUMN active_cycle_program TEXT")
    if "active_cycle_parts" not in meta_cols:
        conn.execute("ALTER TABLE meta ADD COLUMN active_cycle_parts INTEGER NOT NULL DEFAULT 0")
    conn.commit()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _seconds_between(start_iso: str | None, end_iso: str | None) -> int:
    start = _parse_iso(start_iso)
    end = _parse_iso(end_iso)
    if not start or not end or end <= start:
        return 0
    return int((end - start).total_seconds())


def _upsert_machine(conn: sqlite3.Connection, machine: dict) -> None:
    coords = machine.get("coordinates", {})
    conn.execute(
        """
        INSERT INTO machine_state (
            id, machine_status, controller_mode, current_program, current_tool, total_parts,
            cutting_status, coord_x, coord_y, coord_z, spindle_speed, feed_rate, feed_output,
            feed_override, part_interval_seconds, alarm_active, alarm_code, alarm_message, alarm_time, cutting_time_seconds,
            idle_time_seconds, breakdown_time_seconds, updated_at
        ) VALUES (
            1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now')
        )
        ON CONFLICT(id) DO UPDATE SET
            machine_status = excluded.machine_status,
            controller_mode = excluded.controller_mode,
            current_program = excluded.current_program,
            current_tool = excluded.current_tool,
            total_parts = excluded.total_parts,
            cutting_status = excluded.cutting_status,
            coord_x = excluded.coord_x,
            coord_y = excluded.coord_y,
            coord_z = excluded.coord_z,
            spindle_speed = excluded.spindle_speed,
            feed_rate = excluded.feed_rate,
            feed_output = excluded.feed_output,
            feed_override = excluded.feed_override,
            part_interval_seconds = excluded.part_interval_seconds,
            alarm_active = excluded.alarm_active,
            alarm_code = excluded.alarm_code,
            alarm_message = excluded.alarm_message,
            alarm_time = excluded.alarm_time,
            cutting_time_seconds = excluded.cutting_time_seconds,
            idle_time_seconds = excluded.idle_time_seconds,
            breakdown_time_seconds = excluded.breakdown_time_seconds,
            updated_at = excluded.updated_at
        """,
        (
            machine.get("machineStatus", "Running"),
            machine.get("controllerMode", "AUTO"),
            machine.get("currentProgram", "PROGRAM-001"),
            machine.get("currentTool", "#08"),
            int(machine.get("totalParts", 0)),
            machine.get("cuttingStatus", "CUTTING"),
            float(coords.get("x", 0.0)),
            float(coords.get("y", 0.0)),
            float(coords.get("z", 0.0)),
            int(machine.get("spindleSpeed", 0)),
            int(machine.get("feedRate", 0)),
            int(machine.get("feedOutput", 0)),
            int(machine.get("feedOverride", 0)),
            int(machine.get("partIntervalSeconds", 60) or 60),
            1 if bool(machine.get("alarmActive", False)) else 0,
            machine.get("alarmCode", "-"),
            machine.get("alarmMessage", "No active alarm"),
            machine.get("alarmTime", "--:--:--"),
            int(machine.get("cuttingTimeSeconds", 0)),
            int(machine.get("idleTimeSeconds", 0)),
            int(machine.get("breakdownTimeSeconds", 0)),
        ),
    )


def _replace_series(conn: sqlite3.Connection, series_type: str, data: list[dict], value_key: str) -> None:
    # Upsert fixed-size time-series points to avoid delete/reinsert write amplification.
    for idx, row in enumerate(data):
        conn.execute(
            """
            INSERT INTO machine_series (series_type, point_index, time_label, value)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(series_type, point_index) DO UPDATE SET
                time_label = excluded.time_label,
                value = excluded.value
            """,
            (
                series_type,
                idx,
                str(row.get("time", "00:00:00")),
                float(row.get(value_key, 0.0)),
            ),
        )
    conn.execute(
        "DELETE FROM machine_series WHERE series_type = ? AND point_index >= ?",
        (series_type, len(data)),
    )


def _upsert_settings(conn: sqlite3.Connection, settings: dict) -> None:
    modbus = settings.get("modbusSettings", {})
    conn.execute(
        """
        INSERT INTO settings (
            id, is_connected, modbus_ip, modbus_port, modbus_slave_id, modbus_fetch_rate, modbus_graph_rate, updated_at
        ) VALUES (1, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(id) DO UPDATE SET
            is_connected = excluded.is_connected,
            modbus_ip = excluded.modbus_ip,
            modbus_port = excluded.modbus_port,
            modbus_slave_id = excluded.modbus_slave_id,
            modbus_fetch_rate = excluded.modbus_fetch_rate,
            modbus_graph_rate = excluded.modbus_graph_rate,
            updated_at = excluded.updated_at
        """,
        (
            1 if bool(settings.get("isConnected", False)) else 0,
            modbus.get("ip", "127.0.0.1"),
            modbus.get("port", "1502"),
            modbus.get("slaveId", "1"),
            modbus.get("fetchRate", "5s"),
            modbus.get("graphRate", "10s"),
        ),
    )

    conn.execute("DELETE FROM shifts")
    for shift in settings.get("shifts", []):
        conn.execute(
            "INSERT INTO shifts (id, name, start_time, end_time, saved) VALUES (?, ?, ?, ?, ?)",
            (
                int(shift.get("id", 0)),
                str(shift.get("name", "Shift")),
                str(shift.get("start", "00:00")),
                str(shift.get("end", "00:00")),
                1 if bool(shift.get("saved", False)) else 0,
            ),
        )


def _upsert_meta(conn: sqlite3.Connection, meta: dict) -> None:
    conn.execute(
        """
        INSERT INTO meta (
            id, last_tick, sim_speed, sim_clock_mode, manual_shift_name, sim_clock_cursor, part_accumulator_seconds,
            active_cycle_start, active_cycle_program, active_cycle_parts, updated_at
        )
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(id) DO UPDATE SET
            last_tick = excluded.last_tick,
            sim_speed = excluded.sim_speed,
            sim_clock_mode = excluded.sim_clock_mode,
            manual_shift_name = excluded.manual_shift_name,
            sim_clock_cursor = excluded.sim_clock_cursor,
            part_accumulator_seconds = excluded.part_accumulator_seconds,
            active_cycle_start = excluded.active_cycle_start,
            active_cycle_program = excluded.active_cycle_program,
            active_cycle_parts = excluded.active_cycle_parts,
            updated_at = excluded.updated_at
        """,
        (
            meta.get("lastTick"),
            float(meta.get("simSpeed", 1.0)),
            str(meta.get("simClockMode", "auto")),
            str(meta.get("manualShiftName", "Shift A")),
            meta.get("simClockCursor"),
            float(meta.get("partAccumulatorSeconds", 0.0) or 0.0),
            meta.get("activeCycleStart"),
            meta.get("activeCycleProgram"),
            int(meta.get("activeCycleParts", 0) or 0),
        ),
    )


def _persist_event_logs(conn: sqlite3.Connection, prev_machine: dict | None, prev_meta: dict | None, state: dict) -> None:
    machine = state.get("machine", {})
    meta = state.get("meta", {})
    event_time = str(meta.get("lastTick") or datetime.now(timezone.utc).isoformat())

    status_now = str(machine.get("machineStatus", "Running"))
    prev_status = str((prev_machine or {}).get("machineStatus", status_now))
    alarm_now = bool(machine.get("alarmActive", False))
    alarm_code_now = str(machine.get("alarmCode", "-") or "-")
    alarm_message_now = str(machine.get("alarmMessage", "No active alarm") or "No active alarm")
    prev_alarm_active = bool((prev_machine or {}).get("alarmActive", False))
    prev_alarm_code = str((prev_machine or {}).get("alarmCode", "-") or "-")
    prev_program = str((prev_machine or {}).get("currentProgram", "PROGRAM-001") or "PROGRAM-001")
    program_now = str(machine.get("currentProgram", prev_program) or prev_program)
    total_parts_now = int(machine.get("totalParts", 0) or 0)

    if prev_machine and prev_status != status_now:
        conn.execute(
            "INSERT INTO machine_state_log (event_time, from_state, to_state) VALUES (?, ?, ?)",
            (event_time, prev_status, status_now),
        )

    if alarm_now and ((not prev_alarm_active) or (alarm_code_now != prev_alarm_code)):
        conn.execute(
            "INSERT INTO alarm_log (event_time, alarm_code, alarm_message) VALUES (?, ?, ?)",
            (event_time, alarm_code_now, alarm_message_now),
        )

    active_cycle_start = meta.get("activeCycleStart")
    active_cycle_program = meta.get("activeCycleProgram")
    active_cycle_parts = int(meta.get("activeCycleParts", 0) or 0)
    prev_last_tick = (prev_meta or {}).get("lastTick")

    if status_now == "Running":
        if not active_cycle_start:
            meta["activeCycleStart"] = prev_last_tick or event_time
            meta["activeCycleProgram"] = program_now
            meta["activeCycleParts"] = total_parts_now
        elif active_cycle_program and active_cycle_program != program_now:
            cycle_seconds = _seconds_between(active_cycle_start, event_time)
            parts_delta = max(0, total_parts_now - active_cycle_parts)
            conn.execute(
                """
                INSERT INTO cycle_log (program, start_time, end_time, cycle_seconds, parts)
                VALUES (?, ?, ?, ?, ?)
                """,
                (active_cycle_program, active_cycle_start, event_time, cycle_seconds, parts_delta),
            )
            meta["activeCycleStart"] = event_time
            meta["activeCycleProgram"] = program_now
            meta["activeCycleParts"] = total_parts_now
    else:
        if active_cycle_start and active_cycle_program:
            cycle_seconds = _seconds_between(active_cycle_start, event_time)
            parts_delta = max(0, total_parts_now - active_cycle_parts)
            conn.execute(
                """
                INSERT INTO cycle_log (program, start_time, end_time, cycle_seconds, parts)
                VALUES (?, ?, ?, ?, ?)
                """,
                (active_cycle_program, active_cycle_start, event_time, cycle_seconds, parts_delta),
            )
        meta["activeCycleStart"] = None
        meta["activeCycleProgram"] = None
        meta["activeCycleParts"] = total_parts_now


def _prune_old_logs(conn: sqlite3.Connection, state: dict) -> None:
    meta = state.get("meta", {})
    now_dt = _parse_iso(meta.get("lastTick")) or datetime.now(timezone.utc)
    last_prune_at = _parse_iso(meta.get("lastPruneAt"))
    if last_prune_at and (now_dt - last_prune_at).total_seconds() < PRUNE_INTERVAL_SECONDS:
        return

    now_dt = _parse_iso(meta.get("lastTick")) or datetime.now(timezone.utc)
    cutoff_iso = (now_dt - timedelta(days=LOG_RETENTION_DAYS)).isoformat()

    conn.execute("DELETE FROM alarm_log WHERE event_time < ?", (cutoff_iso,))
    conn.execute("DELETE FROM machine_state_log WHERE event_time < ?", (cutoff_iso,))
    conn.execute("DELETE FROM cycle_log WHERE end_time < ?", (cutoff_iso,))
    conn.execute("DELETE FROM status_timeline WHERE end_time < ?", (cutoff_iso,))
    meta["lastPruneAt"] = now_dt.isoformat()


def _append_latest_timeline_row(conn: sqlite3.Connection, timeline: list[dict]) -> None:
    if not timeline:
        return
    row = timeline[-1]
    latest = conn.execute(
        """
        SELECT start_time, end_time, status, parts_delta, power_wh, program, alarm_code, alarm_message
        FROM status_timeline
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    candidate = (
        str(row.get("start", "")),
        str(row.get("end", "")),
        str(row.get("status", "Running")),
        int(row.get("partsDelta", 0)),
        float(row.get("powerWh", 0.0)),
        str(row.get("program", "")),
        str(row.get("alarmCode", "-")),
        str(row.get("alarmMessage", "No active alarm")),
    )
    if latest:
        latest_tuple = (
            latest["start_time"],
            latest["end_time"],
            latest["status"],
            int(latest["parts_delta"] or 0),
            float(latest["power_wh"] or 0.0),
            latest["program"] or "",
            latest["alarm_code"] or "-",
            latest["alarm_message"] or "No active alarm",
        )
        if latest_tuple == candidate:
            return
    conn.execute(
        """
        INSERT INTO status_timeline (
            start_time, end_time, status, parts_delta, power_wh, program, alarm_code, alarm_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        candidate,
    )


def _hydrate_state(conn: sqlite3.Connection, include_timeline: bool = False) -> dict:
    state = initial_state()

    machine_row = conn.execute("SELECT * FROM machine_state WHERE id = 1").fetchone()
    if machine_row:
        state["machine"].update(
            {
                "machineStatus": machine_row["machine_status"],
                "controllerMode": machine_row["controller_mode"],
                "currentProgram": machine_row["current_program"],
                "currentTool": machine_row["current_tool"],
                "totalParts": int(machine_row["total_parts"] or 0),
                "cuttingStatus": machine_row["cutting_status"],
                "coordinates": {
                    "x": float(machine_row["coord_x"] or 0.0),
                    "y": float(machine_row["coord_y"] or 0.0),
                    "z": float(machine_row["coord_z"] or 0.0),
                },
                "spindleSpeed": int(machine_row["spindle_speed"] or 0),
                "feedRate": int(machine_row["feed_rate"] or 0),
                "feedOutput": int(machine_row["feed_output"] or 0),
                "feedOverride": int(machine_row["feed_override"] or 0),
                "partIntervalSeconds": int(machine_row["part_interval_seconds"] or 60),
                "alarmActive": bool(machine_row["alarm_active"] or 0),
                "alarmCode": machine_row["alarm_code"] or "-",
                "alarmMessage": machine_row["alarm_message"] or "No active alarm",
                "alarmTime": machine_row["alarm_time"] or "--:--:--",
                "cuttingTimeSeconds": int(machine_row["cutting_time_seconds"] or 0),
                "idleTimeSeconds": int(machine_row["idle_time_seconds"] or 0),
                "breakdownTimeSeconds": int(machine_row["breakdown_time_seconds"] or 0),
            }
        )

    spindle_rows = conn.execute(
        "SELECT time_label, value FROM machine_series WHERE series_type = 'spindle' ORDER BY point_index ASC"
    ).fetchall()
    feed_rows = conn.execute(
        "SELECT time_label, value FROM machine_series WHERE series_type = 'feed' ORDER BY point_index ASC"
    ).fetchall()
    if spindle_rows:
        state["machine"]["spindleLoadData"] = [{"time": row["time_label"], "load": float(row["value"])} for row in spindle_rows]
    if feed_rows:
        state["machine"]["feedRateData"] = [{"time": row["time_label"], "rate": int(round(row["value"]))} for row in feed_rows]

    settings_row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    if settings_row:
        state["settings"].update(
            {
                "isConnected": bool(settings_row["is_connected"] or 0),
                "modbusSettings": {
                    "ip": settings_row["modbus_ip"] or "127.0.0.1",
                    "port": settings_row["modbus_port"] or "1502",
                    "slaveId": settings_row["modbus_slave_id"] or "1",
                    "fetchRate": settings_row["modbus_fetch_rate"] or "5s",
                    "graphRate": settings_row["modbus_graph_rate"] or "10s",
                },
            }
        )

    shift_rows = conn.execute("SELECT * FROM shifts ORDER BY id ASC").fetchall()
    if shift_rows:
        state["settings"]["shifts"] = [
            {
                "id": int(row["id"]),
                "name": row["name"],
                "start": row["start_time"],
                "end": row["end_time"],
                "saved": bool(row["saved"] or 0),
            }
            for row in shift_rows
        ]

    meta_row = conn.execute("SELECT * FROM meta WHERE id = 1").fetchone()
    if meta_row:
        state["meta"].update(
            {
                "lastTick": meta_row["last_tick"] or state["meta"]["lastTick"],
                "simSpeed": float(meta_row["sim_speed"] or 1.0),
                "simClockMode": meta_row["sim_clock_mode"] or "auto",
                "manualShiftName": meta_row["manual_shift_name"] or "Shift A",
                "simClockCursor": meta_row["sim_clock_cursor"] or state["meta"]["simClockCursor"],
                "partAccumulatorSeconds": float(meta_row["part_accumulator_seconds"] or 0.0),
                "activeCycleStart": meta_row["active_cycle_start"],
                "activeCycleProgram": meta_row["active_cycle_program"],
                "activeCycleParts": int(meta_row["active_cycle_parts"] or 0),
            }
        )

    if include_timeline:
        timeline_rows = conn.execute(
            """
            SELECT start_time, end_time, status, parts_delta, power_wh, program, alarm_code, alarm_message
            FROM status_timeline
            ORDER BY id ASC
            """
        ).fetchall()
        state["meta"]["statusTimeline"] = [
            {
                "start": row["start_time"],
                "end": row["end_time"],
                "status": row["status"],
                "partsDelta": int(row["parts_delta"] or 0),
                "powerWh": float(row["power_wh"] or 0.0),
                "program": row["program"] or "",
                "alarmCode": row["alarm_code"] or "-",
                "alarmMessage": row["alarm_message"] or "No active alarm",
            }
            for row in timeline_rows
        ]

    return state


def _persist_state(conn: sqlite3.Connection, state: dict) -> None:
    previous_machine_row = conn.execute("SELECT * FROM machine_state WHERE id = 1").fetchone()
    previous_meta_row = conn.execute("SELECT * FROM meta WHERE id = 1").fetchone()
    prev_machine = None
    if previous_machine_row:
        prev_machine = {
            "machineStatus": previous_machine_row["machine_status"] or "Running",
            "alarmActive": bool(previous_machine_row["alarm_active"] or 0),
            "alarmCode": previous_machine_row["alarm_code"] or "-",
            "currentProgram": previous_machine_row["current_program"] or "PROGRAM-001",
        }
    prev_meta = None
    if previous_meta_row:
        prev_meta = {
            "lastTick": previous_meta_row["last_tick"],
        }

    _persist_event_logs(conn, prev_machine, prev_meta, state)

    machine = state.get("machine", {})
    settings = state.get("settings", {})
    meta = state.get("meta", {})
    _upsert_machine(conn, machine)
    _replace_series(conn, "spindle", machine.get("spindleLoadData", []), "load")
    _replace_series(conn, "feed", machine.get("feedRateData", []), "rate")
    _upsert_settings(conn, settings)
    _upsert_meta(conn, meta)
    _append_latest_timeline_row(conn, meta.get("statusTimeline", []))
    _prune_old_logs(conn, state)
    conn.commit()


def _bootstrap_from_legacy_or_default(conn: sqlite3.Connection) -> None:
    count = int(conn.execute("SELECT COUNT(1) AS c FROM machine_state").fetchone()["c"])
    if count > 0:
        return
    state = None
    if LEGACY_STATE_FILE.exists():
        try:
            with LEGACY_STATE_FILE.open("r", encoding="utf-8-sig") as handle:
                state = json.load(handle)
        except Exception:
            state = None
    if not isinstance(state, dict):
        state = initial_state()
    _persist_state(conn, state)


def ensure_db() -> None:
    with _LOCK:
        with _connect() as conn:
            _ensure_schema(conn)
            _bootstrap_from_legacy_or_default(conn)


def ensure_state_file() -> None:
    ensure_db()


def load_state(include_timeline: bool = False) -> dict:
    ensure_db()
    with _LOCK:
        with _connect() as conn:
            _ensure_schema(conn)
            _bootstrap_from_legacy_or_default(conn)
            return _hydrate_state(conn, include_timeline=include_timeline)


def save_state(state: dict) -> None:
    ensure_db()
    with _LOCK:
        with _connect() as conn:
            _ensure_schema(conn)
            _persist_state(conn, state)


def reset_state() -> dict:
    state = initial_state()
    save_state(state)
    return deepcopy(state)


def update_state(mutator):
    state = load_state()
    mutator(state)
    save_state(state)
    return deepcopy(state)


def fetch_alarm_logs(start_iso: str, end_iso: str, limit: int = 25) -> list[dict]:
    ensure_db()
    with _LOCK:
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT event_time, alarm_code, alarm_message
                FROM alarm_log
                WHERE event_time >= ? AND event_time <= ?
                ORDER BY event_time DESC
                LIMIT ?
                """,
                (start_iso, end_iso, int(limit)),
            ).fetchall()
            return [
                {
                    "event_time": row["event_time"],
                    "code": row["alarm_code"],
                    "message": row["alarm_message"],
                }
                for row in rows
            ]


def fetch_cycle_logs(start_iso: str, end_iso: str, limit: int = 25) -> list[dict]:
    ensure_db()
    with _LOCK:
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT program, start_time, end_time, cycle_seconds, parts
                FROM cycle_log
                WHERE end_time >= ? AND start_time <= ?
                ORDER BY end_time DESC
                LIMIT ?
                """,
                (start_iso, end_iso, int(limit)),
            ).fetchall()
            return [
                {
                    "program": row["program"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "cycle_seconds": int(row["cycle_seconds"] or 0),
                    "parts": int(row["parts"] or 0),
                }
                for row in rows
            ]


def fetch_machine_state_logs(start_iso: str, end_iso: str, limit: int = 50) -> list[dict]:
    ensure_db()
    with _LOCK:
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT event_time, from_state, to_state
                FROM machine_state_log
                WHERE event_time >= ? AND event_time <= ?
                ORDER BY event_time DESC
                LIMIT ?
                """,
                (start_iso, end_iso, int(limit)),
            ).fetchall()
            return [
                {
                    "event_time": row["event_time"],
                    "from_state": row["from_state"],
                    "to_state": row["to_state"],
                }
                for row in rows
            ]
