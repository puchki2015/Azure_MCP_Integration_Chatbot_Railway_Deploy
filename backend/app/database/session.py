from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import get_settings

settings = get_settings()

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
    settings.DATABASE_URL,
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
