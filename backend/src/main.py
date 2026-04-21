import uvicorn
from fastapi import FastAPI

from auth.router import router as auth_router

app = FastAPI()

app.include_router(auth_router)


@app.get(path="/health", status_code=200)
def health() -> str:
    return "OK"


def main():
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
