import React, { useEffect, useState } from "react";
import {
  Settings,
  Plus,
  Trash2,
  Check,
  PlugZap,
  RotateCcw,
} from "lucide-react";

const SettingsPage = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [modbusSettings, setModbusSettings] = useState({
    ip: "127.0.0.1",
    port: "1502",
    slaveId: "1",
    fetchRate: "5s",
    graphRate: "10s",
  });
  const [shifts, setShifts] = useState([
    {
      id: 1,
      name: "Shift A",
      start: "08:00",
      end: "16:00",
      saved: false,
    },
  ]);

  const loadSettings = async () => {
    try {
      const response = await fetch("/api/settings");
      if (!response.ok) {
        return;
      }

      const data = await response.json();
      setIsConnected(Boolean(data.isConnected));
      setModbusSettings(data.modbusSettings || modbusSettings);
      setShifts(Array.isArray(data.shifts) ? data.shifts : shifts);
    } catch (error) {
      // Keep existing values if backend settings API is unavailable.
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const persistShifts = async (nextShifts) => {
    try {
      await fetch("/api/settings/shifts", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ shifts: nextShifts }),
      });
    } catch (error) {
      // Frontend state is kept so user does not lose form input.
    }
  };

  const handleConnect = async () => {
    try {
      await fetch("/api/settings/modbus", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ modbusSettings }),
      });

      const response = await fetch("/api/settings/connect", { method: "POST" });
      if (!response.ok) {
        return;
      }

      const data = await response.json();
      setIsConnected(Boolean(data.isConnected));
    } catch (error) {
      // Ignore transient failures and let user try again.
    }
  };

  const handleReconnect = async () => {
    try {
      const response = await fetch("/api/settings/reconnect", { method: "POST" });
      if (!response.ok) {
        return;
      }

      const data = await response.json();
      setIsConnected(Boolean(data.isConnected));
    } catch (error) {
      // Keep previous state on API failure.
    }
  };

  const handleShiftChange = (id, field, value) => {
    setShifts((prev) =>
      prev.map((shift) =>
        shift.id === id
          ? {
              ...shift,
              [field]: value,
              saved: false,
            }
          : shift
      )
    );
  };

  const handleSaveShift = async (id) => {
    const currentShift = shifts.find((shift) => shift.id === id);

    if (!currentShift.name.trim() || !currentShift.start || !currentShift.end) {
      alert("Please fill all shift details");
      return;
    }

    const nextShifts = shifts.map((shift) =>
      shift.id === id
        ? {
            ...shift,
            saved: true,
          }
        : shift
    );

    setShifts(nextShifts);
    await persistShifts(nextShifts);
  };

  const handleDeleteShift = async (id) => {
    const nextShifts = shifts.filter((shift) => shift.id !== id);
    setShifts(nextShifts);
    await persistShifts(nextShifts);
  };

  const addShift = () => {
    setShifts((prev) => [
      ...prev,
      {
        id: Date.now(),
        name: "",
        start: "",
        end: "",
        saved: false,
      },
    ]);
  };

  return (
    <div className="w-full min-h-screen bg-[#f4f7fb] p-3 sm:p-5 lg:p-6">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-11 h-11 rounded-2xl bg-[#0b2c6d] flex items-center justify-center shadow-lg">
          <Settings className="text-white" size={22} />
        </div>

        <div>
          <h1 className="text-[#0b2c6d] text-2xl sm:text-3xl font-bold">
            Settings
          </h1>

          <p className="text-[#6c7a96] text-sm">
            CNC Traceability Configuration
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5">
        <div className="bg-white rounded-[28px] border border-[#d8e1f0] shadow-[0_10px_30px_rgba(15,35,95,0.08)] p-4 sm:p-6">
          <div className="flex items-start justify-between gap-4 mb-6 flex-wrap">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-[#edf3ff] flex items-center justify-center">
                <PlugZap className="text-[#0b2c6d]" size={22} />
              </div>

              <div>
                <h2 className="text-[#0b2c6d] text-2xl font-bold">
                  Modbus Connection
                </h2>

                <p className="text-[#7b8ba7] text-sm">
                  Configure machine communication
                </p>
              </div>
            </div>

            {isConnected && (
              <button
                onClick={handleReconnect}
                className="h-[50px] px-5 rounded-2xl bg-[#0b2c6d] text-white font-semibold flex items-center gap-2 shadow-lg hover:scale-[1.02] transition-all"
              >
                <RotateCcw size={18} />
                Reconnect
              </button>
            )}
          </div>

          <div className="w-full h-[2px] bg-[#3b82f6] mb-6 rounded-full"></div>

          <div
            className={`space-y-5 ${
              isConnected ? "cursor-not-allowed opacity-80" : ""
            }`}
          >
            <div>
              <label className="text-[#0b2c6d] text-sm tracking-[2px] uppercase mb-2 block font-semibold">
                Modbus IP
              </label>

              <input
                disabled={isConnected}
                type="text"
                value={modbusSettings.ip}
                onChange={(e) =>
                  setModbusSettings({
                    ...modbusSettings,
                    ip: e.target.value,
                  })
                }
                className="w-full h-[54px] rounded-2xl border border-[#cfd8e6] px-4 bg-[#f8fbff] text-[#0b2c6d] outline-none disabled:cursor-not-allowed disabled:bg-[#eef2f7]"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-[#0b2c6d] text-sm tracking-[2px] uppercase mb-2 block font-semibold">
                  Port
                </label>

                <input
                  disabled={isConnected}
                  type="number"
                  value={modbusSettings.port}
                  onChange={(e) =>
                    setModbusSettings({
                      ...modbusSettings,
                      port: e.target.value,
                    })
                  }
                  className="w-full h-[54px] rounded-2xl border border-[#cfd8e6] px-4 bg-[#f8fbff] text-[#0b2c6d] outline-none disabled:cursor-not-allowed disabled:bg-[#eef2f7]"
                />
              </div>

              <div>
                <label className="text-[#0b2c6d] text-sm tracking-[2px] uppercase mb-2 block font-semibold">
                  Slave ID
                </label>

                <input
                  disabled={isConnected}
                  type="number"
                  value={modbusSettings.slaveId}
                  onChange={(e) =>
                    setModbusSettings({
                      ...modbusSettings,
                      slaveId: e.target.value,
                    })
                  }
                  className="w-full h-[54px] rounded-2xl border border-[#cfd8e6] px-4 bg-[#f8fbff] text-[#0b2c6d] outline-none disabled:cursor-not-allowed disabled:bg-[#eef2f7]"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-[#0b2c6d] text-sm tracking-[2px] uppercase mb-2 block font-semibold">
                  Modbus Data Fetch
                </label>

                <select
                  disabled={isConnected}
                  value={modbusSettings.fetchRate}
                  onChange={(e) =>
                    setModbusSettings({
                      ...modbusSettings,
                      fetchRate: e.target.value,
                    })
                  }
                  className="w-full h-[54px] rounded-2xl border border-[#cfd8e6] px-4 bg-[#f8fbff] text-[#0b2c6d] outline-none disabled:cursor-not-allowed disabled:bg-[#eef2f7]"
                >
                  <option>1s</option>
                  <option>3s</option>
                  <option>5s</option>
                  <option>10s</option>
                </select>
              </div>

          
            </div>

            <div className="flex justify-center pt-2">
              <button
                disabled={isConnected}
                onClick={handleConnect}
                className={`min-w-[220px] h-[58px] rounded-2xl text-lg font-bold transition-all duration-300 shadow-lg
                ${
                  isConnected
                    ? "bg-[#86efac] text-green-900 cursor-not-allowed"
                    : "bg-[#16a34a] hover:scale-[1.02] text-white"
                }`}
              >
                {isConnected ? "Connected" : "Connect"}
              </button>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-[28px] border border-[#d8e1f0] shadow-[0_10px_30px_rgba(15,35,95,0.08)] p-4 sm:p-6">
          <div className="flex items-center justify-between flex-wrap gap-4 mb-6">
            <div>
              <h2 className="text-[#0b2c6d] text-2xl font-bold">
                Shift Timing Setup
              </h2>

              <p className="text-[#7b8ba7] text-sm">
                Configure production shifts
              </p>
            </div>

            <button
              onClick={addShift}
              className="h-[50px] px-5 rounded-2xl bg-[#0b2c6d] text-white flex items-center gap-2 shadow-lg hover:scale-[1.02] transition-all"
            >
              <Plus size={18} />
              Add Shift
            </button>
          </div>

          <div className="space-y-5">
            {shifts.map((shift, index) => (
              <div
                key={shift.id}
                className="bg-[#f7faff] border border-[#dbe5f3] rounded-[24px] p-4 sm:p-5"
              >
                <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
                  <h3 className="text-[#0b2c6d] font-bold text-lg">
                    Shift {index + 1}
                  </h3>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleDeleteShift(shift.id)}
                      className="w-11 h-11 rounded-xl bg-red-50 text-red-500 flex items-center justify-center hover:scale-105 transition-all"
                    >
                      <Trash2 size={18} />
                    </button>

                    <button
                      onClick={() => handleSaveShift(shift.id)}
                      className={`min-w-[120px] h-11 rounded-xl font-semibold transition-all ${
                        shift.saved
                          ? "bg-[#22c55e] text-white"
                          : "bg-[#0b2c6d] text-white"
                      }`}
                    >
                      {shift.saved ? "Saved" : "Save"}
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  <div>
                    <label className="text-[#0b2c6d] text-sm tracking-[2px] uppercase mb-2 block font-semibold">
                      Shift Name
                    </label>

                    <input
                      type="text"
                      value={shift.name}
                      onChange={(e) =>
                        handleShiftChange(
                          shift.id,
                          "name",
                          e.target.value
                        )
                      }
                      placeholder="Enter Shift Name"
                      className="w-full h-[54px] rounded-2xl border border-[#cfd8e6] px-4 bg-white text-[#0b2c6d] outline-none"
                    />
                  </div>

                  <div>
                    <label className="text-[#0b2c6d] text-sm tracking-[2px] uppercase mb-2 block font-semibold">
                      Starting Time
                    </label>

                    <input
                      type="time"
                      value={shift.start}
                      onChange={(e) =>
                        handleShiftChange(
                          shift.id,
                          "start",
                          e.target.value
                        )
                      }
                      className="w-full h-[54px] rounded-2xl border border-[#cfd8e6] px-4 bg-white text-[#0b2c6d] outline-none"
                    />
                  </div>

                  <div>
                    <label className="text-[#0b2c6d] text-sm tracking-[2px] uppercase mb-2 block font-semibold">
                      Ending Time
                    </label>

                    <input
                      type="time"
                      value={shift.end}
                      onChange={(e) =>
                        handleShiftChange(
                          shift.id,
                          "end",
                          e.target.value
                        )
                      }
                      className="w-full h-[54px] rounded-2xl border border-[#cfd8e6] px-4 bg-white text-[#0b2c6d] outline-none"
                    />
                  </div>
                </div>

                {shift.saved && (
                  <div className="mt-4 bg-green-50 border border-green-200 rounded-2xl p-3 flex items-center gap-2 text-green-700">
                    <Check size={18} />
                    Shift timing saved successfully
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
