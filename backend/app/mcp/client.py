import os
from typing import List, Optional

from langchain_mcp_adapters.client import (
    MultiServerMCPClient
)


class AzureMCPClient:

    def __init__(self):

        self._client: Optional[
            MultiServerMCPClient
        ] = None

        self._tools = []

        self._initialized = False

    async def initialize(self):

        if self._initialized:
            return

        print(
            "Initializing Azure MCP Client..."
        )

        self._client = MultiServerMCPClient(
            {
                "azure": {
                    "command": "npx",
                    "args": [
                        "-y",
                        os.getenv(
                            "AZURE_MCP_PACKAGE",
                            "@azure/mcp@latest"
                        ),
                        "server",
                        "start",
                        "--dangerously-disable-elicitation"
                    ],
                    "transport": "stdio",
                    "env": {
                        "AZURE_TENANT_ID":
                            os.getenv(
                                "AZURE_TENANT_ID"
                            ),
                        "AZURE_CLIENT_ID":
                            os.getenv(
                                "AZURE_CLIENT_ID"
                            ),
                        "AZURE_CLIENT_SECRET":
                            os.getenv(
                                "AZURE_CLIENT_SECRET"
                            ),
                        "AZURE_SUBSCRIPTION_ID":
                            os.getenv(
                                "AZURE_SUBSCRIPTION_ID"
                            )
                    }
                }
            }
        )

        self._tools = await self._client.get_tools()

        print(
            f"Loaded {len(self._tools)} Azure MCP tools"
        )

        self._initialized = True

    def get_tools(self):

        if not self._initialized:

            raise RuntimeError(
                "Azure MCP Client not initialized"
            )

        return self._tools

    def is_initialized(self):

        return self._initialized

    async def health_check(self):

        try:

            if not self._initialized:
                return False

            return len(self._tools) > 0

        except Exception:

            return False


azure_mcp_client = AzureMCPClient()
