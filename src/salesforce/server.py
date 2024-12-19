# /// script
# dependencies = [
#   "mcp",
#   "simple-salesforce",
#   "python-dotenv"
# ]
# ///
import asyncio
import json
from typing import Any, Optional
import os
from dotenv import load_dotenv

from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceError

import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

class SalesforceClient:
    """Handles Salesforce operations and caching."""
    
    def __init__(self):
        self.sf: Optional[Salesforce] = None
        self.sobjects_cache: dict[str, Any] = {}

    def connect(self) -> bool:
        """Establishes connection to Salesforce using environment variables.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.sf = Salesforce(
                username=os.getenv('SALESFORCE_USERNAME'),
                password=os.getenv('SALESFORCE_PASSWORD'),
                security_token=os.getenv('SALESFORCE_SECURITY_TOKEN')
            )
            return True
        except Exception as e:
            print(f"Salesforce connection failed: {str(e)}")
            return False

    def run_soql_query(self, query: str) -> list[dict[str, Any]]:
        """Executes a SOQL query and returns the results.
        
        Args:
            query: The SOQL query string to execute
            
        Returns:
            List of records as dictionaries
        """
        if not self.sf:
            print("Error: Salesforce connection not established")
            return []
            
        try:
            result = self.sf.query_all(query)
            return result["records"]
        except SalesforceError as e:
            print(f"Error executing SOQL query: {e}")
            return []

    def run_sosl_search(self, search_query: str) -> list[dict[str, Any]]:
        """Executes a SOSL search and returns the results.
        
        Args:
            search_query: The SOSL search string to execute
            
        Returns:
            List of records as dictionaries
        """
        if not self.sf:
            print("Error: Salesforce connection not established")
            return []
            
        try:
            result = self.sf.search(search_query)
            return result["searchRecords"] if "searchRecords" in result else []
        except SalesforceError as e:
            print(f"Error executing SOSL search: {e}")
            return []

# Create a server instance
server = Server("salesforce-mcp")

# Load environment variables
load_dotenv()

# Configure with Salesforce credentials from environment variables
sf_client = SalesforceClient()
if not sf_client.connect():
    print("Failed to initialize Salesforce connection")
    # Optionally exit here if Salesforce is required
    # sys.exit(1)

# Add tool capabilities to run SOQL queries
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="run_soql_query",
            description="Executes a SOQL query against Salesforce",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SOQL query to execute",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="run_sosl_search",
            description="Executes a SOSL search against Salesforce",
            inputSchema={
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": "The SOSL search to execute (e.g., 'FIND {John Smith} IN ALL FIELDS')",
                    },
                },
                "required": ["search"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, str]) -> list[types.TextContent]:
    if name == "run_soql_query":
        query = arguments.get("query")
        if not query:
            raise ValueError("Missing 'query' argument")

        results = sf_client.run_soql_query(query)
        return [
            types.TextContent(
                type="text",
                text=f"SOQL Query Results (JSON):\n{json.dumps(results, indent=2)}",
            )
        ]
    elif name == "run_sosl_search":
        search = arguments.get("search")
        if not search:
            raise ValueError("Missing 'search' argument")

        results = sf_client.run_sosl_search(search)
        return [
            types.TextContent(
                type="text",
                text=f"SOSL Search Results (JSON):\n{json.dumps(results, indent=2)}",
            )
        ]
    raise ValueError(f"Unknown tool: {name}")

# Add prompt capabilities for common data analysis tasks

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