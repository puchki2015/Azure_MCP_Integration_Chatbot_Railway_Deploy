from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import get_settings

settings = get_settings()


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)

    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)

    return url

engine_options = {
    "pool_pre_ping": True,
    "echo": False
}

if not settings.DATABASE_URL.startswith("sqlite"):
    engine_options.update(
        {
            "pool_size": 20,
            "max_overflow": 40
        }
    )

engine = create_engine(
    _normalize_database_url(settings.DATABASE_URL),
    **engine_options
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
