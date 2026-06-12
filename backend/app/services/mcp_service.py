import json

from app.mcp.client import azure_mcp_client
from app.services.mcp_command_registry import mcp_command_registry


class MCPPayloadError(ValueError):
    pass


class MCPService:

    def validate_payload(
        self,
        tool_name: str,
        payload: dict
    ) -> dict:

        if not isinstance(payload, dict):
            raise MCPPayloadError(
                "MCP payload must be a JSON object"
            )

        command = payload.get("command")
        parameters = payload.get("parameters", {})

        if not command:
            raise MCPPayloadError(
                "MCP payload is missing command"
            )

        if not isinstance(parameters, dict):
            raise MCPPayloadError(
                "MCP payload parameters must be a JSON object"
            )

        command_meta = mcp_command_registry.get_command(
            tool_name,
            command
        )

        if not command_meta:
            raise MCPPayloadError(
                f"Command {command} is not registered for tool {tool_name}"
            )

        missing = [
            name
            for name in command_meta.get("required", [])
            if parameters.get(name) in (None, "")
        ]

        if missing:
            raise MCPPayloadError(
                "MCP payload is missing required parameter(s): "
                + ", ".join(missing)
            )

        return {
            "command": command,
            "parameters": parameters
        }

    async def call_tool(
        self,
        tool_name: str,
        payload: dict
    ):

        tools = azure_mcp_client.get_tools()

        tool = next(
            (
                t
                for t in tools
                if t.name == tool_name
            ),
            None
        )

        if not tool:
            raise Exception(
                f"Tool not found: {tool_name}"
            )

        tool_args = self.validate_payload(
            tool_name=tool_name,
            payload=payload
        )

        print("\n=== MCP EXECUTION ===")
        print("TOOL:", tool_name)
        print("ARGS:", json.dumps(tool_args, indent=2, default=str))
        print("=====================\n")

        result = await tool.ainvoke(tool_args)

        return result


mcp_service = MCPService()
