from app.config.settings import get_settings
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

settings = get_settings()

LANGGRAPH_DB_URL = settings.DATABASE_URL

checkpointer = None
checkpointer_cm = None
