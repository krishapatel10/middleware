# db/session.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/reviews_db")

# Async engine & session
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

# SINGLE shared Base used by all models
Base = declarative_base()

async def create_tables():
    """Create DB tables (useful for local/dev: python -m create_db)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
