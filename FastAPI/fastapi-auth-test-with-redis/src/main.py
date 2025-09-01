from fastapi import FastAPI

from src.app.database import engine

app = FastAPI(
    title="FastAPI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.get("/ping")
async def ping_db():
    try:
        with engine.connect() as conn:
            return {"status": "connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
