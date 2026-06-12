import json
from typing import Any

from fastapi import APIRouter
from fastapi import Depends

from app.auth.dependencies import get_current_app_user
from app.database.models import User
from app.mcp.client import azure_mcp_client
from app.services.command_catalog_service import command_catalog_service
from app.services.mcp_command_registry import mcp_command_registry
from app.services.tool_catalog_service import tool_catalog_service

router = APIRouter(
    tags=["Debug"],
    dependencies=[Depends(get_current_app_user)]
)


def _find_tool(tool_name: str):
    return next(
        (
            tool
            for tool in azure_mcp_client.get_tools()
            if tool.name == tool_name
        ),
        None
    )


@router.get("/debug/tools")
async def debug_tools():
    return tool_catalog_service.get_catalog()


@router.get("/debug/tool/{tool_name}")
async def debug_tool(tool_name: str):
    tool = _find_tool(tool_name)

    if not tool:
        return {
            "error": f"Tool not found: {tool_name}"
        }

    return {
        "name": tool.name,
        "description": getattr(tool, "description", ""),
        "args_schema": str(getattr(tool, "args_schema", {})),
        "metadata": getattr(tool, "metadata", None)
    }


@router.get("/debug/tool/{tool_name}/learn")
async def learn_tool(tool_name: str):
    tool = _find_tool(tool_name)

    if not tool:
        return {
            "error": f"Tool not found: {tool_name}"
        }

    try:
        result = await tool.ainvoke(
            {
                "learn": True
            }
        )

        return {
            "tool": tool.name,
            "description": tool.description,
            "learn_output": json.loads(
                json.dumps(
                    result,
                    default=str
                )
            )
        }
    except Exception as ex:
        return {
            "tool": tool_name,
            "error": str(ex)
        }


@router.get("/debug/tool/{tool_name}/schemas")
async def tool_schemas(tool_name: str) -> dict[str, Any]:
    tool = _find_tool(tool_name)

    if not tool:
        return {
            "error": f"Tool not found: {tool_name}"
        }

    result = {}

    for attr in (
        "args_schema",
        "input_schema",
        "output_schema",
        "metadata",
        "tags",
        "tool_call_schema"
    ):
        try:
            result[attr] = str(getattr(tool, attr, None))
        except Exception as ex:
            result[attr] = str(ex)

    for method in (
        "get_input_jsonschema",
        "get_output_jsonschema"
    ):
        try:
            result[method] = getattr(tool, method)()
        except Exception as ex:
            result[method] = str(ex)

    return result


@router.get("/debug/registry")
async def debug_registry():
    return mcp_command_registry.registry


@router.get("/debug/registry/{tool_name}")
async def debug_registry_tool(tool_name: str):
    return mcp_command_registry.get_tool_commands(
        tool_name
    )


@router.get("/debug/registry/{tool_name}/{command_name}")
async def registry_command(
    tool_name: str,
    command_name: str
):
    return mcp_command_registry.get_command(
        tool_name,
        command_name
    )


@router.get("/debug/commands")
async def debug_commands():
    return command_catalog_service.get_catalog_prompt()
