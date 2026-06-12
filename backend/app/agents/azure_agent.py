import logging

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.config.settings import get_settings
from app.mcp.client import azure_mcp_client

import app.langgraph.checkpointer as cp_module


settings = get_settings()

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are Azure AI Ops Assistant.

Responsibilities:
- Help users manage Azure resources.
- Use Azure MCP tools whenever required.
- Explain Azure resources clearly.
- Ask clarifying questions when information is missing.

IMPORTANT SAFETY RULES:

Before performing ANY action that can:

- Create resources
- Update resources
- Delete resources
- Restart resources
- Stop resources
- Scale resources
- Change permissions
- Modify networking

You MUST ask for explicit confirmation.

Example:

User:
Create VM vm1

Assistant:
This operation will create Azure resources and may incur cost.

Do you approve this action?

Reply YES to continue.

Only proceed if the user explicitly replies YES.

If user does not confirm:
Do NOT call tools.
Do NOT perform action.
"""



class AzureAgent:

    def __init__(self):
        self.agent = None
        self.initialized = False

    async def initialize(self):

        if self.initialized:
            return


        tools =  azure_mcp_client.get_tools()

        if not tools:
            raise Exception(
                "Azure MCP tools not loaded"
            )

        logger.info(
            f"Loaded {len(tools)} Azure MCP tools"
        )

        llm = ChatOpenAI(
            model=settings.OPENAI_EXECUTION_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0
        )

        self.agent = create_react_agent(
            model=llm,
            tools=tools,
            checkpointer=cp_module.checkpointer
        )

        self.initialized = True

        logger.info("Azure Agent Ready")

    async def invoke(
        self,
        message: str,
        session_id: str,
        memory_context: str | None = None
    ) -> str:

        if not self.initialized:
            raise Exception(
                "Azure Agent not initialized"
            )

        try:

            system_prompt = SYSTEM_PROMPT
            if memory_context:
                system_prompt = (
                    f"{SYSTEM_PROMPT}\n\n"
                    f"Relevant prior session context:\n{memory_context}\n\n"
                    "Use this context when it helps answer the user."
                )

            config = {
                "configurable": {
                "thread_id": session_id
        }
    }

            result = await self.agent.ainvoke(
                {
                    "messages": [
                    (
                        "system",
                        system_prompt
                    ),
                        (
                            "user",
                            message
                        )
                    ]
                },
                config=config
            )

            return result["messages"][-1].content

        except Exception as ex:

            logger.exception(
                "Azure Agent execution failed"
            )

            return (
                "An error occurred while processing "
                f"your request: {str(ex)}"
            )


azure_agent = AzureAgent()
