# /// script
# dependencies = [
#   "mcp",
#   "simple-salesforce",
#   "python-dotenv"
# ]
# ///
import asyncio
import json
from typing import Any
import os
from dotenv import load_dotenv

from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceError

import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

class SalesforceMCP:
    def __init__(self, sf_instance: Salesforce):
        self.sf = sf_instance
        self.sobjects_cache: dict[str, Any] = {}

    def fetch_sobjects_list(self) -> dict[str, Any]:
        """Fetches just the list of available SObjects without their full schemas."""
        try:
            sobjects_response = self.sf.describe()
            return {
                obj["name"]: obj for obj in sobjects_response["sobjects"] if obj["queryable"]
            }
        except SalesforceError as e:
            print(f"Error fetching SObjects list: {e}")
            return {}

    def get_sobject_schema(self, sobject_name: str) -> dict[str, Any] | None:
        """Retrieves the schema for a specific SObject, using cache if available."""
        if sobject_name not in self.sobjects_cache:
            try:
                details = self.sf.__getattr__(sobject_name).describe()
                base_info = self.fetch_sobjects_list().get(sobject_name, {})
                base_info["fields"] = details["fields"]
                self.sobjects_cache[sobject_name] = base_info
            except SalesforceError as e:
                print(f"Error fetching schema for {sobject_name}: {e}")
                return None
        return self.sobjects_cache.get(sobject_name)

    def run_soql_query(self, query: str) -> list[dict[str, Any]]:
        """Executes a SOQL query and returns the results."""
        try:
            result = self.sf.query_all(query)
            return result["records"]
        except SalesforceError as e:
            print(f"Error executing SOQL query: {e}")
            return []

# Create a server instance
server = Server("salesforce-mcp")

# Load environment variables
load_dotenv()

# Configure with Salesforce credentials from environment variables
try:
    sf = Salesforce(
        username=os.getenv('SALESFORCE_USERNAME'),
        password=os.getenv('SALESFORCE_PASSWORD'),
        security_token=os.getenv('SALESFORCE_SECURITY_TOKEN')
    )
except Exception as e:
    print(f"Connection failed: {str(e)}")

sf_mcp = SalesforceMCP(sf)

# Add resource capabilities to expose Salesforce object schemas
@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    resources = []
    for name in sf_mcp.fetch_sobjects_list().keys():
        resources.append(
            types.Resource(
                uri=f"salesforce://sobjects/{name}",
                description=f"Schema for Salesforce object: {name}",
                model=None,  # You can specify a model if applicable
            )
        )
    return resources

@server.read_resource()
async def handle_read_resource(uri: str) -> types.ResourceContents:
    if uri.startswith("salesforce://sobjects/"):
        sobject_name = uri.split("/")[-1]
        schema = sf_mcp.get_sobject_schema(sobject_name)
        if schema:
            return types.ResourceContents(
                type="application/json", text=json.dumps(schema)
            )
    raise ValueError(f"Unknown resource: {uri}")

# Add tool capabilities to run SOQL queries
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="run_soql_query",
            description="Executes a SOQL query against Salesforce",
            arguments=[
                types.ToolArgument(
                    name="query",
                    description="The SOQL query to execute",
                    type="string",
                    required=True,
                )
            ],
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, str]) -> list[types.TextContent]:
    if name == "run_soql_query":
        query = arguments.get("query")
        if not query:
            raise ValueError("Missing 'query' argument")

        results = sf_mcp.run_soql_query(query)
        return [
            types.TextContent(
                type="text",
                text=f"SOQL Query Results (JSON):\n{json.dumps(results, indent=2)}",
            )
        ]
    raise ValueError(f"Unknown tool: {name}")

# Add prompt capabilities for common data analysis tasks
@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="summarize_opportunities",
            description="Summarize recent opportunities",
            arguments=[
                types.PromptArgument(
                    name="limit",
                    description="Number of opportunities to summarize",
                    required=False,
                )
            ],
        ),
        types.Prompt(
            name="analyze_account_activity",
            description="Analyze recent activity for a specific account",
            arguments=[
                types.PromptArgument(
                    name="account_id", description="ID of the account", required=True
                )
            ],
        ),
    ]

@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    if name == "summarize_opportunities":
        limit = arguments.get("limit", "5")
        return types.GetPromptResult(
            description="Summarize recent opportunities",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Please summarize the {limit} most recent opportunities from Salesforce. Include details like name, amount, stage, and close date.",
                    ),
                )
            ],
        )
    elif name == "analyze_account_activity":
        account_id = arguments.get("account_id")
        if not account_id:
            raise ValueError("Missing 'account_id' argument")

        return types.GetPromptResult(
            description="Analyze recent activity for a specific account",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Please analyze the recent activity for account ID: {account_id}. Include details about recent contacts, opportunities, and cases related to this account.",
                    ),
                )
            ],
        )

    raise ValueError(f"Unknown prompt: {name}")

async def run():
    async with mcp.server.stdio.stdio_server() as (read, write):
        await server.run(
            read,
            write,
            InitializationOptions(
                server_name="salesforce-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(run())