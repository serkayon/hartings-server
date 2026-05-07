#!/usr/bin/env bash
set -e

# Start backend
cd backend/app
python -m uvicorn main:app --reload --port 5000