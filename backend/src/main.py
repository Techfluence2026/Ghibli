import uvicorn
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth.router import router as auth_router
from db.db import ping
from medications.router import router as medications_router
from medications.services import check_and_send_alerts
from metrics.router import router as metrics_router
from prescriptions.router import router as prescriptions_router
from reports.router import router as reports_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_and_send_alerts, "interval", seconds=60)
    scheduler.start()
    yield
    # Shutdown
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(prescriptions_router)
app.include_router(reports_router)
app.include_router(metrics_router)
app.include_router(medications_router)


@app.get(path="/health", status_code=200)
def health() -> str:
    return "OK"


def main():
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
