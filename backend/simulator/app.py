from __future__ import annotations

import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_BACKEND_APP_DIR = _BACKEND_ROOT / "app"
if str(_BACKEND_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_APP_DIR))

from state_store import load_state as db_load_state  # noqa: E402
from state_store import save_state as db_save_state  # noqa: E402

app = FastAPI(title="Hartings Simulator", version="2.0.0")


class MachinePatch(BaseModel):
    machineStatus: str | None = None
    controllerMode: str | None = None
    currentProgram: str | None = None
    currentTool: str | None = None
    totalParts: int | None = None
    spindleSpeed: int | None = None
    feedRate: int | None = None
    feedOutput: int | None = None
    feedOverride: int | None = None
    partIntervalSeconds: int | None = None
    alarmActive: bool | None = None
    alarmCode: str | None = None
    alarmMessage: str | None = None
    alarmTime: str | None = None
    coordinates: dict[str, float] | None = None


class SimulatorPatch(BaseModel):
    machine: MachinePatch | None = None
    meta: dict[str, Any] | None = None


def _fresh_state() -> dict[str, Any]:
    now = datetime.now().astimezone().isoformat()
    return {
        "machine": {
            "machineStatus": "Running",
            "controllerMode": "AUTO",
            "currentProgram": "PROGRAM-001",
            "currentTool": "#01",
            "totalParts": 0,
            "cuttingStatus": "CUTTING",
            "coordinates": {"x": 0.0, "y": 0.0, "z": 0.0},
            "spindleSpeed": 3200,
            "feedRate": 40,
            "feedOutput": 800,
            "feedOverride": 100,
            "partIntervalSeconds": 60,
            "alarmActive": False,
            "alarmCode": "-",
            "alarmMessage": "No active alarm",
            "alarmTime": "--:--:--",
            "spindleLoadData": [],
            "feedRateData": [],
            "cuttingTimeSeconds": 0,
            "idleTimeSeconds": 0,
            "breakdownTimeSeconds": 0,
        },
        "settings": {
            "isConnected": False,
            "modbusSettings": {
                "ip": "127.0.0.1",
                "port": "1502",
                "slaveId": "1",
                "fetchRate": "5s",
                "graphRate": "10s",
            },
            "shifts": [
                {"id": 1, "name": "Shift A", "start": "08:00", "end": "16:00", "saved": True},
                {"id": 2, "name": "Shift B", "start": "16:00", "end": "00:00", "saved": True},
                {"id": 3, "name": "Shift C", "start": "00:00", "end": "08:00", "saved": True},
            ],
        },
        "meta": {
            "lastTick": now,
            "simSpeed": 1.0,
            "simClockMode": "auto",
            "manualShiftName": "Shift A",
            "simClockCursor": now,
        },
    }


def _load_state() -> dict[str, Any]:
    try:
        return db_load_state()
    except Exception:
        state = _fresh_state()
        db_save_state(state)
        return state


def _save_state(state: dict[str, Any]) -> None:
    db_save_state(state)


def _normalize_status(status: str | None) -> str:
    value = (status or "").strip().lower()
    if value in {"running", "active"}:
        return "Running"
    if value in {"idle"}:
        return "Idle"
    if value in {"breakdown", "break down", "alarm"}:
        return "Breakdown"
    return "Running"


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/state")
def get_state() -> dict:
    return _load_state()


@app.patch("/state")
def patch_state(payload: SimulatorPatch) -> dict:
    state = _load_state()
    machine = state.setdefault("machine", {})
    meta_state = state.setdefault("meta", {})

    if payload.machine is not None:
        patch = payload.machine.model_dump(exclude_none=True)
        if "machineStatus" in patch:
            patch["machineStatus"] = _normalize_status(patch["machineStatus"])
            if patch["machineStatus"] == "Breakdown":
                patch.setdefault("alarmActive", True)
                patch.setdefault("alarmCode", "T0125")
                patch.setdefault("alarmMessage", "SPINDLE OVERLOAD DETECTED")
                patch.setdefault("alarmTime", datetime.now().strftime("%H:%M:%S"))
            elif patch["machineStatus"] in {"Running", "Idle"}:
                patch.setdefault("alarmActive", False)
                patch.setdefault("alarmCode", "-")
                patch.setdefault("alarmMessage", "No active alarm")
                patch.setdefault("alarmTime", "--:--:--")

        for key, value in patch.items():
            if key == "coordinates" and isinstance(value, dict):
                machine.setdefault("coordinates", {}).update(value)
            else:
                machine[key] = value

    if payload.meta:
        sim_mode = (payload.meta.get("simClockMode") or "auto").strip().lower()
        if sim_mode not in {"auto", "manual_shift"}:
            sim_mode = "auto"
        manual_shift = str(payload.meta.get("manualShiftName") or "Shift A").strip() or "Shift A"
        meta_state["simClockMode"] = sim_mode
        meta_state["manualShiftName"] = manual_shift

    _save_state(state)
    return state


@app.post("/machine/status/{status}")
def set_machine_status(status: str) -> dict:
    state = _load_state()
    normalized = _normalize_status(status)
    state.setdefault("machine", {})["machineStatus"] = normalized

    if normalized == "Breakdown":
        state["machine"]["alarmActive"] = True
        state["machine"]["alarmCode"] = "T0125"
        state["machine"]["alarmMessage"] = "SPINDLE OVERLOAD DETECTED"
        state["machine"]["alarmTime"] = datetime.now().strftime("%H:%M:%S")
    else:
        state["machine"]["alarmActive"] = False
        state["machine"]["alarmCode"] = "-"
        state["machine"]["alarmMessage"] = "No active alarm"
        state["machine"]["alarmTime"] = "--:--:--"

    _save_state(state)
    return state


@app.get("/", response_class=HTMLResponse)
def simulator_ui() -> str:
    return """
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Hartings Real-Time Simulator</title>
  <style>
    :root {
      --navy:#102a5c;
      --soft:#eef3fb;
      --line:#d8e1ef;
      --ok:#148f3d;
      --idle:#475569;
      --bad:#dc2626;
    }
    body{font-family:Segoe UI,Arial,sans-serif;background:linear-gradient(180deg,#f7f9fd,#edf2fa);margin:0;padding:18px;color:var(--navy)}
    .wrap{max-width:1100px;margin:0 auto;background:#fff;border:1px solid var(--line);border-radius:20px;padding:18px;box-shadow:0 16px 36px rgba(16,42,92,.10)}
    h1{margin:0 0 8px;font-size:28px}
    .hint{font-size:13px;color:#64748b;margin:0 0 14px}
    .grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
    .grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
    label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:#6b7a99}
    select,input[type=number]{width:100%;padding:10px;border:1px solid #cfd9e8;border-radius:10px;margin-top:6px;background:#fff}
    .range-box{background:#f8fbff;border:1px solid #dde6f3;border-radius:12px;padding:10px}
    input[type=range]{width:100%}
    .range-row{display:flex;justify-content:space-between;font-size:12px;color:#64748b}
    .row{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
    button{border:0;border-radius:12px;padding:10px 14px;font-weight:700;cursor:pointer}
    .primary{background:var(--navy);color:#fff}
    .ok{background:var(--ok);color:#fff}
    .idle{background:var(--idle);color:#fff}
    .bad{background:var(--bad);color:#fff}
    .ghost{background:#e5ebf6;color:var(--navy)}
    .pill{display:inline-flex;align-items:center;padding:6px 10px;border-radius:999px;font-size:12px;font-weight:700;background:#e9effa}
    .live{display:flex;align-items:center;gap:8px;margin-top:10px}
    .dot{width:10px;height:10px;border-radius:50%;background:#9ca3af}
    .dot.on{background:#22c55e;box-shadow:0 0 10px rgba(34,197,94,.6)}
    .split{display:grid;grid-template-columns:2fr 1fr;gap:12px}
    .mini{background:#f8fbff;border:1px solid #dde6f3;border-radius:12px;padding:10px}
    .mini h3{margin:0 0 8px;font-size:14px}
    .mono{font-family:Consolas,monospace}
    @media (max-width: 900px){
      .grid,.grid3,.split{grid-template-columns:1fr}
    }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>Hartings Live Machine Simulator</h1>
    <p class=\"hint\">Set machine profile once. Start simulation to push live values every 5 seconds. Any control change applies immediately.</p>

    <div class=\"split\">
      <div>
        <div class=\"grid\">
          <div>
            <label>Machine Status</label>
            <select id=\"machineStatus\" onchange=\"applyManual()\">
              <option>Running</option>
              <option>Idle</option>
              <option>Breakdown</option>
            </select>
          </div>
          <div>
            <label>Mode</label>
            <select id=\"controllerMode\" onchange=\"applyManual()\">
              <option>AUTO</option>
              <option>MDI</option>
              <option>JOG</option>
            </select>
          </div>
          <div>
            <label>Current Program</label>
            <select id=\"currentProgram\" onchange=\"applyManual()\"></select>
          </div>
          <div>
            <label>Current Tool</label>
            <select id=\"currentTool\" onchange=\"applyManual()\"></select>
          </div>
        </div>

        <div class=\"grid\" style=\"margin-top:12px\">
          <div>
            <label>Total Parts</label>
            <input id=\"totalParts\" type=\"number\" min=\"0\" onchange=\"applyManual()\" />
          </div>
          <div>
            <label>Spindle Speed</label>
            <input id=\"spindleSpeed\" type=\"number\" min=\"0\" max=\"6000\" onchange=\"applyManual()\" />
          </div>
        </div>
        <div class=\"grid\" style=\"margin-top:12px\">
          <div>
            <label>Seconds Per Part</label>
            <input id=\"partIntervalSeconds\" type=\"number\" min=\"1\" step=\"1\" value=\"60\" onchange=\"applyManual()\" />
          </div>
          <div></div>
        </div>

        <div class=\"grid\" style=\"margin-top:12px\">
          <div>
            <label>Alarm State</label>
            <select id=\"alarmState\" onchange=\"updateAlarmUI(); applyManual()\">
              <option value=\"off\">Alarm OFF</option>
              <option value=\"on\">Alarm ON</option>
            </select>
          </div>
          <div>
            <label>Alarm Code</label>
            <select id=\"alarmCodeSelect\" onchange=\"updateAlarmUI(); applyManual()\"></select>
          </div>
        </div>
        <div style=\"margin-top:8px\">
          <label>Alarm Reason</label>
          <input id=\"alarmReason\" type=\"text\" readonly />
        </div>

        <div class=\"grid3\" style=\"margin-top:12px\">
          <div class=\"range-box\">
            <label>X Axis</label>
            <input id=\"x\" type=\"range\" min=\"-500\" max=\"500\" step=\"0.01\" oninput=\"syncRange('x')\" onchange=\"applyManual()\" />
            <div class=\"range-row\"><span>-500</span><span id=\"xVal\" class=\"mono\">0.00</span><span>500</span></div>
          </div>
          <div class=\"range-box\">
            <label>Y Axis</label>
            <input id=\"y\" type=\"range\" min=\"-500\" max=\"500\" step=\"0.01\" oninput=\"syncRange('y')\" onchange=\"applyManual()\" />
            <div class=\"range-row\"><span>-500</span><span id=\"yVal\" class=\"mono\">0.00</span><span>500</span></div>
          </div>
          <div class=\"range-box\">
            <label>Z Axis</label>
            <input id=\"z\" type=\"range\" min=\"-500\" max=\"500\" step=\"0.01\" oninput=\"syncRange('z')\" onchange=\"applyManual()\" />
            <div class=\"range-row\"><span>-500</span><span id=\"zVal\" class=\"mono\">0.00</span><span>500</span></div>
          </div>
        </div>
      </div>

      <div class=\"mini\">
        <h3>Live Engine</h3>
        <div class=\"live\"><span id=\"liveDot\" class=\"dot\"></span><span id=\"liveText\">Stopped</span></div>
        <div style=\"margin-top:10px\" class=\"pill\">Push Interval: 5 sec</div>
        <div style=\"margin-top:12px\">
          <label>Shift Insertion Mode</label>
          <select id=\"simClockMode\" onchange=\"updateShiftModeUI(); applyManual()\">
            <option value=\"auto\">Auto by current time</option>
            <option value=\"manual_shift\">Manual shift selection</option>
          </select>
        </div>
        <div style=\"margin-top:8px\">
          <label>Target Shift</label>
          <select id=\"manualShiftName\" onchange=\"applyManual()\">
            <option>Shift A</option>
            <option>Shift B</option>
            <option>Shift C</option>
          </select>
        </div>

        <div class=\"row\" style=\"margin-top:12px\">
          <button class=\"ok\" onclick=\"startSimulation()\">Start</button>
          <button class=\"ghost\" onclick=\"stopSimulation()\">Stop</button>
          <button class=\"primary\" onclick=\"applyManual()\">Apply Now</button>
        </div>

        <div class=\"row\" style=\"margin-top:8px\">
          <button class=\"ok\" onclick=\"quickStatus('running')\">Set Running</button>
          <button class=\"idle\" onclick=\"quickStatus('idle')\">Set Idle</button>
          <button class=\"bad\" onclick=\"quickStatus('breakdown')\">Set Breakdown</button>
        </div>

        <p class=\"hint\" style=\"margin-top:12px\">When simulation is ON, machine values keep changing like a real controller stream.</p>
      </div>
    </div>
  </div>

<script>
const PROGRAMS = Array.from({length: 10}, (_, i) => `PROGRAM-${String(i + 1).padStart(3, '0')}`);
const TOOLS = Array.from({length: 10}, (_, i) => `#${String(i + 1).padStart(2, '0')}`);
const ALARM_PROFILES = [
  { code: "T0125", reason: "Spindle overload detected" },
  { code: "A0301", reason: "Axis drive overcurrent" },
  { code: "M1002", reason: "Lubrication pressure low" },
  { code: "P2007", reason: "Hydraulic pressure drop" },
  { code: "C4410", reason: "Coolant flow failure" },
];

let simulationTimer = null;

function fillOptions() {
  currentProgram.innerHTML = PROGRAMS.map(p => `<option>${p}</option>`).join('');
  currentTool.innerHTML = TOOLS.map(t => `<option>${t}</option>`).join('');
  alarmCodeSelect.innerHTML = ALARM_PROFILES.map(a => `<option value="${a.code}">${a.code}</option>`).join('');
}

function syncRange(id) {
  const el = document.getElementById(id);
  document.getElementById(id + 'Val').textContent = Number(el.value).toFixed(2);
}

function setLiveStatus(isOn) {
  liveDot.classList.toggle('on', isOn);
  liveText.textContent = isOn ? 'Running (auto push every 5s)' : 'Stopped';
}

function updateShiftModeUI() {
  manualShiftName.disabled = simClockMode.value !== 'manual_shift';
}

function selectedAlarmProfile() {
  const code = alarmCodeSelect.value || ALARM_PROFILES[0].code;
  return ALARM_PROFILES.find(a => a.code === code) || ALARM_PROFILES[0];
}

function updateAlarmUI() {
  const alarmOn = alarmState.value === 'on';
  alarmCodeSelect.disabled = !alarmOn;
  const profile = selectedAlarmProfile();
  alarmReason.value = alarmOn ? profile.reason : "No active alarm";
  if (alarmOn) {
    machineStatus.value = "Breakdown";
  }
}

function readBasePayload() {
  return {
    machineStatus: machineStatus.value,
    controllerMode: controllerMode.value,
    currentProgram: currentProgram.value,
    currentTool: currentTool.value,
    totalParts: Number(totalParts.value || 0),
    spindleSpeed: Number(spindleSpeed.value || 0),
    partIntervalSeconds: Number(partIntervalSeconds.value || 60),
    coordinates: {
      x: Number(x.value || 0),
      y: Number(y.value || 0),
      z: Number(z.value || 0)
    }
  };
}

function applyAlarmToPayload(base, timeValue) {
  const alarmOn = alarmState.value === 'on';
  const shouldAlarm = alarmOn || base.machineStatus === "Breakdown";
  if (shouldAlarm) {
    const profile = selectedAlarmProfile();
    base.machineStatus = "Breakdown";
    base.alarmActive = true;
    base.alarmCode = profile.code;
    base.alarmMessage = profile.reason.toUpperCase();
    base.alarmTime = timeValue;
  } else {
    base.alarmActive = false;
    base.alarmCode = "-";
    base.alarmMessage = "No active alarm";
    base.alarmTime = "--:--:--";
  }
}

function readMetaPayload() {
  return {
    simClockMode: simClockMode.value,
    manualShiftName: manualShiftName.value
  };
}

async function patchMachine(machinePatch) {
  await fetch('/state', {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ machine: machinePatch, meta: readMetaPayload() })
  });
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function jitter(value, step) {
  return Number((value + (Math.random() * 2 - 1) * step).toFixed(2));
}

function generateLivePatch() {
  const base = readBasePayload();
  if (alarmState.value === 'on') {
    base.machineStatus = "Breakdown";
  }
  const status = base.machineStatus;

  if (status === 'Running') {
    base.spindleSpeed = randomInt(2600, 5200);
    base.feedRate = randomInt(35, 95);
    base.feedOutput = base.feedRate * randomInt(16, 22);
    base.feedOverride = randomInt(90, 110);
    base.coordinates.x = jitter(base.coordinates.x, 0.25);
    base.coordinates.y = jitter(base.coordinates.y, 0.25);
    base.coordinates.z = jitter(base.coordinates.z, 0.12);
  } else if (status === 'Idle') {
    base.spindleSpeed = randomInt(0, 700);
    base.feedRate = randomInt(0, 10);
    base.feedOutput = base.feedRate * randomInt(8, 12);
    base.feedOverride = randomInt(80, 100);
    base.coordinates.x = jitter(base.coordinates.x, 0.05);
    base.coordinates.y = jitter(base.coordinates.y, 0.05);
    base.coordinates.z = jitter(base.coordinates.z, 0.03);
  } else {
    base.spindleSpeed = 0;
    base.feedRate = 0;
    base.feedOutput = 0;
    base.feedOverride = randomInt(0, 20);
  }

  applyAlarmToPayload(base, new Date().toLocaleTimeString('en-GB', {hour12: false}));

  spindleSpeed.value = base.spindleSpeed;
  return base;
}

async function applyManual() {
  const patch = readBasePayload();
  applyAlarmToPayload(patch, new Date().toLocaleTimeString('en-GB', {hour12: false}));
  await patchMachine(patch);
}

async function simulateTick() {
  const patch = generateLivePatch();
  delete patch.totalParts;
  await patchMachine(patch);
  syncRange('x');
  syncRange('y');
  syncRange('z');
}

function startSimulation() {
  if (simulationTimer) return;
  setLiveStatus(true);
  simulateTick();
  simulationTimer = setInterval(simulateTick, 5000);
}

function stopSimulation() {
  if (simulationTimer) {
    clearInterval(simulationTimer);
    simulationTimer = null;
  }
  setLiveStatus(false);
}

async function quickStatus(status) {
  if (status === 'breakdown') {
    alarmState.value = 'on';
    machineStatus.value = 'Breakdown';
  } else {
    alarmState.value = 'off';
    machineStatus.value = status === 'idle' ? 'Idle' : 'Running';
  }
  updateAlarmUI();
  await applyManual();
  await loadState();
}

async function loadState() {
  const res = await fetch('/state');
  const state = await res.json();
  const m = state.machine || {};
  const c = m.coordinates || {};
  const meta = state.meta || {};

  machineStatus.value = m.machineStatus || 'Running';
  controllerMode.value = m.controllerMode || 'AUTO';
  currentProgram.value = m.currentProgram || PROGRAMS[0];
  currentTool.value = m.currentTool || TOOLS[0];
  totalParts.value = m.totalParts || 0;
  spindleSpeed.value = m.spindleSpeed || 0;
  partIntervalSeconds.value = m.partIntervalSeconds || 60;
  alarmState.value = m.alarmActive ? 'on' : 'off';
  const knownAlarm = ALARM_PROFILES.some(a => a.code === m.alarmCode) ? m.alarmCode : ALARM_PROFILES[0].code;
  alarmCodeSelect.value = knownAlarm;
  simClockMode.value = meta.simClockMode || 'auto';
  manualShiftName.value = meta.manualShiftName || 'Shift A';
  updateShiftModeUI();
  updateAlarmUI();

  x.value = c.x ?? 0;
  y.value = c.y ?? 0;
  z.value = c.z ?? 0;

  syncRange('x');
  syncRange('y');
  syncRange('z');
}

fillOptions();
loadState();
setLiveStatus(false);
</script>
</body>
</html>
"""
