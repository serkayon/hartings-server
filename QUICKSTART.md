# Hartings Live Demo (Frontend + FastAPI + Simulator)

## Folder Layout

- `frontend/` React dashboard UI
- `backend/app/` FastAPI backend API
- `backend/simulator/` simulator app to change live machine values

## 1) Start Backend API

```bash
cd backend/app
pip install -r requirements.txt
uvicorn main:app --reload --port 5000
```

## 2) Start Simulator App (separate terminal)

```bash
cd backend/simulator
pip install -r requirements.txt
uvicorn app:app --reload --port 5050
```

Open: `http://localhost:5050`

Change values in simulator and save. Backend serves those values to frontend.

## 3) Start Frontend (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

Open: `http://localhost:3000`

Frontend calls backend through Vite proxy (`/api -> http://localhost:5000`).

## Useful API Endpoints

- `GET /api/dashboard`
- `GET /api/analytics`
- `GET /api/report`
- `GET /api/settings`
- `PUT /api/settings/modbus`
- `PUT /api/settings/shifts`
- `POST /api/settings/connect`
- `POST /api/settings/reconnect`
- `POST /api/reset`
