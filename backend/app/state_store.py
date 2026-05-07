from __future__ import annotations

import json
import os
import sqlite3
import threading
from copy import deepcopy
from pathlib import Path

try:
    from .defaults import initial_state
except ImportError:
    from defaults import initial_state

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_DEFAULT_DB_FILE = _BACKEND_DIR / "app" / "live_state.db"
DB_FILE = Path(os.getenv("LIVE_DB_FILE", str(_DEFAULT_DB_FILE)))
LEGACY_STATE_FILE = Path(os.getenv("LIVE_STATE_FILE", str(_BACKEND_DIR / "simulator" / "live_state.json")))
_LOCK = threading.Lock()


def _connect() -> sqlite3.Connection:
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
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
        """
    )
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(machine_state)").fetchall()}
    if "part_interval_seconds" not in cols:
        conn.execute("ALTER TABLE machine_state ADD COLUMN part_interval_seconds INTEGER")
    meta_cols = {row["name"] for row in conn.execute("PRAGMA table_info(meta)").fetchall()}
    if "part_accumulator_seconds" not in meta_cols:
        conn.execute("ALTER TABLE meta ADD COLUMN part_accumulator_seconds REAL NOT NULL DEFAULT 0.0")
    conn.commit()


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
    conn.execute("DELETE FROM machine_series WHERE series_type = ?", (series_type,))
    for idx, row in enumerate(data):
        conn.execute(
            """
            INSERT INTO machine_series (series_type, point_index, time_label, value)
            VALUES (?, ?, ?, ?)
            """,
            (
                series_type,
                idx,
                str(row.get("time", "00:00:00")),
                float(row.get(value_key, 0.0)),
            ),
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
        INSERT INTO meta (id, last_tick, sim_speed, sim_clock_mode, manual_shift_name, sim_clock_cursor, part_accumulator_seconds, updated_at)
        VALUES (1, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(id) DO UPDATE SET
            last_tick = excluded.last_tick,
            sim_speed = excluded.sim_speed,
            sim_clock_mode = excluded.sim_clock_mode,
            manual_shift_name = excluded.manual_shift_name,
            sim_clock_cursor = excluded.sim_clock_cursor,
            part_accumulator_seconds = excluded.part_accumulator_seconds,
            updated_at = excluded.updated_at
        """,
        (
            meta.get("lastTick"),
            float(meta.get("simSpeed", 1.0)),
            str(meta.get("simClockMode", "auto")),
            str(meta.get("manualShiftName", "Shift A")),
            meta.get("simClockCursor"),
            float(meta.get("partAccumulatorSeconds", 0.0) or 0.0),
        ),
    )


def _sync_timeline(conn: sqlite3.Connection, timeline: list[dict]) -> None:
    db_count = int(conn.execute("SELECT COUNT(1) AS c FROM status_timeline").fetchone()["c"])
    state_count = len(timeline)

    if state_count < db_count:
        conn.execute("DELETE FROM status_timeline")
        db_count = 0

    for row in timeline[db_count:]:
        conn.execute(
            """
            INSERT INTO status_timeline (
                start_time, end_time, status, parts_delta, power_wh, program, alarm_code, alarm_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(row.get("start", "")),
                str(row.get("end", "")),
                str(row.get("status", "Running")),
                int(row.get("partsDelta", 0)),
                float(row.get("powerWh", 0.0)),
                str(row.get("program", "")),
                str(row.get("alarmCode", "-")),
                str(row.get("alarmMessage", "No active alarm")),
            ),
        )

    if timeline:
        cutoff_iso = timeline[0].get("start")
        if cutoff_iso:
            conn.execute("DELETE FROM status_timeline WHERE end_time < ?", (str(cutoff_iso),))


def _hydrate_state(conn: sqlite3.Connection) -> dict:
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
            }
        )

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
    machine = state.get("machine", {})
    settings = state.get("settings", {})
    meta = state.get("meta", {})
    _upsert_machine(conn, machine)
    _replace_series(conn, "spindle", machine.get("spindleLoadData", []), "load")
    _replace_series(conn, "feed", machine.get("feedRateData", []), "rate")
    _upsert_settings(conn, settings)
    _upsert_meta(conn, meta)
    _sync_timeline(conn, meta.get("statusTimeline", []))
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


def load_state() -> dict:
    ensure_db()
    with _LOCK:
        with _connect() as conn:
            _ensure_schema(conn)
            _bootstrap_from_legacy_or_default(conn)
            return _hydrate_state(conn)


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
