# MediSync

> **🌐 FRONTEND DEPLOYED AT: [app.risb.xyz](https://app.risb.xyz)**

MediSync is a full-stack healthcare management web application that lets patients securely manage prescriptions, lab reports, medications, and health metrics — all in one place. It features AI-powered OCR for document extraction, WhatsApp medication reminders via Twilio, and rich analytics dashboards.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Features](#features)
- [Backend — API Reference](#backend--api-reference)
  - [Authentication](#authentication-apiauthsignin)
  - [Prescriptions](#prescriptions-apiprescriptions)
  - [Reports](#reports-apireports)
  - [Medications & Alerts](#medications--alerts-apimedications)
  - [Metrics / Analytics](#metrics--analytics-apimetrics)
- [Frontend — Pages & Components](#frontend--pages--components)
- [Environment Variables](#environment-variables)
- [Running Locally](#running-locally)
- [Docker & Compose](#docker--compose)
- [Deployment](#deployment)

---

## Overview

MediSync is built for patients who want a unified digital health record. Key capabilities include:

- **Prescription management** — upload image/PDF prescriptions, extract text via Google Document AI OCR, and track status (new / active / expired).
- **Lab report management** — upload reports, auto-extract structured medical data in the background, and review them later.
- **Medication reminders** — schedule medications with specific times; the backend scheduler fires every 60 seconds and sends a personalized WhatsApp message via Twilio at the right time in the user's own timezone.
- **Health metrics / analytics** — track time-series health metrics (e.g., blood sugar, blood pressure) and visualize trends with Chart.js.
- **Secure auth** — JWT-based access tokens + refresh token sessions stored in MongoDB.

---

## Tech Stack

| Layer      | Technology                                                                 |
|------------|----------------------------------------------------------------------------|
| Frontend   | React 19, Vite 8, React Router v7, Chart.js, Three.js / React-Three-Fiber, Axios, Lucide React |
| Backend    | Python 3.14, FastAPI, Uvicorn, APScheduler, PyJWT, Passlib / bcrypt       |
| Database   | MongoDB (PyMongo)                                                          |
| Storage    | AWS S3 (boto3)                                                             |
| AI / OCR   | Google Document AI, OpenAI (groq-compatible)                  |
| Messaging  | Twilio WhatsApp API                                                        |
| Container  | Docker + Docker Compose, Nginx (frontend serving)                         |

---

## Project Structure

```
MediSync/
├── compose.yaml                  # Docker Compose orchestration
├── backend/
│   ├── Dockerfile                # Python 3.14-slim image
│   ├── requirements.txt          # All Python dependencies
│   ├── run.sh                    # Local dev launcher (sets env vars + starts server)
│   └── src/
│       ├── main.py               # FastAPI app entry point, CORS, APScheduler setup
│       ├── auth/                 # User registration, login, token management
│       │   ├── models.py         # User & Session domain classes
│       │   ├── schemas.py        # Pydantic request/response schemas
│       │   ├── services.py       # Business logic (hashing, JWT creation, etc.)
│       │   └── router.py         # Auth API endpoints
│       ├── prescriptions/        # Prescription CRUD + OCR evaluation
│       │   ├── models.py
│       │   ├── schemas.py
│       │   ├── services.py
│       │   └── router.py
│       ├── reports/              # Lab report CRUD + background AI extraction
│       │   ├── models.py
│       │   ├── schemas.py
│       │   ├── services.py
│       │   └── router.py
│       ├── medications/          # Medication CRUD + WhatsApp reminder scheduler
│       │   ├── schemas.py
│       │   ├── services.py       # includes check_and_send_alerts()
│       │   └── router.py
│       ├── metrics/              # Health metrics time-series tracking
│       │   ├── models.py
│       │   ├── schemas.py
│       │   ├── services.py
│       │   └── router.py
│       ├── db/                   # MongoDB connection helpers
│       ├── storage/              # AWS S3 upload/download helpers
│       └── utils/                # Google Document AI OCR utility
│           └── ocr.py
└── frontend/
    ├── Dockerfile                # Multi-stage: Node 20 builder → Nginx 1.27 alpine
    ├── nginx.conf                # SPA routing + port 5173
    ├── vite.config.js
    ├── package.json
    └── src/
        ├── App.jsx               # React Router routes & ProtectedRoute guard
        ├── index.css             # Global design system & utility classes
        ├── main.jsx
        ├── api/
        │   ├── client.js         # Axios instance with auth header injection
        │   └── health.js         # API helper functions for all endpoints
        ├── context/
        │   └── AuthContext.jsx   # Global auth state (login, logout, user)
        ├── components/
        │   ├── Layout.jsx        # App shell wrapping Sidebar + Topbar + Outlet
        │   ├── Sidebar.jsx / .css
        │   ├── Topbar.jsx / .css
        │   ├── GradientBg.jsx    # Animated gradient background
        │   └── ParticleCanvas.jsx# Three.js particle animation
        └── pages/
            ├── Auth.jsx / .css   # Login & sign-up page
            ├── Dashboard.jsx / .css
            ├── Upload.jsx / .css # Prescription & report upload with file preview
            ├── Records.jsx / .css# Browse & manage records
            ├── Analytics.jsx / .css # Health metrics charts
            └── Profile.jsx / .css   # User profile & medication management
```

---

## Features

### 🔐 Authentication
- **Sign up** with email, password, username, and phone number.
- **Login** returns a short-lived JWT access token + a long-lived refresh token.
- **Token renewal** via refresh token; **logout** and **revoke** endpoints to invalidate sessions.
- **Update profile** — age, blood group, diseases, allergies, height, weight, gender, timezone.
- **`GET /api/me`** — fetch the authenticated user's full profile.

### 📄 Prescriptions
- Upload prescription files (JPG, PNG, WEBP, PDF) stored in **AWS S3**.
- Track multiple medications per prescription (name, dose, frequency).
- Status lifecycle: `new` → `active` → `expired`.
- **OCR evaluation** endpoint runs **Google Document AI** on the stored file and returns extracted text on demand.
- Full CRUD: create, list (with optional `?status=` filter + pagination), get by ID, update, delete.

### 🧪 Lab Reports
- Upload lab report PDFs or images to S3.
- Returns immediately; structured medical data is extracted **asynchronously** in the background using AI.
- Status tracking: `pending` → `processing` → `reviewed` → `archived`.
- Full CRUD with status filters and pagination.

### 💊 Medications & WhatsApp Alerts
- Add medications with name, dose, and a list of daily reminder times (HH:MM).
- **APScheduler** job (`check_and_send_alerts`) fires every **60 seconds**.
- Per-user **IANA timezone** support — reminder times match the user's local clock.
- Phone numbers are sanitized to **E.164 format** before sending.
- **Deduplication guard** — a `reminder_log` collection prevents double-sends within the same minute.
- WhatsApp messages sent via **Twilio**.

### 📊 Health Metrics & Analytics
- Create named metric trackers (e.g., "Blood Sugar", "Blood Pressure").
- Append time-stamped readings with `POST /api/metrics/add_value/{metric_id}`.
- Retrieve full history per metric; visualized as charts on the Analytics page.
- Full CRUD: add, list, get by ID, update, add value, delete.

---

## Backend — API Reference

All protected routes require `Authorization: Bearer <access_token>`.

### Authentication (`/api/auth/*`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/signin` | Register a new user |
| `POST` | `/api/auth/login` | Login, returns access + refresh tokens |
| `POST` | `/api/auth/logout` | Invalidate a session by session ID |
| `POST` | `/api/tokens/renew` | Renew access token using refresh token |
| `POST` | `/api/tokens/revoke` | Revoke a refresh token |
| `PUT`  | `/api/user_details` | Update user profile details 🔒 |
| `GET`  | `/api/me` | Get current user's profile 🔒 |
| `GET`  | `/health` | Health check (returns `"OK"`) |

### Prescriptions (`/api/prescriptions`)

| Method | Path | Description |
|--------|------|-------------|
| `POST`   | `/api/prescriptions/add` | Upload a new prescription (multipart form) 🔒 |
| `GET`    | `/api/prescriptions/` | List all my prescriptions (filter + pagination) 🔒 |
| `GET`    | `/api/prescriptions/{id}` | Get a single prescription by ID 🔒 |
| `GET`    | `/api/prescriptions/{id}/evaluate` | Run OCR on the prescription file 🔒 |
| `PUT`    | `/api/prescriptions/update/{id}` | Update prescription fields 🔒 |
| `DELETE` | `/api/prescriptions/delete/{id}` | Delete a prescription 🔒 |

### Reports (`/api/reports`)

| Method | Path | Description |
|--------|------|-------------|
| `POST`   | `/api/reports/add` | Upload a lab report (multipart form) 🔒 |
| `GET`    | `/api/reports/` | List all my reports (filter + pagination) 🔒 |
| `GET`    | `/api/reports/{id}` | Get a single report by ID 🔒 |
| `PUT`    | `/api/reports/update/{id}` | Update report metadata 🔒 |
| `DELETE` | `/api/reports/delete/{id}` | Delete a report 🔒 |

### Medications & Alerts (`/api/medications`)

| Method | Path | Description |
|--------|------|-------------|
| `POST`   | `/api/medications/` | Add a new medication with reminder times 🔒 |
| `GET`    | `/api/medications/` | List all my medications 🔒 |
| `PUT`    | `/api/medications/{id}` | Update a medication 🔒 |
| `DELETE` | `/api/medications/{id}` | Delete a medication 🔒 |

### Metrics / Analytics (`/api/metrics`)

| Method | Path | Description |
|--------|------|-------------|
| `POST`   | `/api/metrics/add` | Create a new metric tracker 🔒 |
| `GET`    | `/api/metrics/` | List all my metrics 🔒 |
| `GET`    | `/api/metrics/{id}` | Get a specific metric with all its values 🔒 |
| `PUT`    | `/api/metrics/update/{id}` | Update metric metadata 🔒 |
| `POST`   | `/api/metrics/add_value/{id}` | Append a new value/reading to a metric 🔒 |
| `DELETE` | `/api/metrics/delete/{id}` | Delete a metric 🔒 |

---

## Frontend — Pages & Components

| Page / Component | Route | Description |
|-----------------|-------|-------------|
| `Auth` | `/auth` | Login and sign-up forms with animated particle background |
| `Dashboard` | `/dashboard` | Overview of recent prescriptions, reports, and medications |
| `Upload` | `/upload` | Upload prescriptions or lab reports with file preview |
| `Records` | `/records` | Browse and manage all prescriptions and reports |
| `Analytics` | `/analytics` | Time-series charts for health metrics (Chart.js) |
| `Profile` | `/profile` | User profile details, medication list management |
| `Sidebar` | — | Navigation sidebar with route links |
| `Topbar` | — | Top bar with user info and actions |
| `GradientBg` | — | Animated CSS gradient background component |
| `ParticleCanvas` | — | Three.js canvas particle animation (auth page) |

---

## Environment Variables

### Backend

| Variable | Description |
|----------|-------------|
| `MONGO_URL` | Full MongoDB connection URI |
| `MONGO_DB_NAME` | MongoDB database name (e.g., `mediDB`) |
| `JWT_SECRET` | Secret key for JWT signing |
| `JWT_ALGORITHM` | JWT algorithm (e.g., `HS256`) |
| `AWS_ACCESS_KEY_ID` | AWS access key for S3 |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for S3 |
| `AWS_DEFAULT_REGION` | AWS region (e.g., `us-east-1`) |
| `S3_BUCKET_NAME` | Name of the S3 bucket for file storage |
| `OPENAI_API_KEY` | OpenAI / Groq-compatible API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `DOCUMENT_AI_KEY` | Google Document AI API key |
| `GCP_PROJECT_ID` | GCP project ID for Document AI |
| `GCP_LOCATION` | GCP location (e.g., `us`) |
| `PROCESSOR_ID` | Document AI processor ID |
| `TWILIO_ACCOUNT_SID` | Twilio account SID for WhatsApp |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_WHATSAPP_NUMBER` | Twilio WhatsApp sender number (E.164) |
| `DEFAULT_USER_TIMEZONE` | Fallback timezone if user has none set (default: `UTC`) |

### Frontend

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Base URL of the backend API (set at Docker build time) |

---

## Running Locally

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables and start server
bash run.sh
```

The API will be available at `http://localhost:8080`.  
Interactive docs: `http://localhost:8080/docs`

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Set the backend URL
echo "VITE_API_BASE_URL=http://localhost:8080" > .env

# Start dev server
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## Docker & Compose

The project ships with a `compose.yaml` that orchestrates three services:

| Service | Image | Port |
|---------|-------|------|
| `mongo` | `mongo:latest` | `27017` |
| `backend` | `risbernfernandes/backend` | `8080` |
| `frontend` | `nickaraujo0/frontend` | `5173` |

All services share a private `medi_network` bridge network. MongoDB data is persisted via a named volume (`mongo_data`).

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

> **Note:** The frontend Docker image requires `VITE_API_BASE_URL` to be passed as a **build-time ARG** (not a runtime env). Rebuild the image if the backend URL changes.

### Building images individually

```bash
# Backend
docker build -t risbernfernandes/backend ./backend

# Frontend (with backend URL)
docker build \
  --build-arg VITE_API_BASE_URL=http://your-backend-url:8080 \
  -t nickaraujo0/frontend ./frontend
```

---

## Deployment

| Component | Details |
|-----------|---------|
| **Frontend** | **[app.risb.xyz](https://app.risb.xyz)** — served via Nginx inside Docker container |
| **Backend** | Docker container (`risbernfernandes/backend`) — exposes port `8080` |
| **Database** | MongoDB container with persistent volume |

The backend serves the FastAPI application directly via Uvicorn on port `8080`. The frontend build is a static React/Vite bundle served by Nginx which also handles client-side routing (all paths fall through to `index.html`).

---

## License

This project was built as part of a hackathon. All rights reserved © 2026 MediSync Team.
