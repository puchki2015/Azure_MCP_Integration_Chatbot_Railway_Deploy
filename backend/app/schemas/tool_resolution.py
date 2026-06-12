# app/schemas/tool_resolution.py

from pydantic import BaseModel
from typing import Dict, Any


class ToolResolution(BaseModel):
    tool_name: str
    payload: Dict[str, Any]
    requires_approval: bool = True