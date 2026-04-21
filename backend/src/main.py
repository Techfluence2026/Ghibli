import uvicorn
from fastapi import FastAPI

from auth.router import router as auth_router
from prescriptions.router import router as prescriptions_router
from reports.router import router as reports_router

from db.db import ping

app = FastAPI()

app.include_router(auth_router)
app.include_router(prescriptions_router)
app.include_router(reports_router)

@app.get(path="/health", status_code=200)
def health() -> str:
    ping()
    return "OK"


def main():
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
