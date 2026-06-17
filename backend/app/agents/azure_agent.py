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

MySQL pricing guidance:

- If the user asks for Azure Database for MySQL pricing, extract any values already present in the text before asking follow-up questions.
- Do not repeat a question for region, deployment model, tier, or compute generation when the user already stated it.
- Treat these as the required MySQL pricing fields:
  - region
  - deployment_model
  - tier
  - compute_generation
- Use these normalized dropdown values:
  - deployment_model: Single Server, Flexible Server
  - tier: Basic, Burstable, General Purpose, Memory Optimized, Business Critical
  - compute_generation: Gen4, Gen5, Dsv3, Dsv5, Dsv6, Dasv5, Dasv6, Ddsv5, Ddsv6, Esv6, Easv6, Eadsv5, Eadsv6, Edsv5, Edsv6
- If the exact pricing row is not found, retry with a relaxed filter and show all candidate rows.
- Do not invent values.
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
