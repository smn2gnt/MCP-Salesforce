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
            access_token = os.getenv('SALESFORCE_ACCESS_TOKEN')
            instance_url = os.getenv('SALESFORCE_INSTANCE_URL')
            
            if access_token and instance_url:
                self.sf = Salesforce(
                    instance_url=instance_url,
                    session_id=access_token
                )
                return True
            
            self.sf = Salesforce(
                username=os.getenv('SALESFORCE_USERNAME'),
                password=os.getenv('SALESFORCE_PASSWORD'),
                security_token=os.getenv('SALESFORCE_SECURITY_TOKEN')
            )
            return True
        except Exception as e:
            print(f"Salesforce connection failed: {str(e)}")
            return False
    
    def get_object_fields(self, object_name: str) -> str:
        """Retrieves field Names, labels and typesfor a specific Salesforce object.

        Args:
            object_name (str): The name of the Salesforce object.

        Returns:
            str: JSON representation of the object fields.
        """
        if not self.sf:
            raise ValueError("Salesforce connection not established.")
        if object_name not in self.sobjects_cache:
            sf_object = getattr(self.sf, object_name)
            fields = sf_object.describe()['fields']
            filtered_fields = []
            for field in fields:
                filtered_fields.append({
                    'label': field['label'],
                    'name': field['name'],
                    'updateable': field['updateable'],
                    'type': field['type'],
                    'length': field['length'],
                    'picklistValues': field['picklistValues']
                })
            self.sobjects_cache[object_name] = filtered_fields
            
        return json.dumps(self.sobjects_cache[object_name], indent=2)

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
        ),
        types.Tool(
            name="get_object_fields",
            description="Retrieves field Names, labels and types for a specific Salesforce object",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "The name of the Salesforce object (e.g., 'Account', 'Contact')",
                    },
                },
                "required": ["object_name"],
            },
        ),
        types.Tool(
            name="get_record",
            description="Retrieves a specific record by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "The name of the Salesforce object (e.g., 'Account', 'Contact')",
                    },
                    "record_id": {
                        "type": "string",
                        "description": "The ID of the record to retrieve",
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
        types.Tool(
            name="list_sobjects",
            description="Retrieves a list of all available Salesforce SObjects (standard and custom).",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="bulk_create_records",
            description="Creates multiple records of a specified SObject type in bulk.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "The API name of the Salesforce SObject (e.g., 'Account', 'MyCustomObject__c')."
                    },
                    "data": {
                        "type": "array",
                        "description": "A list of records to create. Each record is a dictionary of field names and values.",
                        "items": {
                            "type": "object",
                            "additionalProperties": True
                        }
                    }
                },
                "required": ["object_name", "data"]
            },
        ),
        types.Tool(
            name="bulk_update_records",
            description="Updates multiple records of a specified SObject type in bulk. Each record must have an 'Id' field.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "The API name of the Salesforce SObject (e.g., 'Account', 'MyCustomObject__c')."
                    },
                    "data": {
                        "type": "array",
                        "description": "A list of records to update. Each record is a dictionary of field names and values, and *must* include an 'Id' field.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "Id": {"type": "string", "description": "The ID of the record to update."}
                            },
                            "required": ["Id"],
                            "additionalProperties": True
                        }
                    }
                },
                "required": ["object_name", "data"]
            },
        ),
        types.Tool(
            name="bulk_delete_records",
            description="Deletes multiple records of a specified SObject type in bulk, given their IDs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "The API name of the Salesforce SObject (e.g., 'Account', 'MyCustomObject__c')."
                    },
                    "record_ids": {
                        "type": "array",
                        "description": "A list of record IDs (strings) to delete.",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["object_name", "record_ids"]
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, str]) -> list[types.TextContent]:
    if name == "run_soql_query":
        query = arguments.get("query")
        if not query:
            raise ValueError("Missing 'query' argument")

        results = sf_client.sf.query_all(query)
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

        results = sf_client.sf.search(search)
        return [
            types.TextContent(
                type="text",
                text=f"SOSL Search Results (JSON):\n{json.dumps(results, indent=2)}",
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
                text=f"{object_name} Metadata (JSON):\n{results}",
            )
        ]
    elif name == "get_record":
        object_name = arguments.get("object_name")
        record_id = arguments.get("record_id")
        if not object_name or not record_id:
            raise ValueError("Missing 'object_name' or 'record_id' argument")
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")
        sf_object = getattr(sf_client.sf, object_name)
        results = sf_object.get(record_id)
        return [
            types.TextContent(
                type="text",
                text=f"{object_name} Record (JSON):\n{json.dumps(results, indent=2)}",
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
    elif name == "list_sobjects":
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")
        
        global_describe = sf_client.sf.describe()
        sobject_names = [s['name'] for s in global_describe['sobjects']]
        return [
            types.TextContent(
                type="text",
                text=f"Available SObjects (JSON):\n{json.dumps(sobject_names, indent=2)}",
            )
        ]
    elif name == "bulk_create_records":
        object_name = arguments.get("object_name")
        records_data = arguments.get("data")

        if not object_name or not records_data:
            raise ValueError("Missing 'object_name' or 'data' argument for bulk_create_records")
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")
        if not isinstance(records_data, list):
            raise ValueError("'data' argument must be a list of records for bulk_create_records")

        bulk_op = getattr(sf_client.sf.bulk, object_name)
        results = bulk_op.insert(records_data)

        return [
            types.TextContent(
                type="text",
                text=f"Bulk Create {object_name} Results (JSON):\n{json.dumps(results, indent=2)}",
            )
        ]
    elif name == "bulk_update_records":
        object_name = arguments.get("object_name")
        records_data = arguments.get("data")

        if not object_name or not records_data:
            raise ValueError("Missing 'object_name' or 'data' argument for bulk_update_records")
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")
        if not isinstance(records_data, list):
            raise ValueError("'data' argument must be a list of records for bulk_update_records")
        
        for record in records_data:
            if not isinstance(record, dict) or 'Id' not in record:
                raise ValueError("Each record in 'data' must be an object and include an 'Id' field for bulk updates.")

        bulk_op = getattr(sf_client.sf.bulk, object_name)
        results = bulk_op.update(records_data)

        return [
            types.TextContent(
                type="text",
                text=f"Bulk Update {object_name} Results (JSON):\n{json.dumps(results, indent=2)}",
            )
        ]
    elif name == "bulk_delete_records":
        object_name = arguments.get("object_name")
        record_ids_to_delete = arguments.get("record_ids")

        if not object_name or not record_ids_to_delete:
            raise ValueError("Missing 'object_name' or 'record_ids' argument for bulk_delete_records")
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")
        if not isinstance(record_ids_to_delete, list):
            raise ValueError("'record_ids' argument must be a list of strings for bulk_delete_records")
        
        data_to_delete = []
        for item in record_ids_to_delete:
            if not isinstance(item, str):
                raise ValueError("Each item in 'record_ids' must be a string ID.")
            data_to_delete.append({'Id': item})

        bulk_op = getattr(sf_client.sf.bulk, object_name)
        results = bulk_op.delete(data_to_delete)

        return [
            types.TextContent(
                type="text",
                text=f"Bulk Delete {object_name} Results (JSON):\n{json.dumps(results, indent=2)}",
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
                server_version="0.2.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(run())
