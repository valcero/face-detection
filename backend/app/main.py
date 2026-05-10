from sqlalchemy import text

from fastapi import FastAPI

from app.db import async_session

app = FastAPI(title="Face ROI API", version="0.1.0")


@app.get("/health")
async def health():
    # Confirms DB connectivity early; helps Compose healthcheck meaningfully reflect readiness.
    async with async_session() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok"}
