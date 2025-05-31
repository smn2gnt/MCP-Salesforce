# /// script
# dependencies = [
#   "mcp",
#   "simple-salesforce",
#   "python-dotenv"
# ]
# ///
import asyncio
import csv
import io
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
                security_token=os.getenv('SALESFORCE_SECURITY_TOKEN'),
                domain=os.getenv('SALESFORCE_DOMAIN')
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

    def get_field_details(self, object_name: str, field_name: str) -> str:
        """Retrieves detailed metadata for a specific field including external ID, unique, required settings.
        
        Args:
            object_name (str): The name of the Salesforce object.
            field_name (str): The API name of the field.
            
        Returns:
            str: JSON representation of the field details.
        """
        if not self.sf:
            raise ValueError("Salesforce connection not established.")
            
        try:
            sf_object = getattr(self.sf, object_name)
            describe_result = sf_object.describe()
            
            # Find the specific field
            field_details = None
            for field in describe_result['fields']:
                if field['name'].lower() == field_name.lower():
                    field_details = {
                        'name': field['name'],
                        'label': field['label'],
                        'type': field['type'],
                        'length': field['length'],
                        'required': not field['nillable'],
                        'unique': field['unique'],
                        'external_id': field['externalId'],
                        'updateable': field['updateable'],
                        'createable': field['createable'],
                        'custom': field['custom'],
                        'calculated': field['calculated'],
                        'defaulted_on_create': field['defaultedOnCreate'],
                        'dependency_following': field['dependentPicklist'],
                        'picklist_values': field['picklistValues'],
                        'referenced_to': field['referenceTo'],
                        'relationship_name': field['relationshipName']
                    }
                    break
                    
            if not field_details:
                # Debug: show all field names containing the search term
                matching_fields = [f['name'] for f in describe_result['fields'] if field_name.lower() in f['name'].lower()]
                return json.dumps({
                    "error": f"Field '{field_name}' not found in object '{object_name}'",
                    "similar_fields": matching_fields[:10]  # Show first 10 similar fields
                }, indent=2)
                
            return json.dumps(field_details, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Failed to get field details: {str(e)}"}, indent=2)

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
        types.Tool(
            name="get_record_types",
            description="Retrieves all record types for a specific SObject.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "The API name of the Salesforce SObject (e.g., 'Account', 'Opportunity')."
                    }
                },
                "required": ["object_name"]
            },
        ),
        types.Tool(
            name="get_user_permissions",
            description="Retrieves current user's permissions for a specific SObject including field-level security.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "The API name of the Salesforce SObject (e.g., 'Account', 'Contact')."
                    }
                },
                "required": ["object_name"]
            },
        ),
        types.Tool(
            name="create_custom_field",
            description="Creates a new custom field on a specified SObject using Tooling API.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "The API name of the Salesforce SObject (e.g., 'Account', 'MyCustomObject__c')."
                    },
                    "field_name": {
                        "type": "string",
                        "description": "The name for the new custom field (without __c suffix)."
                    },
                    "field_type": {
                        "type": "string",
                        "description": "The type of field to create.",
                        "enum": ["Text", "Number", "Date", "DateTime", "Checkbox", "Picklist", "Email", "Phone", "Url", "TextArea", "LongTextArea"]
                    },
                    "field_label": {
                        "type": "string",
                        "description": "The display label for the field."
                    },
                    "length": {
                        "type": "number",
                        "description": "Length for Text fields (optional, default 255)."
                    },
                    "precision": {
                        "type": "number", 
                        "description": "Precision for Number fields (optional)."
                    },
                    "scale": {
                        "type": "number",
                        "description": "Scale for Number fields (optional)."
                    },
                    "required": {
                        "type": "boolean",
                        "description": "Whether the field is required (default false)."
                    },
                    "unique": {
                        "type": "boolean",
                        "description": "Whether the field should be unique (default false)."
                    },
                    "external_id": {
                        "type": "boolean",
                        "description": "Whether the field is an external ID (default false)."
                    }
                },
                "required": ["object_name", "field_name", "field_type", "field_label"]
            },
        ),
        types.Tool(
            name="update_custom_field",
            description="Updates settings of an existing custom field using Tooling API.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "The API name of the Salesforce SObject."
                    },
                    "field_name": {
                        "type": "string", 
                        "description": "The API name of the custom field (with __c suffix)."
                    },
                    "field_label": {
                        "type": "string",
                        "description": "New display label for the field (optional)."
                    },
                    "required": {
                        "type": "boolean",
                        "description": "Whether the field is required (optional)."
                    },
                    "unique": {
                        "type": "boolean",
                        "description": "Whether the field should be unique (optional)."
                    },
                    "external_id": {
                        "type": "boolean", 
                        "description": "Whether the field is an external ID (optional)."
                    }
                },
                "required": ["object_name", "field_name"]
            },
        ),
        types.Tool(
            name="set_field_permissions",
            description="Sets field-level security permissions for a custom field on profiles or permission sets.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "The API name of the Salesforce SObject."
                    },
                    "field_name": {
                        "type": "string",
                        "description": "The API name of the custom field (with __c suffix)."
                    },
                    "permission_set_name": {
                        "type": "string",
                        "description": "The API name of the permission set or profile (optional, defaults to 'System Administrator')."
                    },
                    "readable": {
                        "type": "boolean",
                        "description": "Whether the field is readable (default: true)."
                    },
                    "editable": {
                        "type": "boolean",
                        "description": "Whether the field is editable (default: true)."
                    }
                },
                "required": ["object_name", "field_name"]
            },
        ),
        types.Tool(
            name="get_field_permissions",
            description="Retrieves field-level security permissions for a custom field across all profiles and permission sets.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "The API name of the Salesforce SObject."
                    },
                    "field_name": {
                        "type": "string",
                        "description": "The API name of the field."
                    }
                },
                "required": ["object_name", "field_name"]
            },
        ),
        types.Tool(
            name="get_field_details",
            description="Retrieves detailed metadata for a specific field of a Salesforce object, including external ID, unique, required settings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "The API name of the Salesforce SObject (e.g., 'Account', 'Contact')."
                    },
                    "field_name": {
                        "type": "string",
                        "description": "The API name of the field (e.g., 'GLN__c', 'Name', 'Email')."
                    }
                },
                "required": ["object_name", "field_name"]
            },
        ),
        types.Tool(
            name="export_data_csv",
            description="Export SOQL query results to CSV format",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SOQL query to execute and export"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Optional filename for the CSV file (default: 'export.csv')"
                    }
                },
                "required": ["query"]
            },
        ),
        types.Tool(
            name="list_reports",
            description="Get all available reports and folders in the organization",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder_id": {
                        "type": "string",
                        "description": "Optional folder ID to filter reports (default: all reports)"
                    }
                }
            },
        ),
        types.Tool(
            name="list_users",
            description="Get all users with their profiles, roles, and status",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_inactive": {
                        "type": "boolean",
                        "description": "Include inactive users in results (default: false)"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of users to return (default: 100)"
                    }
                }
            },
        ),
        types.Tool(
            name="get_org_limits",
            description="Get current API usage limits and organizational features",
            inputSchema={
                "type": "object",
                "properties": {}
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
    elif name == "get_record_types":
        object_name = arguments.get("object_name")
        if not object_name:
            raise ValueError("Missing 'object_name' argument")
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")
        
        # Query RecordType object for the specified SObject
        query = f"SELECT Id, Name, DeveloperName, Description, IsActive FROM RecordType WHERE SobjectType = '{object_name}'"
        results = sf_client.sf.query(query)
        
        return [
            types.TextContent(
                type="text",
                text=f"{object_name} Record Types (JSON):\n{json.dumps(results, indent=2)}",
            )
        ]
    elif name == "get_user_permissions":
        object_name = arguments.get("object_name")
        if not object_name:
            raise ValueError("Missing 'object_name' argument")
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")
        
        # Get object describe info which includes user permissions
        sf_object = getattr(sf_client.sf, object_name)
        describe_result = sf_object.describe()
        
        # Extract permission information
        permissions = {
            "object_permissions": {
                "createable": describe_result.get("createable", False),
                "deletable": describe_result.get("deletable", False), 
                "queryable": describe_result.get("queryable", False),
                "updateable": describe_result.get("updateable", False),
                "retrieveable": describe_result.get("retrieveable", False)
            },
            "field_permissions": []
        }
        
        # Get field-level permissions
        for field in describe_result.get("fields", []):
            permissions["field_permissions"].append({
                "name": field["name"],
                "label": field["label"],
                "createable": field.get("createable", False),
                "updateable": field.get("updateable", False),
                "nillable": field.get("nillable", False),
                "filterable": field.get("filterable", False),
                "sortable": field.get("sortable", False)
            })
        
        return [
            types.TextContent(
                type="text",
                text=f"{object_name} User Permissions (JSON):\n{json.dumps(permissions, indent=2)}",
            )
        ]
    elif name == "create_custom_field":
        object_name = arguments.get("object_name")
        field_name = arguments.get("field_name")
        field_type = arguments.get("field_type")
        field_label = arguments.get("field_label")
        
        if not all([object_name, field_name, field_type, field_label]):
            raise ValueError("Missing required arguments: object_name, field_name, field_type, field_label")
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")
        
        # Build field definition based on type
        field_definition = {
            "FullName": f"{object_name}.{field_name}__c",
            "Metadata": {
                "type": field_type,
                "label": field_label,
                "required": arguments.get("required", False),
                "unique": arguments.get("unique", False),
                "externalId": arguments.get("external_id", False)
            }
        }
        
        # Add type-specific properties
        if field_type == "Text":
            field_definition["Metadata"]["length"] = arguments.get("length", 255)
        elif field_type == "Number":
            field_definition["Metadata"]["precision"] = arguments.get("precision", 18)
            field_definition["Metadata"]["scale"] = arguments.get("scale", 0)
        
        # Create field using Tooling API
        try:
            result = sf_client.sf.toolingexecute("sobjects/CustomField", method="POST", data=field_definition)
            return [
                types.TextContent(
                    type="text",
                    text=f"Create Custom Field Result (JSON):\n{json.dumps(result, indent=2)}",
                )
            ]
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error creating custom field: {str(e)}",
                )
            ]
    elif name == "update_custom_field":
        object_name = arguments.get("object_name")
        field_name = arguments.get("field_name")
        
        if not all([object_name, field_name]):
            raise ValueError("Missing required arguments: object_name, field_name")
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")
        
        # First, get the field ID
        query = f"SELECT Id FROM CustomField WHERE TableEnumOrId = '{object_name}' AND DeveloperName = '{field_name.replace('__c', '')}'"
        field_query = sf_client.sf.toolingexecute(f"query?q={query}")
        
        if not field_query.get("records"):
            raise ValueError(f"Custom field {field_name} not found on {object_name}")
        
        field_id = field_query["records"][0]["Id"]
        
        # Build update payload
        update_data = {}
        if "field_label" in arguments:
            update_data["Label"] = arguments["field_label"]
        if "required" in arguments:
            update_data["Required"] = arguments["required"]
        if "unique" in arguments:
            update_data["Unique"] = arguments["unique"]
        if "external_id" in arguments:
            update_data["ExternalId"] = arguments["external_id"]
        
        if not update_data:
            raise ValueError("No update fields provided")
        
        # Update field using Tooling API
        try:
            result = sf_client.sf.toolingexecute(f"sobjects/CustomField/{field_id}", method="PATCH", data=update_data)
            return [
                types.TextContent(
                    type="text",
                    text=f"Update Custom Field Result (JSON):\n{json.dumps(result, indent=2)}",
                )
            ]
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error updating custom field: {str(e)}",
                )
            ]
    
    elif name == "set_field_permissions":
        object_name = arguments.get("object_name")
        field_name = arguments.get("field_name")
        permission_set_name = arguments.get("permission_set_name", "System Administrator")
        readable = arguments.get("readable", True)
        editable = arguments.get("editable", True)
        
        if not object_name or not field_name:
            raise ValueError("Missing 'object_name' or 'field_name' argument for set_field_permissions")
            
        try:
            # First, find the permission set or profile ID
            perm_query = sf_client.sf.toolingexecute(
                f"query/?q=SELECT Id,Name,IsOwnedByProfile FROM PermissionSet WHERE Name='{permission_set_name}'"
            )
            
            if not perm_query.get("records"):
                return [
                    types.TextContent(
                        type="text",
                        text=f"Permission set/profile '{permission_set_name}' not found.",
                    )
                ]
            
            perm_set_id = perm_query["records"][0]["Id"]
            is_profile = perm_query["records"][0]["IsOwnedByProfile"]
            
            # Check if field permission already exists
            field_perm_query = sf_client.sf.toolingexecute(
                f"query/?q=SELECT Id FROM FieldPermissions WHERE ParentId='{perm_set_id}' AND Field='{object_name}.{field_name}'"
            )
            
            field_permission_data = {
                "ParentId": perm_set_id,
                "SobjectType": object_name,
                "Field": f"{object_name}.{field_name}",
                "PermissionsRead": readable,
                "PermissionsEdit": editable
            }
            
            if field_perm_query.get("records"):
                # Update existing permission
                field_perm_id = field_perm_query["records"][0]["Id"]
                result = sf_client.sf.toolingexecute(
                    f"sobjects/FieldPermissions/{field_perm_id}", 
                    method="PATCH", 
                    data=field_permission_data
                )
                action = "updated"
            else:
                # Create new permission
                result = sf_client.sf.toolingexecute(
                    "sobjects/FieldPermissions", 
                    method="POST", 
                    data=field_permission_data
                )
                action = "created"
            
            permission_type = "profile" if is_profile else "permission set"
            
            return [
                types.TextContent(
                    type="text",
                    text=f"Field permissions {action} successfully!\n"
                         f"Field: {object_name}.{field_name}\n"
                         f"{permission_type.title()}: {permission_set_name}\n"
                         f"Readable: {readable}\n"
                         f"Editable: {editable}\n"
                         f"Result: {json.dumps(result, indent=2)}",
                )
            ]
            
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error setting field permissions: {str(e)}",
                )
            ]
    
    elif name == "get_field_permissions":
        object_name = arguments.get("object_name")
        field_name = arguments.get("field_name")
        
        if not object_name or not field_name:
            raise ValueError("Missing 'object_name' or 'field_name' argument for get_field_permissions")
            
        try:
            # Get all field permissions for this field
            field_perms_query = sf_client.sf.toolingexecute(
                f"query/?q=SELECT Id,ParentId,Parent.Name,Parent.IsOwnedByProfile,PermissionsRead,PermissionsEdit,Field FROM FieldPermissions WHERE Field='{object_name}.{field_name}'"
            )
            
            if not field_perms_query.get("records"):
                return [
                    types.TextContent(
                        type="text",
                        text=f"No field permissions found for {object_name}.{field_name}",
                    )
                ]
            
            permissions_list = []
            for perm in field_perms_query["records"]:
                permission_type = "Profile" if perm["Parent"]["IsOwnedByProfile"] else "Permission Set"
                permissions_list.append({
                    "name": perm["Parent"]["Name"],
                    "type": permission_type,
                    "readable": perm["PermissionsRead"],
                    "editable": perm["PermissionsEdit"],
                    "id": perm["ParentId"]
                })
            
            return [
                types.TextContent(
                    type="text",
                    text=f"Field Permissions for {object_name}.{field_name}:\n{json.dumps(permissions_list, indent=2)}",
                )
            ]
            
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error getting field permissions: {str(e)}",
                )
            ]
    
    elif name == "get_field_details":
        object_name = arguments.get("object_name")
        field_name = arguments.get("field_name")
        
        if not object_name or not field_name:
            raise ValueError("Missing 'object_name' or 'field_name' argument for get_field_details")
            
        try:
            result = sf_client.get_field_details(object_name, field_name)
            return [
                types.TextContent(
                    type="text",
                    text=f"Field Details for {object_name}.{field_name} (JSON):\n{result}",
                )
            ]
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error getting field details: {str(e)}",
                )
            ]
    
    elif name == "export_data_csv":
        query = arguments.get("query")
        filename = arguments.get("filename", "export.csv")
        
        if not query:
            raise ValueError("Missing 'query' argument for export_data_csv")
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")
        
        try:
            # Execute SOQL query
            results = sf_client.sf.query_all(query)
            records = results.get("records", [])
            
            if not records:
                return [
                    types.TextContent(
                        type="text",
                        text="No records found for the query. CSV file not created.",
                    )
                ]
            
            # Create CSV content
            output = io.StringIO()
            
            # Get field names (excluding 'attributes')
            field_names = [key for key in records[0].keys() if key != 'attributes']
            
            writer = csv.DictWriter(output, fieldnames=field_names)
            writer.writeheader()
            
            # Write records (excluding 'attributes' field)
            for record in records:
                clean_record = {k: v for k, v in record.items() if k != 'attributes'}
                writer.writerow(clean_record)
            
            csv_content = output.getvalue()
            output.close()
            
            return [
                types.TextContent(
                    type="text",
                    text=f"CSV Export completed successfully!\n\nFilename: {filename}\nRecords exported: {len(records)}\nFields: {', '.join(field_names)}\n\nCSV Content Preview (first 500 chars):\n{csv_content[:500]}{'...' if len(csv_content) > 500 else ''}",
                )
            ]
            
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error exporting data to CSV: {str(e)}",
                )
            ]
    
    elif name == "list_reports":
        folder_id = arguments.get("folder_id")
        
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")
        
        try:
            # Get reports using Analytics REST API
            if folder_id:
                reports_url = f"sobjects/Report?q=SELECT Id,Name,DeveloperName,FolderName,Description,LastRunDate FROM Report WHERE FolderId = '{folder_id}'"
            else:
                reports_url = "sobjects/Report?q=SELECT Id,Name,DeveloperName,FolderName,Description,LastRunDate FROM Report"
            
            # Use REST API to get reports
            reports_result = sf_client.sf.query("SELECT Id,Name,DeveloperName,FolderName,Description,LastRunDate FROM Report ORDER BY FolderName, Name")
            
            # Also get report folders
            folders_result = sf_client.sf.query("SELECT Id,Name,DeveloperName,Type FROM Folder WHERE Type = 'Report' ORDER BY Name")
            
            result_data = {
                "reports": reports_result.get("records", []),
                "folders": folders_result.get("records", []),
                "total_reports": len(reports_result.get("records", [])),
                "total_folders": len(folders_result.get("records", []))
            }
            
            return [
                types.TextContent(
                    type="text",
                    text=f"Reports and Folders (JSON):\n{json.dumps(result_data, indent=2)}",
                )
            ]
            
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error listing reports: {str(e)}",
                )
            ]
    
    elif name == "list_users":
        include_inactive = arguments.get("include_inactive", False)
        limit = arguments.get("limit", 100)
        
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")
        
        try:
            # Build SOQL query for users
            active_filter = "" if include_inactive else "WHERE IsActive = TRUE"
            
            query = f"""
            SELECT Id, Username, FirstName, LastName, Email, IsActive, 
                   Profile.Name, UserRole.Name, LastLoginDate, CreatedDate
            FROM User 
            {active_filter}
            ORDER BY LastName, FirstName
            LIMIT {limit}
            """
            
            users_result = sf_client.sf.query(query)
            
            # Get user count
            count_query = f"SELECT COUNT() FROM User {active_filter}"
            total_count = sf_client.sf.query(count_query)["totalSize"]
            
            result_data = {
                "users": users_result.get("records", []),
                "total_count": total_count,
                "returned_count": len(users_result.get("records", [])),
                "include_inactive": include_inactive,
                "limit": limit
            }
            
            return [
                types.TextContent(
                    type="text",
                    text=f"Users List (JSON):\n{json.dumps(result_data, indent=2)}",
                )
            ]
            
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error listing users: {str(e)}",
                )
            ]
    
    elif name == "get_org_limits":
        if not sf_client.sf:
            raise ValueError("Salesforce connection not established.")
        
        try:
            # Get organization limits from REST API
            limits = sf_client.sf.restful("limits")
            
            # Get additional org info
            org_info = sf_client.sf.query("SELECT Id, Name, OrganizationType, IsSandbox, InstanceName FROM Organization")
            
            result_data = {
                "organization": org_info.get("records", [{}])[0] if org_info.get("records") else {},
                "limits": limits,
                "summary": {
                    "api_requests_used": limits.get("DailyApiRequests", {}).get("Max", 0) - limits.get("DailyApiRequests", {}).get("Remaining", 0),
                    "api_requests_remaining": limits.get("DailyApiRequests", {}).get("Remaining", 0),
                    "api_requests_limit": limits.get("DailyApiRequests", {}).get("Max", 0),
                    "data_storage_used_mb": limits.get("DataStorageMB", {}).get("Max", 0) - limits.get("DataStorageMB", {}).get("Remaining", 0),
                    "data_storage_remaining_mb": limits.get("DataStorageMB", {}).get("Remaining", 0),
                    "data_storage_limit_mb": limits.get("DataStorageMB", {}).get("Max", 0)
                }
            }
            
            return [
                types.TextContent(
                    type="text",
                    text=f"Organization Limits and Info (JSON):\n{json.dumps(result_data, indent=2)}",
                )
            ]
            
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error getting organization limits: {str(e)}",
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
                server_version="0.2.3",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(run())
