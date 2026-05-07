import React, { useState } from "react";
import { Menu, X, Settings ,Sidebar,BarChart3, FileText,LayoutDashboard,ArrowLeft  } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import Logo from "../assets/logo.png"
const Navbar = () => {
  const [open, setOpen] = useState(false);
const location = useLocation();
const isMenuPage = location.pathname.startsWith("/menu");
  return (
    <>
      <nav
        className="
          fixed top-0 left-0 w-full z-50
          bg-[#f5f6f8]/95
          backdrop-blur-md
          border-b border-[#d8dde7]
          shadow-[0_8px_25px_rgba(15,23,42,0.08)]
        "
      >
        <div
          className="
            h-[78px]
            flex items-center justify-between
            px-3 sm:px-5 lg:px-8
          "
        >
          {/* LEFT SIDE */}
          <div className="flex items-center gap-3">
            
            {/* DUMMY LOGO */}
       {/* REAL LOGO IMAGE */}
<div
  className="
    w-11 h-11
    md:w-14 md:h-14
    rounded-2xl
    overflow-hidden
    shadow-lg
    border border-[#e5e6e7]
    bg-white
    shrink-0
  "
>
  <img
    src={Logo}
    alt="HartingsLogo"
    className="w-full h-full object-cover"
  />
</div>

            {/* TITLE */}
            <div className="flex flex-col leading-tight overflow-hidden">
              <h1
                className="
                  text-[#0f2d6b]
                  font-extrabold
                  tracking-wide
                  text-[11px]
                  sm:text-[16px]
                  md:text-[24px]
                  lg:text-[30px]
                  whitespace-nowrap
                "
              >
                Hartings CNC Traceability System
              </h1>

              <p
                className="
                  text-[#7b88a8]
                  uppercase
                  tracking-[2px]
                  text-[7px]
                  sm:text-[10px]
                  md:text-[12px]
                  font-medium
                "
              >
                Powered by Serkayon
              </p>
            </div>
          </div>

       {/* DESKTOP NAV ITEMS */}
<div className="hidden md:flex items-center gap-5">

  <Link
    to={isMenuPage ? "/" : "/menu"}
    className="
      flex
      items-center gap-2
      bg-[#0f2d6b]
      hover:bg-[#163b86]
      text-white
      px-5 py-3
      rounded-2xl
      shadow-lg
      transition-all duration-300
      font-semibold
      tracking-wide
    "
  >
    {isMenuPage ? (
      <>
        <ArrowLeft className="w-5 h-5" />
        Back to Dashboard
      </>
    ) : (
      <>
        <Sidebar className="w-5 h-5" />
        MENU
      </>
    )}
  </Link>

</div>

          {/* MOBILE HAMBURGER RIGHT SIDE */}
          <button
            onClick={() => setOpen(!open)}
            className="
              flex md:hidden
              w-11 h-11
              rounded-2xl
              bg-[#0f2d6b]
              shadow-lg
              items-center justify-center
              text-white
              shrink-0
            "
          >
            {open ? (
              <X className="w-6 h-6" />
            ) : (
              <Menu className="w-6 h-6" />
            )}
          </button>
        </div>

        {/* MOBILE DROPDOWN */}
        <div
          className={`
            md:hidden
            overflow-hidden
            transition-all duration-500
            ${
              open
                ? "max-h-[350px] opacity-100"
                : "max-h-0 opacity-0"
            }
          `}
        >
          <div
            className="
              px-4 pb-5 pt-2
              bg-[#f5f6f8]
              border-t border-[#dde3ed]
            "
          >
            <div className="flex flex-col gap-3">
              
              {/* DASHBOARD */}
              <Link
                to="/"
                onClick={() => setOpen(false)}
                className="
                  bg-white
                  border border-[#dfe5ee]
                  rounded-2xl
                  px-4 py-3
                  text-[#0f2d6b]
                  font-semibold
                  shadow-sm
                "
              >
                Dashboard
              </Link>

              {/* MENU */}
              <Link
                to="/menu"
                onClick={() => setOpen(false)}
                className="
                  bg-white
                  border border-[#dfe5ee]
                  rounded-2xl
                  px-4 py-3
                  text-[#0f2d6b]
                  font-semibold
                  shadow-sm
                "
              >
                Menu
              </Link>

         
            </div>
          </div>
        </div>
      </nav>

      {/* NAVBAR SPACE */}
      <div className="h-[78px]" />
    </>
  );
};

export default Navbar;

