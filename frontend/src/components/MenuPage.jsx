import React, { useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import Navbar from "./Navbar";

import {
  FileText,
  BarChart3,
  Settings,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

const MenuPage = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const location = useLocation();

  return (
    <div className="min-h-screen bg-[#f4f6fb]">
      {/* NAVBAR */}
      <Navbar />

      {/* MAIN LAYOUT */}
      <div className="flex relative">
        {/* =========================================
            DESKTOP SIDEBAR
        ========================================= */}
        <div
          className={`
            hidden md:flex
            bg-white
            border-r border-[#d8dfef]
            shadow-xl
            z-40
            transition-all duration-300
            flex-col
            
            fixed
            top-[88px]
            left-0
            
            h-[calc(100vh-88px)]
            
            ${
              sidebarOpen
                ? "w-[260px]"
                : "w-[85px]"
            }
          `}
        >
          {/* TOP */}
          <div className="flex items-center justify-between px-4 py-5 border-b border-[#e4e8f2]">
            {sidebarOpen && (
              <h2 className="text-[#123274] text-xl font-bold tracking-wide">
                MENU
              </h2>
            )}

            <button
              onClick={() =>
                setSidebarOpen(!sidebarOpen)
              }
              className="
                bg-[#123274]
                text-white
                p-2
                rounded-xl
                shadow-md
                hover:scale-105
                transition-all
              "
            >
              {sidebarOpen ? (
                <ChevronLeft size={20} />
              ) : (
                <ChevronRight size={20} />
              )}
            </button>
          </div>

          {/* MENU ITEMS */}
          <div className="flex flex-col gap-4 p-4 overflow-y-auto">
            {/* REPORT */}
            <Link
              to="/menu/report"
              className={`
                flex items-center gap-4
                px-4 py-4
                rounded-2xl
                transition-all duration-300
                shadow-md

                ${
                  location.pathname ===
                  "/menu/report"
                    ? "bg-[#123274] text-white"
                    : "bg-[#f5f7fc] text-[#123274] hover:bg-[#e8eefc]"
                }
              `}
            >
              <FileText size={22} />

              {sidebarOpen && (
                <span className="font-semibold tracking-wide">
                  Report
                </span>
              )}
            </Link>

            {/* KPI */}
            <Link
              to="/menu/kpi"
              className={`
                flex items-center gap-4
                px-4 py-4
                rounded-2xl
                transition-all duration-300
                shadow-md

                ${
                  location.pathname ===
                  "/menu/kpi"
                    ? "bg-[#123274] text-white"
                    : "bg-[#f5f7fc] text-[#123274] hover:bg-[#e8eefc]"
                }
              `}
            >
              <BarChart3 size={22} />

              {sidebarOpen && (
                <span className="font-semibold tracking-wide">
                  KPI
                </span>
              )}
            </Link>

            {/* SETTINGS */}
            <Link
              to="/menu/settings"
              className={`
                flex items-center gap-4
                px-4 py-4
                rounded-2xl
                transition-all duration-300
                shadow-md

                ${
                  location.pathname ===
                  "/menu/settings"
                    ? "bg-[#123274] text-white"
                    : "bg-[#f5f7fc] text-[#123274] hover:bg-[#e8eefc]"
                }
              `}
            >
              <Settings size={22} />

              {sidebarOpen && (
                <span className="font-semibold tracking-wide">
                  Settings
                </span>
              )}
            </Link>
          </div>
        </div>

        {/* =========================================
            MOBILE BOTTOM NAVIGATION
        ========================================= */}
        <div
          className="
            fixed bottom-0 left-0
            w-full
            bg-white
            border-t border-[#d8dfef]
            shadow-[0_-5px_20px_rgba(0,0,0,0.08)]
            z-50
            
            flex md:hidden
            items-center
            justify-around
            
            px-2 py-3
          "
        >
          {/* REPORT */}
          <Link
            to="/menu/report"
            className={`
              flex flex-col items-center justify-center
              gap-1
              px-4 py-2
              rounded-2xl
              transition-all duration-300
              
              ${
                location.pathname ===
                "/menu/report"
                  ? "text-white bg-[#123274]"
                  : "text-[#123274]"
              }
            `}
          >
            <FileText size={20} />

            <span className="text-[11px] font-semibold">
              Report
            </span>
          </Link>

          {/* KPI */}
          <Link
            to="/menu/kpi"
            className={`
              flex flex-col items-center justify-center
              gap-1
              px-4 py-2
              rounded-2xl
              transition-all duration-300
              
              ${
                location.pathname ===
                "/menu/kpi"
                  ? "text-white bg-[#123274]"
                  : "text-[#123274]"
              }
            `}
          >
            <BarChart3 size={20} />

            <span className="text-[11px] font-semibold">
              KPI
            </span>
          </Link>

          {/* SETTINGS */}
          <Link
            to="/menu/settings"
            className={`
              flex flex-col items-center justify-center
              gap-1
              px-4 py-2
              rounded-2xl
              transition-all duration-300
              
              ${
                location.pathname ===
                "/menu/settings"
                  ? "text-white bg-[#123274]"
                  : "text-[#123274]"
              }
            `}
          >
            <Settings size={20} />

            <span className="text-[11px] font-semibold">
              Settings
            </span>
          </Link>
        </div>

        {/* =========================================
            CONTENT
        ========================================= */}
        <div
          className={`
            flex-1
            transition-all duration-300
            
            min-h-[calc(100vh-88px)]
            
            p-3 sm:p-4 md:p-8
            
            pb-28 md:pb-8
            
            ${
              sidebarOpen
                ? "md:ml-[260px]"
                : "md:ml-[85px]"
            }
          `}
        >
          {/* CONTENT AREA */}
          <div
            className="
              bg-white
              rounded-[32px]
              border border-[#dce3f1]
              shadow-xl
              
              min-h-[400px]
              
              p-4 sm:p-6 md:p-10
              
              overflow-x-hidden
            "
          >
            <Outlet />
          </div>
        </div>
      </div>
    </div>
  );
};

export default MenuPage;