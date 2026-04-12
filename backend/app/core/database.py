from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    db_url = settings.get_db_url()
    if settings.DB_TYPE == "sqlite":
        return create_async_engine(
            db_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
    # PostgreSQL
    return create_async_engine(db_url, pool_pre_ping=True, echo=False)


engine = _make_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Create all tables (used for SQLite / dev mode)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
