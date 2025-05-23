# /// script
# dependencies = [
#   "fastmcp",
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

from fastmcp import FastMCP

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
mcp = FastMCP(name="salesforce-mcp")

# Load environment variables
load_dotenv()

# Configure with Salesforce credentials from environment variables
sf_client = SalesforceClient()
if not sf_client.connect():
    print("Failed to initialize Salesforce connection")
    # Optionally exit here if Salesforce is required
    # sys.exit(1)

@mcp.tool()
async def run_soql_query(query: str) -> str:
    """Executes a SOQL query against Salesforce"""
    if not query:
        raise ValueError("Missing 'query' argument")
    results = sf_client.sf.query_all(query)
    return f"SOQL Query Results (JSON):\n{json.dumps(results, indent=2)}"

@mcp.tool()
async def run_sosl_search(search: str) -> str:
    """Executes a SOSL search against Salesforce"""
    if not search:
        raise ValueError("Missing 'search' argument")
    results = sf_client.sf.search(search)
    return f"SOSL Search Results (JSON):\n{json.dumps(results, indent=2)}"

@mcp.tool()
async def get_object_fields(object_name: str) -> str:
    """Retrieves field Names, labels and types for a specific Salesforce object"""
    if not object_name:
        raise ValueError("Missing 'object_name' argument")
    if not sf_client.sf:
        raise ValueError("Salesforce connection not established.")
    results = sf_client.get_object_fields(object_name)
    return f"{object_name} Metadata (JSON):\n{results}"

@mcp.tool()
async def get_record(object_name: str, record_id: str) -> str:
    """Retrieves a specific record by ID"""
    if not object_name or not record_id:
        raise ValueError("Missing 'object_name' or 'record_id' argument")
    if not sf_client.sf:
        raise ValueError("Salesforce connection not established.")
    sf_object = getattr(sf_client.sf, object_name)
    results = sf_object.get(record_id)
    return f"{object_name} Record (JSON):\n{json.dumps(results, indent=2)}"

@mcp.tool()
async def create_record(object_name: str, data: dict[str, Any]) -> str:
    """Creates a new record"""
    if not object_name or not data:
        raise ValueError("Missing 'object_name' or 'data' argument")
    if not sf_client.sf:
        raise ValueError("Salesforce connection not established.")
    sf_object = getattr(sf_client.sf, object_name)
    results = sf_object.create(data)
    return f"Create {object_name} Record Result (JSON):\n{json.dumps(results, indent=2)}"

@mcp.tool()
async def update_record(object_name: str, record_id: str, data: dict[str, Any]) -> str:
    """Updates an existing record"""
    if not object_name or not record_id or not data:
        raise ValueError("Missing 'object_name', 'record_id', or 'data' argument")
    if not sf_client.sf:
        raise ValueError("Salesforce connection not established.")
    sf_object = getattr(sf_client.sf, object_name)
    # simple-salesforce returns status code (e.g., 204) on success, not JSON
    results = sf_object.update(record_id, data)
    return f"Update {object_name} Record Result: {results}" 

@mcp.tool()
async def delete_record(object_name: str, record_id: str) -> str:
    """Deletes a record"""
    if not object_name or not record_id:
        raise ValueError("Missing 'object_name' or 'record_id' argument")
    if not sf_client.sf:
        raise ValueError("Salesforce connection not established.")
    sf_object = getattr(sf_client.sf, object_name)
    # simple-salesforce returns status code (e.g., 204) on success, not JSON
    results = sf_object.delete(record_id)
    return f"Delete {object_name} Record Result: {results}"

@mcp.tool()
async def tooling_execute(action: str, method: str = "GET", data: Optional[dict[str, Any]] = None) -> str:
    """Executes a Tooling API request"""
    if not action:
        raise ValueError("Missing 'action' argument")
    if not sf_client.sf:
        raise ValueError("Salesforce connection not established.")
    results = sf_client.sf.toolingexecute(action, method=method, data=data)
    return f"Tooling Execute Result (JSON):\n{json.dumps(results, indent=2)}"

@mcp.tool()
async def apex_execute(action: str, method: str = "GET", data: Optional[dict[str, Any]] = None) -> str:
    """Executes an Apex REST request"""
    if not action:
        raise ValueError("Missing 'action' argument")
    if not sf_client.sf:
        raise ValueError("Salesforce connection not established.")
    results = sf_client.sf.apexecute(action, method=method, data=data)
    return f"Apex Execute Result (JSON):\n{json.dumps(results, indent=2)}"

@mcp.tool()
async def restful(path: str, method: str = "GET", params: Optional[dict[str, Any]] = None, data: Optional[dict[str, Any]] = None) -> str:
    """Makes a direct REST API call to Salesforce"""
    if not path:
        raise ValueError("Missing 'path' argument")
    if not sf_client.sf:
        raise ValueError("Salesforce connection not established.")
    results = sf_client.sf.restful(path, method=method, params=params, json=data)
    return f"RESTful API Call Result (JSON):\n{json.dumps(results, indent=2)}"

# Add prompt capabilities for common data analysis tasks

if __name__ == "__main__":
    mcp.run()
