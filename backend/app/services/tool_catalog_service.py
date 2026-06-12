from app.mcp.client import azure_mcp_client
import json


class ToolCatalogService:

    def __init__(self):
        self.catalog = []
        self.catalog_prompt = ""

    def initialize(self):

        catalog = []

        for tool in azure_mcp_client.get_tools():

            catalog.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "args_schema": str(
                        tool.args_schema
                    )
                }
            )

        # actual Python list
        self.catalog = catalog

        # LLM prompt version
        self.catalog_prompt = json.dumps(
            catalog,
            indent=2
        )

    def get_catalog(self):
        return self.catalog

    def get_catalog_prompt(self):
        return self.catalog_prompt


tool_catalog_service = ToolCatalogService()