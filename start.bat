@echo off
REM Start backend API
cd /d %~dp0backend\app
python -m uvicorn main:app --reload --port 5000