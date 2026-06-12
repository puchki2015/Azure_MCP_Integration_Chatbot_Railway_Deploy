import json
import re

from openai import AsyncOpenAI

from app.config.settings import get_settings
from app.schemas.tool_resolution import ToolResolution
from app.mcp.client import azure_mcp_client
from app.services.mcp_command_registry import (
    mcp_command_registry
)
from app.services.mcp_service import mcp_service


class ToolResolver:

    def __init__(self):

        self.client = AsyncOpenAI()
        self.settings = get_settings()

    def _tokenize(self, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9]+", text.lower())
            if len(token) > 2
        }

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

    def _history_to_text(
        self,
        conversation_history: list[dict] | None,
        limit: int = 6,
        max_chars: int = 400
    ) -> str:
        if not conversation_history:
            return ""

        recent_messages = conversation_history[-limit:]
        lines: list[str] = []

        for message in recent_messages:
            role = str(message.get("role", "unknown")).lower()
            content = str(message.get("content", "")).strip()

            if not content:
                continue

            lines.append(
                f"{role}: {content[:max_chars]}"
            )

        return "\n".join(lines)

    def _get_tool_catalog(self) -> list[dict]:
        catalog = []

        for tool in azure_mcp_client.get_tools():
            catalog.append(
                {
                    "name": tool.name,
                    "description": getattr(tool, "description", "")
                }
            )

        return catalog

    async def _select_tool_family(
        self,
        message: str,
        conversation_history: list[dict] | None = None
    ) -> str | None:
        catalog = self._get_tool_catalog()

        if not catalog:
            return None

        if len(catalog) == 1:
            return catalog[0]["name"]

        history_text = self._history_to_text(conversation_history)

        prompt = f"""
You are selecting the best Azure MCP tool family for the request.

Recent conversation:
{history_text}

Current user message:
{message}

Available tools:
{json.dumps(catalog, separators=(",", ":"))}

Return only JSON in this shape:
{{"tool_name":"..."}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.OPENAI_PLANNER_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ]
            )

            payload = json.loads(
                response.choices[0].message.content
            )
            tool_name = payload.get("tool_name")

            if tool_name and any(
                tool["name"] == tool_name for tool in catalog
            ):
                return tool_name
        except Exception:
            pass

        normalized_message = self._normalize_text(message)
        message_tokens = self._tokenize(message)

        scored_tools: list[tuple[int, str]] = []

        for tool in catalog:
            tool_name = tool["name"]
            description = tool.get("description", "")
            tool_text = self._tokenize(f"{tool_name} {description}")

            score = len(message_tokens & tool_text) * 3

            if tool_name == "arm" and (
                "resource group" in normalized_message
                or "subscription" in normalized_message
                or "azure" in normalized_message
            ):
                score += 12

            if "storage" in normalized_message and "storage" in tool_name:
                score += 12

            if "network" in normalized_message and "network" in tool_name:
                score += 12

            if "vm" in message_tokens or "virtual machine" in normalized_message:
                if "compute" in tool_name or tool_name == "arm":
                    score += 8

            if history_text:
                history_tokens = self._tokenize(history_text)
                score += len(history_tokens & tool_text)

            scored_tools.append((score, tool_name))

        scored_tools.sort(key=lambda item: (item[0], item[1]), reverse=True)

        return scored_tools[0][1] if scored_tools else None

    def _score_command(
        self,
        message_tokens: set[str],
        message_text: str,
        history_tokens: set[str],
        tool_name: str,
        command_name: str,
        command_meta: dict
    ) -> int:
        score = 0

        name_tokens = self._tokenize(
            f"{tool_name} {command_name} {command_meta.get('description', '')}"
        )

        score += len(message_tokens & name_tokens) * 3
        score += len(history_tokens & name_tokens)

        if "resource group" in message_text or "resourcegroup" in message_text:
            if "resource_group" in command_name or "resourcegroup" in command_name:
                score += 20
            if tool_name == "arm":
                score += 10

        if "subscription" in message_tokens and tool_name == "arm":
            score += 5

        if "storage" in message_tokens and "storage" in tool_name:
            score += 10

        if "virtual" in message_tokens or "vm" in message_tokens:
            if tool_name == "arm":
                score += 5

        if command_meta.get("destructive"):
            score += 1

        return score

    def _select_candidate_commands(
        self,
        message: str,
        conversation_history: list[dict] | None = None,
        forced_tool_name: str | None = None,
        limit: int = 12
    ) -> list[dict]:
        message_tokens = self._tokenize(message)
        history_text = self._history_to_text(conversation_history)
        history_tokens = self._tokenize(history_text)
        normalized_message = self._normalize_text(message)
        candidates = []

        for candidate_tool_name, commands in mcp_command_registry.registry.items():
            if forced_tool_name and candidate_tool_name != forced_tool_name:
                continue

            for command_name, command_meta in commands.items():
                score = self._score_command(
                    message_tokens=message_tokens,
                    message_text=normalized_message,
                    history_tokens=history_tokens,
                    tool_name=candidate_tool_name,
                    command_name=command_name,
                    command_meta=command_meta
                )

                candidates.append(
                    {
                        "tool": candidate_tool_name,
                        "command": command_name,
                        "description": command_meta.get("description", ""),
                        "required": command_meta.get("required", []),
                        "optional": command_meta.get("optional", []),
                        "destructive": command_meta.get("destructive", False),
                        "read_only": command_meta.get("read_only", False),
                        "score": score
                    }
                )

        candidates.sort(
            key=lambda item: (
                item["score"],
                1 if item["tool"] == "arm" else 0,
                item["command"]
            ),
            reverse=True
        )

        top_candidates = candidates[:limit]

        if top_candidates and top_candidates[0]["score"] <= 0:
            return candidates[: min(limit, len(candidates))]

        return top_candidates

    async def _resolve_command(
        self,
        message: str,
        conversation_history: list[dict] | None = None,
        tool_name: str | None = None
    ):

        all_commands = self._select_candidate_commands(
            message=message,
            conversation_history=conversation_history,
            forced_tool_name=tool_name
        )

        registry_json = json.dumps(
            all_commands,
            separators=(",", ":")
        )        

        history_text = self._history_to_text(conversation_history)


        prompt = f"""
You are an Azure MCP Command Planner.

Recent conversation:
{history_text}

Available Azure MCP Commands:

{registry_json}

Rules:

1. Return ONLY commands that exists in json.
2. Never invent commands.
3. Use the exact command name.
4. Build parameters from user request.
5. For destructive commands, set requires_approval to true.
6. If required parameters are missing from the user request, return the best command with only known parameters.
7. Return only JSON.

Return:

{{
    "command": "...",
    "parameters": {{}},
    "requires_approval": true
}}
"""

        response = await self.client.chat.completions.create(
            model=self.settings.OPENAI_PLANNER_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": message
                }
            ]
        )

        return json.loads(
            response.choices[0].message.content
        )

    async def resolve(
        self,
        message: str,
        conversation_history: list[dict] | None = None
    ) -> ToolResolution:

        #
        # Resolve Command
        #

        selected_tool = await self._select_tool_family(
            message=message,
            conversation_history=conversation_history
        )

        command_result = await self._resolve_command(
            message=message,
            conversation_history=conversation_history,
            tool_name=selected_tool
        )

        command = command_result.get(
            "command"
        )

        parameters = command_result.get(
            "parameters",
            {}
        )

        requires_approval = command_result.get(
            "requires_approval",
            False
        )


        if not command:
            raise ValueError(
                "Unable to resolve an Azure MCP command from the request"
            )

        resolved_command = (
            mcp_command_registry.resolve_command_name(
                tool_name=selected_tool or "",
                command_name=command
            )
            if selected_tool
            else None
        )

        if not resolved_command:
            resolved_command = (
                mcp_command_registry.resolve_command_name(
                    tool_name="arm",
                    command_name=command
                )
                or mcp_command_registry.resolve_command_name(
                    tool_name="storage",
                    command_name=command
                )
            )

        if resolved_command:
            command = resolved_command

        tool_name = (
            mcp_command_registry
            .find_tool_for_command(
                command
            )
        )

        if not tool_name:
            print("\n=== INVALID COMMAND FROM LLM ===")
            print(f"Returned: {command}")
            print("================================\n")

            raise Exception(
                f"LLM returned invalid command: {command}"
                    )

        valid_commands = (
            mcp_command_registry
            .get_tool_commands(
                tool_name
            )
        )

        print("\n=== COMMAND DEBUG ===")
        print(f"Tool: {tool_name}")
        print(f"Command Returned: {command}")
        print(f"Valid Commands: {list(valid_commands.keys())}")
        print("=====================\n")

        if command not in valid_commands:

            fallback_command = mcp_command_registry.resolve_command_name(
                tool_name=tool_name,
                command_name=command
            )

            if fallback_command and fallback_command in valid_commands:
                command = fallback_command
            else:
                raise Exception(
                    f"Command {command} not found under tool {tool_name}"
                )

        command_meta = valid_commands[command]
        requires_approval = bool(
            command_meta.get("destructive")
            or requires_approval
        )

        payload = {
            "command": command,
            "parameters": parameters
        }

        mcp_service.validate_payload(
            tool_name=tool_name,
            payload=payload
        )

        #
        # Debug
        #

        print("\n=== TOOL RESOLUTION ===")

        print(
            f"User Message: {message}"
        )

        print(
            f"Tool Name: {tool_name}"
        )

        print(
            f"Command: {command}"
        )

        print(
            f"Parameters: {parameters}"
        )

        print(
            f"Requires Approval: {requires_approval}"
        )

        print("=======================\n")

        return ToolResolution(
            tool_name=tool_name,
            payload=payload,
            requires_approval=requires_approval
        )


tool_resolver = ToolResolver()
