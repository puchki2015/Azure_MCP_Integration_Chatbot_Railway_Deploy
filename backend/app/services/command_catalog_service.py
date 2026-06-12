# app/services/command_catalog_service.py

from app.services.mcp_command_registry import (
    mcp_command_registry
)


class CommandCatalogService:

    def __init__(self):
        self.catalog = ""
        self.catalog_prompt = ""

    def build_catalog(self):

        print("Building command catalog...")

        registry = mcp_command_registry.registry

        lines = []

        for tool_name, commands in registry.items():

            if not commands:
                continue

            lines.append(f"Tool: {tool_name}")

            for command_name in sorted(commands.keys()):

                lines.append(
                    f"  - {command_name}"
                )

            lines.append("")

        self.catalog = "\n".join(lines)

        print("Command Catalog Ready")

    def get_catalog_prompt(self):

        return self.catalog

    def get_commands_for_tool(
        self,
        tool_name: str
    ):

        commands = (
            mcp_command_registry
            .get_tool_commands(tool_name)
        )

        if not commands:
            return ""

        lines = [
            f"Tool: {tool_name}",
            "",
            "Available Commands:"
        ]

        for command_name in sorted(commands.keys()):

            lines.append(
                f"- {command_name}"
            )

        return "\n".join(lines)


command_catalog_service = (
    CommandCatalogService()
)