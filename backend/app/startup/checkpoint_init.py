from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.langgraph import checkpointer as cp_module


async def initialize_checkpointer():

    cp_module.checkpointer_cm = (
        AsyncPostgresSaver.from_conn_string(
            cp_module.LANGGRAPH_DB_URL
        )
    )

    cp_module.checkpointer = (
        await cp_module.checkpointer_cm.__aenter__()
    )

    await cp_module.checkpointer.setup()

    print("LangGraph AsyncPostgresSaver initialized")