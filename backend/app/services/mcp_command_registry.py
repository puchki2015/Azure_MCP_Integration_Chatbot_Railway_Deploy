import ast
import json
import re


class MCPCommandRegistry:

    def __init__(self):

        self.registry = {}

    def build_from_learn_output(
        self,
        tool_name: str,
        learn_result: str
    ):

        try:

            # Azure MCP returns:
            # "[{'type':'text','text':'....'}]"

            outer = ast.literal_eval(
                learn_result
            )

            if not outer:
                return

            text_payload = outer[0]["text"]

            start = text_payload.find("[{")

            if start < 0:
                return

            commands_json = text_payload[start:]

            commands = json.loads(
                commands_json
            )

            self.registry[tool_name] = {}

            for cmd in commands:

                props = (
                    cmd
                    .get(
                        "inputSchema",
                        {}
                    )
                    .get(
                        "properties",
                        {}
                    )
                )

                required = (
                    cmd
                    .get(
                        "inputSchema",
                        {}
                    )
                    .get(
                        "required",
                        []
                    )
                )

                optional = [
                    p
                    for p in props.keys()
                    if p not in required
                ]

                self.registry[tool_name][
                    cmd["name"]
                ] = {
                    "description":
                        cmd.get(
                            "description",
                            ""
                        ),

                    "required":
                        required,

                    "optional":
                        optional,

                    "parameters":
                        props,

                    "destructive":
                        bool(
                            cmd.get(
                                "annotations",
                                {}
                            ).get(
                                "destructiveHint",
                                False
                            )
                        ),

                    "read_only":
                        bool(
                            cmd.get(
                                "annotations",
                                {}
                            ).get(
                                "readOnlyHint",
                                False
                            )
                        )
                }

        except Exception as ex:

            print(
                f"Registry build failed: {ex}"
            )

    def get_tool_commands(
        self,
        tool_name: str
    ):

        return self.registry.get(
            tool_name,
            {}
        )

    def get_command(
        self,
        tool_name: str,
        command_name: str
    ):

        return (
            self.registry
            .get(tool_name, {})
            .get(command_name)
        )

    def _normalize_name(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    def resolve_command_name(
        self,
        tool_name: str,
        command_name: str
    ) -> str | None:

        commands = self.get_tool_commands(tool_name)

        if not commands:
            return None

        if command_name in commands:
            return command_name

        normalized = self._normalize_name(command_name)

        for name in commands:
            if self._normalize_name(name) == normalized:
                return name

        alias_map = {
            "azgroupcreate": "create_or_update_resource_group",
            "azgroupupdate": "create_or_update_resource_group",
            "createresourcegroup": "create_or_update_resource_group",
            "updateresourcegroup": "create_or_update_resource_group",
            "resourcegroupcreate": "create_or_update_resource_group",
            "resourcegroupupdate": "create_or_update_resource_group"
        }

        mapped = alias_map.get(normalized)
        if mapped and mapped in commands:
            return mapped

        if tool_name == "arm" and (
            "group" in normalized
            and ("create" in normalized or "update" in normalized)
        ):
            for name, meta in commands.items():
                description = str(meta.get("description", "")).lower()
                if (
                    "resource group" in name.lower()
                    or "resource group" in description
                ):
                    return name

        return None

    def get_registry_prompt(self):

        return json.dumps(
        self.registry,
        indent=2
    )

    def find_tool_for_command(
            self,
            command_name:str
    ):
        for tool_name, commands in self.registry.items():

            if command_name in commands:
                return tool_name

        return None


mcp_command_registry = MCPCommandRegistry()
