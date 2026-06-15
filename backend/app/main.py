from contextlib import asynccontextmanager
from sqlalchemy import inspect
from sqlalchemy import text

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.api.approvals import router as approval_router

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.speech import router as speech_router

from app.api.debug import router as debug_router

from app.services.tool_catalog_service import (
    tool_catalog_service
)

from app.services.mcp_command_registry import (
    mcp_command_registry
)

from app.services.command_catalog_service import (
    command_catalog_service
)


from app.websocket.chat_ws import (
    router as chat_ws_router
)

from app.middleware.request_id import (
    RequestIdMiddleware
)

from app.api.chat import (
    router as chat_router
)

from app.api.costs import (
    router as costs_router
)


from app.middleware.security import (
    SecurityHeadersMiddleware
)

from app.startup.checkpoint_init import (
    initialize_checkpointer
)

# Database imports
from app.database.base import Base
from app.database.session import engine

# Import models so SQLAlchemy registers them
from app.database.models import (
    User,
    ChatSession,
    ChatMessage,
    ApprovalRequest,
    SessionMemory,
    AuditLog,
    ApprovalActionLog,
    PricingLookupKey,
    PricingSnapshot,
    PriceRefreshRun,
    CostEstimate,
    CostEstimateLine
)

from app.mcp.client import azure_mcp_client
from app.agents.azure_agent import azure_agent

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):

    print("Starting Azure AI Ops...")

    try:

        # Verify DB
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        print("Database connection successful")

        # Create tables
        Base.metadata.create_all(bind=engine)

        inspector = inspect(engine)
        approval_columns = {
            column["name"]
            for column in inspector.get_columns("approval_requests")
        }

        if "decision_reason" not in approval_columns:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE approval_requests "
                        "ADD COLUMN decision_reason TEXT NULL"
                    )
                )

        print("Database schema initialized")

        # Initialize LangGraph checkpoint tables
        await initialize_checkpointer()

        print("LangGraph checkpoint tables initialized")

        # Initialize Azure MCP
        print("Loading Azure MCP Tools...")
        await azure_mcp_client.initialize()

        


        print("Azure MCP Tools Loaded")

        from app.services.mcp_command_registry import (
            mcp_command_registry
                        )
        
        print("Building MCP Command Registry...")

                  

        print("Building Tool Catalog...")
        tool_catalog_service.initialize()

        print("Tool Catalog Ready")

        print("Building Command Catalog...")

        

        print("\n=== COMMAND CATALOG ===")
        print(command_catalog_service.get_catalog_prompt())
        print("=======================\n")

        print("Command Catalog Ready")

        print("Building MCP Command Registry...")

        #---------------------------------
        #####BUILD MCP COMMAND REGISTRY#####
        #---------------------------------

        print("Learning MCP Commands...")

        tools = azure_mcp_client.get_tools()

        for tool in tools:
            try:
                print(f"Learning commands for tool: {tool.name}...")

                result = await tool.ainvoke(
                    {
                        "learn": True
                    }
                )

                if tool.name == "storage":
                    print("\n=== STORAGE TOOL LEARN OUTPUT ===")
                    print(str(result)[:5000])  # Print first 5000 chars
                    print("================================\n")

                mcp_command_registry.build_from_learn_output(
                    tool_name=tool.name,
                    learn_result=str(result)
                )

                command_count = len(
                    mcp_command_registry.get_tool_commands(tool.name)
                )


                print(f"Learned {command_count} commands for tool: {tool.name}")

            except Exception as ex:

                print(
                    f"Failed to learn commands for tool: {tool.name}, error: {ex}"
                )

        print("MCP Command Registry Ready")

        command_catalog_service.build_catalog()


        print("\n=== STORAGE REGISTRY ===")

        storage_cmds = (
            mcp_command_registry.get_tool_commands(
         "storage"
            )
        )

        print(f"Storage Commands Count: {len(storage_cmds)}")

        for cmd in storage_cmds.keys():
            print(cmd)

        print("=========================\n")

        print("\n=== REGISTRY KEYS ===")
        print(list(mcp_command_registry.registry.keys()))
        print("=====================\n")

        # Initialize LangGraph Agent
        print("Loading Azure Agent...")
        await azure_agent.initialize()

        print("Azure Agent Ready")

    except Exception as ex:

        print(f"Startup failed: {ex}")
        raise

    yield

    from app.langgraph import checkpointer as cp_module

    if cp_module.checkpointer_cm:
        await cp_module.checkpointer_cm.__aexit__(
            None,
            None,
            None
        )

    print("Shutting down Azure AI Ops...")


app = FastAPI(
    title="Azure AI Ops",
    lifespan=lifespan
)

app.add_middleware(
    RequestIdMiddleware
)

app.add_middleware(
    SecurityHeadersMiddleware
)

cors_origins = settings.get_cors_origins()

if settings.ENVIRONMENT.lower() in {"prod", "production"} and not cors_origins:
    raise RuntimeError(
        "CORS_ORIGINS must be set in production. "
        "Set it to the Railway frontend domain or custom domain."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(
    health_router,
    prefix="/api/v1"
)

app.include_router(
    auth_router,
    prefix="/api/v1"
)

app.include_router(
    speech_router,
    prefix="/api/v1"
)

app.include_router(
    chat_ws_router,
    prefix="/ws"
)

app.include_router(
    chat_router,
    prefix="/api/v1"
)

app.include_router(
    costs_router,
    prefix="/api/v1"
)


app.include_router(
    approval_router,
    prefix="/api/v1"
)

app.include_router(
    debug_router,
    prefix="/api/v1"
)
