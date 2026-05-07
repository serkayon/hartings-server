from pydantic import BaseModel, Field
from typing import List


class Coordinates(BaseModel):
    x: float
    y: float
    z: float


class SpindlePoint(BaseModel):
    time: str
    load: float


class FeedPoint(BaseModel):
    time: str
    rate: float


class ShiftSummary(BaseModel):
    name: str
    start: str
    end: str
    runtime: str
    idle: str
    breakdown: str
    runtimePercentage: int
    idlePercentage: int
    breakdownPercentage: int
    parts: int
    power: str
    remainingTime: str | None = None


class DashboardResponse(BaseModel):
    machineStatus: str
    controllerMode: str
    currentProgram: str
    currentTool: str
    totalParts: int
    cuttingStatus: str
    coordinates: Coordinates
    spindleSpeed: int
    feedRate: int
    feedOutput: int
    feedOverride: int
    alarmActive: bool
    alarmCode: str
    alarmMessage: str
    alarmTime: str
    spindleLoadData: List[SpindlePoint] = Field(default_factory=list)
    feedRateData: List[FeedPoint] = Field(default_factory=list)
    cuttingTime: str
    idleTime: str
    breakdownTime: str
    shiftSummaries: List[ShiftSummary] = Field(default_factory=list)
    consolidatedSummary: ShiftSummary


class ModbusSettings(BaseModel):
    ip: str
    port: str
    slaveId: str
    fetchRate: str
    graphRate: str


class ShiftModel(BaseModel):
    id: int
    name: str
    start: str
    end: str
    saved: bool = False


class SettingsResponse(BaseModel):
    isConnected: bool
    modbusSettings: ModbusSettings
    shifts: List[ShiftModel] = Field(default_factory=list)


class ConnectionResponse(BaseModel):
    isConnected: bool


class UpdateShiftsRequest(BaseModel):
    shifts: List[ShiftModel]


class UpdateModbusRequest(BaseModel):
    modbusSettings: ModbusSettings
