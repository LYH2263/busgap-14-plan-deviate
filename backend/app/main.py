from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.services.seed import backfill_scheduled, seed_if_empty


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # 无迁移框架：旧库补齐计划到站列（create_all 不会改已存在的表）
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE arrivals ADD COLUMN IF NOT EXISTS scheduled_arrive TIMESTAMP"))
    db = SessionLocal()
    try:
        if settings.seed_on_empty:
            seed_if_empty(db)
        # 对已种过数据的旧库，也按 计划发车+站序×单站运行分钟 回填缺失的计划到站
        backfill_scheduled(db)
    finally:
        db.close()
    yield


app = FastAPI(title="BusGap", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")
