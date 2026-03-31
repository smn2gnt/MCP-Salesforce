# /// script
# dependencies = [
#   "mcp",
#   "simple-salesforce",
#   "python-dotenv"
# ]
# ///
import asyncio
import json
import csv
import io
from typing import Any, Optional
import os
import shutil
import subprocess
from dotenv import load_dotenv
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceError
from simple_salesforce import SFType

import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio


def _strip_attributes(record: dict) -> dict:
    """Recursively strip 'attributes' metadata from a Salesforce record dict."""
    clean = {}
    for k, v in record.items():
        if k == 'attributes':
            continue
        if isinstance(v, dict):
            clean[k] = _strip_attributes(v)
        else:
            clean[k] = v
    return clean


def format_records(records: list[dict], format_type: str = "csv", include_total: bool = True) -> str:
    """Format Salesforce records in a token-optimized way.

    Args:
        records: List of record dictionaries from Salesforce
        format_type: 'csv' (default, most compact), 'compact' (JSON without attributes), 'json' (full)
        include_total: Whether to include total count in output

    Returns:
        Formatted string representation of records
    """
    total_line = f"Total: {len(records)} records\n" if include_total else ""

    if not records:
        return total_line + "No records found."

    # Strip 'attributes' metadata from all records (fully recursive)
    clean_records = [_strip_attributes(record) for record in records]

    if format_type == "json":
        return total_line + json.dumps(clean_records, indent=2)

    if format_type == "compact":
        return total_line + json.dumps(clean_records, separators=(',', ':'))

    # Default: CSV format (most token-efficient)
    output = io.StringIO()
    # Collect all field names across all records to handle sparse results
    fieldnames = list(dict.fromkeys(k for record in clean_records for k in record))
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    for record in clean_records:
        # Flatten any nested dicts for CSV
        flat_record = {k: json.dumps(v) if isinstance(v, dict) else v for k, v in record.items()}
        writer.writerow(flat_record)

    return total_line + output.getvalue()


class SalesforceClient:
    """Handles Salesforce operations and caching."""
    
    def __init__(self):
        self.sf: Optional[Salesforce] = None
        self.sobjects_cache: dict[str, Any] = {}

    def connect(self) -> bool:
        """Establishes connection to Salesforce using environment variables.

        Supports three authentication methods (checked in order):
        1. OAuth Access Token: SALESFORCE_ACCESS_TOKEN + SALESFORCE_INSTANCE_URL
        2. Client Credentials: SALESFORCE_CLIENT_ID + SALESFORCE_CLIENT_SECRET
        3. Username/Password: SALESFORCE_USERNAME + SALESFORCE_PASSWORD + SALESFORCE_SECURITY_TOKEN

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            domain = os.getenv('SALESFORCE_DOMAIN')

            # Method 1: OAuth Access Token
            access_token = os.getenv('SALESFORCE_ACCESS_TOKEN')
            instance_url = os.getenv('SALESFORCE_INSTANCE_URL')
            domain = os.getenv('SALESFORCE_DOMAIN')
            if access_token and instance_url:
                self.sf = Salesforce(
                    instance_url=instance_url,
                    session_id=access_token,
                    domain=domain
                )
                return True

            cli_auth = self._get_cli_auth()
            if cli_auth:
                self.sf = Salesforce(
                    instance_url=cli_auth['instance_url'],
                    session_id=cli_auth['access_token'],
                )
                return True

            # Method 2: Client Credentials (OAuth 2.0 Client Credentials Flow)
            client_id = os.getenv('SALESFORCE_CLIENT_ID')
            client_secret = os.getenv('SALESFORCE_CLIENT_SECRET')
            if client_id and client_secret:
                self.sf = Salesforce(
                    consumer_key=client_id,
                    consumer_secret=client_secret,
                    domain=domain
                )
                return True

            # Method 3: Username/Password (Legacy)
            self.sf = Salesforce(
                username=os.getenv('SALESFORCE_USERNAME'),
                password=os.getenv('SALESFORCE_PASSWORD'),
                security_token=os.getenv('SALESFORCE_SECURITY_TOKEN'),
                domain=domain
            )
            return True
        except Exception as e:
            print(f"Salesforce connection failed: {str(e)}")
            return False

    def _get_cli_auth(self) -> Optional[dict[str, str]]:
        """Retrieves Salesforce authentication from the Salesforce CLI.

        This method attempts to use either the `sf` or `sfdx` CLI to obtain
        the access token and instance URL for a Salesforce org. If the
        `SALESFORCE_CLI_TARGET_ORG` environment variable is set, its value
        is used to select the target org; otherwise, the CLI default org is
        used.

        Returns:
            Optional[dict[str, str]]: A dictionary containing `access_token`
            and `instance_url` keys if authentication details can be
            retrieved, otherwise `None`.
        """
        target_org = os.getenv("SALESFORCE_CLI_TARGET_ORG")
        sf_cmd = shutil.which("sf")
        sfdx_cmd = shutil.which("sfdx")

        if sf_cmd:
            cmd = [sf_cmd, "org", "display", "--json"]
            if target_org:
                cmd.extend(["--target-org", target_org])
        elif sfdx_cmd:
            cmd = [sfdx_cmd, "force:org:display", "--json"]
            if target_org:
                cmd.extend(["--targetusername", target_org])
        else:
            return None

        try:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            payload = json.loads(result.stdout)
            auth = payload.get("result", {})
            access_token = auth.get("accessToken")
            instance_url = auth.get("instanceUrl")
            if access_token and instance_url:
                return {"access_token": access_token, "instance_url": instance_url}
        except subprocess.TimeoutExpired as e:
            print(f"Salesforce CLI auth lookup timed out: {str(e)}")
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"Salesforce CLI auth lookup failed: {str(e)}")

        return None
    
    def get_object_fields(self, object_name: str) -> str:
        """Retrieves field names and types for a Salesforce object in CSV format.

        Args:
            object_name (str): The name of the Salesforce object.

        Returns:
            str: CSV representation of the object fields.
        """
        if not self.sf:
            raise ValueError("Salesforce connection not established.")
        if object_name not in self.sobjects_cache:
            sf_object = getattr(self.sf, object_name)
            fields = sf_object.describe()['fields']
            self.sobjects_cache[object_name] = fields

        fields = self.sobjects_cache[object_name]
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['name', 'label', 'type', 'updateable'])
        for field in fields:
            writer.writerow([
                field['name'],
                field['label'],
                field['type'],
                field['updateable']
            ])
        return f"Total: {len(fields)} fields\n{output.getvalue()}"

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
            description="""Executes a SOQL query against Salesforce.

TOKEN OPTIMIZATION GUIDELINES:
- Always SELECT only the fields you need (never SELECT *)
- Use LIMIT to restrict results (start with LIMIT 10, increase if needed)
- Use WHERE clauses to filter data server-side
- Default output is CSV format (most token-efficient)
- Use format='json' only when you need nested data structure
- You can always run additional queries if you need more data

Example efficient query: SELECT Id, Name FROM Account WHERE IsActive = true LIMIT 20""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SOQL query to execute. Always include LIMIT clause and select only needed fields.",
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format: 'csv' (default, most compact), 'compact' (JSON no whitespace), 'json' (full JSON)",
                        "enum": ["csv", "compact", "json"],
                        "default": "csv",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="run_sosl_search",
            description="""Executes a SOSL search against Salesforce.

TOKEN OPTIMIZATION: Use RETURNING clause to limit fields and objects.
Example: FIND {searchterm} RETURNING Account(Id, Name), Contact(Id, Name) LIMIT 10""",
            inputSchema={
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": "The SOSL search to execute. Use RETURNING to specify fields and LIMIT for result count.",
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format: 'csv' (default), 'compact', 'json'",
                        "enum": ["csv", "compact", "json"],
                        "default": "csv",
                    },
                },
                "required": ["search"],
            },
        ),
        types.Tool(
            name="get_object_fields",
            description="""Retrieves field names and types for a Salesforce object. Use this to discover available fields before writing SOQL queries.

Output is CSV format: name,label,type,updateable""",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "The Salesforce object API name (e.g., 'Account', 'Contact', 'Store__c')",
                    },
                },
                "required": ["object_name"],
            },
        ),
        types.Tool(
            name="get_record",
            description="""Retrieves a specific record by ID. Returns all fields - prefer SOQL with specific fields for token efficiency.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "The Salesforce object API name (e.g., 'Account', 'Contact')",
                    },
                    "record_id": {
                        "type": "string",
                        "description": "The 15 or 18 character Salesforce record ID",
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format: 'compact' (default), 'json'",
                        "enum": ["compact", "json"],
                        "default": "compact",
                    },
                },
                "required": ["object_name", "record_id"],
            },
        ),
        types.Tool(
            name="create_record",
            description="Creates a new record",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "The name of the Salesforce object (e.g., 'Account', 'Contact')",
                    },
                    "data": {
                        "type": "object",
                        "description": "The data for the new record",
                        "properties": {},
                        "additionalProperties": True,
                    },
                },
                "required": ["object_name", "data"],
            },
        ),
        types.Tool(
            name="update_record",
            description="Updates an existing record",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "The name of the Salesforce object (e.g., 'Account', 'Contact')",
                    },
                    "record_id": {
                        "type": "string",
                        "description": "The ID of the record to update",
                    },
                    "data": {
                        "type": "object",
                        "description": "The updated data for the record",
                        "properties": {},
                        "additionalProperties": True,
                    },
                },
                "required": ["object_name", "record_id", "data"],
            },
        ),
        types.Tool(
            name="delete_record",
            description="Deletes a record",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "The name of the Salesforce object (e.g., 'Account', 'Contact')",
                    },
                    "record_id": {
                        "type": "string",
                        "description": "The ID of the record to delete",
                    },
                },
                "required": ["object_name", "record_id"],
            },
        ),
        types.Tool(
            name="tooling_execute",
            description="Executes a Tooling API request",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The Tooling API endpoint to call (e.g., 'sobjects/ApexClass')",
                    },
                    "method": {
                        "type": "string",
                        "description": "The HTTP method (default: 'GET')",
                        "enum": ["GET", "POST", "PATCH", "DELETE"],
                        "default": "GET",
                    },
                    "data": {
                        "type": "object",
                        "description": "Data for POST/PATCH requests",
                        "properties": {},
                        "additionalProperties": True,
                    },
                },
                "required": ["action"],
            },
        ),
        types.Tool(
            name="apex_execute",
            description="Executes an Apex REST request",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The Apex REST endpoint to call (e.g., '/MyApexClass')",
                    },
                    "method": {
                        "type": "string",
                        "description": "The HTTP method (default: 'GET')",
                        "enum": ["GET", "POST", "PATCH", "DELETE"],
                        "default": "GET",
                    },
                    "data": {
                        "type": "object",
                        "description": "Data for POST/PATCH requests",
                        "properties": {},
                        "additionalProperties": True,
                    },
                },
                "required": ["action"],
            },
        ),
        types.Tool(
            name="restful",
            description="Makes a direct REST API call to Salesforce",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path of the REST API endpoint (e.g., 'sobjects/Account/describe')",
                    },
                    "method": {
                        "type": "string",
                        "description": "The HTTP method (default: 'GET')",
                        "enum": ["GET", "POST", "PATCH", "DELETE"],
                        "default": "GET",
                    },
                    "params": {
                        "type": "object",
                        "description": "Query parameters for the request",
                        "properties": {},
                        "additionalProperties": True,
                    },
                    "data": {
                        "type": "object",
                        "description": "Data for POST/PATCH requests",
                        "properties": {},
                        "additionalProperties": True,
                    },
                },
                "required": ["path"],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, str]) -> list[types.TextContent]:
    if name == "run_soql_query":
        query = arguments.get("query")
        format_type = arguments.get("format", "csv")
        if not query:
            raise ValueError("Missing 'query' argument")

        results = sf_client.sf.query_all(query)
        formatted = format_records(results.get('records', []), format_type)
        return [
            types.TextContent(
                type="text",
                text=formatted,
            )
        ]
    elif name == "run_sosl_search":
        search = arguments.get("search")
        format_type = arguments.get("format", "csv")
        if not search:
            raise ValueError("Missing 'search' argument")

        results = sf_client.sf.search(search)
        # SOSL returns {'searchRecords': [...]}
        records = results.get('searchRecords', [])
        formatted = format_records(records, format_type)
        return [
            types.TextContent(
                type="text",
                text=formatted,
            )
        ]
    elif name == "get_object_fields":
        object_name = arguments.get("object_name")
        if not object_name:
            raise ValueError("Missing 'object_name' argument")
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")
        results = sf_client.get_object_fields(object_name)
        return [
            types.TextContent(
                type="text",
                text=results,
            )
        ]
    elif name == "get_record":
        object_name = arguments.get("object_name")
        record_id = arguments.get("record_id")
        format_type = arguments.get("format", "compact")
        if not object_name or not record_id:
            raise ValueError("Missing 'object_name' or 'record_id' argument")
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")
        sf_object = getattr(sf_client.sf, object_name)
        if not isinstance(sf_object, SFType):
            raise ValueError(f"Invalid Salesforce object name: {object_name}")
        results = sf_object.get(record_id)
        # Strip attributes
        clean = {k: v for k, v in results.items() if k != 'attributes'}
        if format_type == "json":
            text = json.dumps(clean, indent=2)
        else:
            text = json.dumps(clean, separators=(',', ':'))
        return [
            types.TextContent(
                type="text",
                text=text,
            )
        ]
    elif name == "create_record":
        object_name = arguments.get("object_name")
        data = arguments.get("data")
        if not object_name or not data:
            raise ValueError("Missing 'object_name' or 'data' argument")
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")
        sf_object = getattr(sf_client.sf, object_name)
        results = sf_object.create(data)
        return [
            types.TextContent(
                type="text",
                text=f"Create {object_name} Record Result (JSON):\n{json.dumps(results, indent=2)}",
            )
        ]
    elif name == "update_record":
        object_name = arguments.get("object_name")
        record_id = arguments.get("record_id")
        data = arguments.get("data")
        if not object_name or not record_id or not data:
            raise ValueError("Missing 'object_name', 'record_id', or 'data' argument")
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")
        sf_object = getattr(sf_client.sf, object_name)
        results = sf_object.update(record_id, data)
        return [
            types.TextContent(
                type="text",
                text=f"Update {object_name} Record Result: {results}",
            )
        ]
    elif name == "delete_record":
        object_name = arguments.get("object_name")
        record_id = arguments.get("record_id")
        if not object_name or not record_id:
            raise ValueError("Missing 'object_name' or 'record_id' argument")
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")
        sf_object = getattr(sf_client.sf, object_name)
        results = sf_object.delete(record_id)
        return [
            types.TextContent(
                type="text",
                text=f"Delete {object_name} Record Result: {results}",
            )
        ]
    elif name == "tooling_execute":
        action = arguments.get("action")
        method = arguments.get("method", "GET")
        data = arguments.get("data")

        if not action:
            raise ValueError("Missing 'action' argument")
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")

        results = sf_client.sf.toolingexecute(action, method=method, data=data)
        return [
            types.TextContent(
                type="text",
                text=f"Tooling Execute Result (JSON):\n{json.dumps(results, indent=2)}",
            )
        ]

    elif name == "apex_execute":
        action = arguments.get("action")
        method = arguments.get("method", "GET")
        data = arguments.get("data")

        if not action:
            raise ValueError("Missing 'action' argument")
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")

        results = sf_client.sf.apexecute(action, method=method, data=data)
        return [
            types.TextContent(
                type="text",
                text=f"Apex Execute Result (JSON):\n{json.dumps(results, indent=2)}",
            )
        ]
    elif name == "restful":
        path = arguments.get("path")
        method = arguments.get("method", "GET")
        params = arguments.get("params")
        data = arguments.get("data")

        if not path:
            raise ValueError("Missing 'path' argument")
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")

        results = sf_client.sf.restful(path, method=method, params=params, json=data)
        return [
            types.TextContent(
                type="text",
                text=f"RESTful API Call Result (JSON):\n{json.dumps(results, indent=2)}",
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
                server_version="0.1.5",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(run())
