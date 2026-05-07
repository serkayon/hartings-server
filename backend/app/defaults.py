from __future__ import annotations

from datetime import datetime, timezone


def initial_state() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "machine": {
            "machineStatus": "Running",
            "controllerMode": "AUTO",
            "currentProgram": "PROGRAM-001",
            "currentTool": "#08",
            "totalParts": 1847,
            "cuttingStatus": "CUTTING",
            "coordinates": {"x": 125.45, "y": 200.32, "z": -50.10},
            "spindleSpeed": 3500,
            "feedRate": 42,
            "feedOutput": 900,
            "feedOverride": 95,
            "partIntervalSeconds": 60,
            "alarmActive": False,
            "alarmCode": "-",
            "alarmMessage": "No active alarm",
            "alarmTime": "--:--:--",
            "spindleLoadData": [
                {"time": "00:10", "load": 65},
                {"time": "00:12", "load": 68},
                {"time": "00:14", "load": 72},
                {"time": "00:16", "load": 75},
                {"time": "00:18", "load": 78},
            ],
            "feedRateData": [
                {"time": "00:10", "rate": 620},
                {"time": "00:12", "rate": 710},
                {"time": "00:14", "rate": 780},
                {"time": "00:16", "rate": 860},
                {"time": "00:18", "rate": 920},
            ],
            "cuttingTimeSeconds": 15 * 60 + 32,
            "idleTimeSeconds": 5 * 60 + 20,
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
                {
                    "id": 1,
                    "name": "Shift A",
                    "start": "08:00",
                    "end": "16:00",
                    "saved": True,
                },
                {
                    "id": 2,
                    "name": "Shift B",
                    "start": "16:00",
                    "end": "00:00",
                    "saved": True,
                },
                {
                    "id": 3,
                    "name": "Shift C",
                    "start": "00:00",
                    "end": "08:00",
                    "saved": True,
                },
            ],
        },
        "meta": {
            "lastTick": now,
            "simSpeed": 1.0,
            "simClockMode": "auto",
            "manualShiftName": "Shift A",
            "simClockCursor": now,
            "partAccumulatorSeconds": 0.0,
        },
    }
