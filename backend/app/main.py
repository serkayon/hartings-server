from __future__ import annotations

import json
import os
import threading
from typing import Optional
from urllib.error import URLError
from urllib.request import urlopen

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from .models import (
        ConnectionResponse,
        DashboardResponse,
        SettingsResponse,
        UpdateModbusRequest,
        UpdateShiftsRequest,
    )
    from .services import build_analytics_payload, build_dashboard_payload, build_report_payload, tick
    from .state_store import load_state, reset_state, save_state
except ImportError:
    from models import (
        ConnectionResponse,
        DashboardResponse,
        SettingsResponse,
        UpdateModbusRequest,
        UpdateShiftsRequest,
    )
    from services import build_analytics_payload, build_dashboard_payload, build_report_payload, tick
    from state_store import load_state, reset_state, save_state

app = FastAPI(title="Hartings Live Demo API", version="1.0.0")
_POLL_THREAD: threading.Thread | None = None
_POLL_STOP = threading.Event()


def _simulator_state_url() -> str:
    return os.getenv("SIMULATOR_STATE_URL", "http://127.0.0.1:8001/state")


def _pull_simulator_state() -> dict | None:
    try:
        with urlopen(_simulator_state_url(), timeout=0.9) as response:
            payload = response.read()
        data = json.loads(payload.decode("utf-8"))
        return data if isinstance(data, dict) else None
    except (URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def _merge_simulator_into_state(state: dict, sim_state: dict) -> None:
    sim_machine = sim_state.get("machine", {})
    sim_settings = sim_state.get("settings", {})
    sim_meta = sim_state.get("meta", {})

    if isinstance(sim_machine, dict):
        state["machine"] = sim_machine
    if isinstance(sim_settings, dict):
        state["settings"] = sim_settings

    meta = state.setdefault("meta", {})
    for key in ("simSpeed", "simClockMode", "manualShiftName", "simClockCursor"):
        if key in sim_meta:
            meta[key] = sim_meta[key]


def _poll_loop() -> None:
    while not _POLL_STOP.is_set():
        state = load_state()
        sim_state = _pull_simulator_state()
        if sim_state:
            _merge_simulator_into_state(state, sim_state)
        tick(state)
        save_state(state)
        _POLL_STOP.wait(1.0)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/dashboard", response_model=DashboardResponse)
def dashboard() -> dict:
    state = load_state()
    return build_dashboard_payload(state)


@app.get("/api/analytics")
def analytics() -> dict:
    state = load_state()
    return build_analytics_payload(state)


@app.get("/api/report")
def report(
    mode: str = "daily",
    shift: str = "All",
    dateTime: Optional[str] = None,
    fromDateTime: Optional[str] = None,
    toDateTime: Optional[str] = None,
) -> dict:
    state = load_state()
    return build_report_payload(
        state=state,
        mode=mode,
        shift=shift,
        from_dt=fromDateTime,
        to_dt=toDateTime,
        date_time=dateTime,
    )


@app.get("/api/settings", response_model=SettingsResponse)
def get_settings() -> dict:
    state = load_state()
    return state["settings"]


@app.put("/api/settings/modbus", response_model=SettingsResponse)
def update_modbus(payload: UpdateModbusRequest) -> dict:
    state = load_state()
    state["settings"]["modbusSettings"] = payload.modbusSettings.model_dump()
    save_state(state)
    return state["settings"]


@app.put("/api/settings/shifts", response_model=SettingsResponse)
def update_shifts(payload: UpdateShiftsRequest) -> dict:
    state = load_state()
    state["settings"]["shifts"] = [shift.model_dump() for shift in payload.shifts]
    save_state(state)
    return state["settings"]


@app.post("/api/settings/connect", response_model=ConnectionResponse)
def connect() -> dict:
    state = load_state()
    state["settings"]["isConnected"] = True
    save_state(state)
    return {"isConnected": True}


@app.post("/api/settings/reconnect", response_model=ConnectionResponse)
def reconnect() -> dict:
    state = load_state()
    state["settings"]["isConnected"] = False
    save_state(state)
    return {"isConnected": False}


@app.post("/api/reset")
def reset() -> dict:
    reset_state()
    return {"ok": True}


@app.on_event("startup")
def _startup_polling() -> None:
    global _POLL_THREAD
    if _POLL_THREAD and _POLL_THREAD.is_alive():
        return
    _POLL_STOP.clear()
    _POLL_THREAD = threading.Thread(target=_poll_loop, name="simulator-poller", daemon=True)
    _POLL_THREAD.start()


@app.on_event("shutdown")
def _shutdown_polling() -> None:
    _POLL_STOP.set()
    if _POLL_THREAD and _POLL_THREAD.is_alive():
        _POLL_THREAD.join(timeout=1.2)
