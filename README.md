# MCP Salesforce Connector

A Model Context Protocol (MCP) server implementation for Salesforce integration, allowing LLMs to interact with Salesforce data through SOQL queries and SOSL searches.

## Features

- Execute SOQL (Salesforce Object Query Language) queries
- Perform SOSL (Salesforce Object Search Language) searches
- Retrieve metadata for Salesforce objects, including field names, labels, and types
- **List all available SObjects** - Discover standard and custom objects
- Retrieve, create, update, and delete records
- **Bulk operations** - Create, update, and delete up to 10,000 records at once
- Execute Tooling API requests
- Execute Apex REST requests
- Make direct REST API calls to Salesforce


## Configuration
### Model Context Protocol

To use this server with the Model Context Protocol, you need to configure it in your `claude_desktop_config.json` file. Add the following entry to the `mcpServers` section:


    {
        "mcpServers": {
            "salesforce": {
            "command": "uvx",
            "args": [
                "--from",
                "mcp-salesforce-connector",
                "salesforce"
            ],
            "env": {
                "SALESFORCE_ACCESS_TOKEN": "SALESFORCE_ACCESS_TOKEN",
                "SALESFORCE_INSTANCE_URL": "SALESFORCE_INSTANCE_URL",
                }
            }
        }
    }
    


**Note on Salesforce Authentication Methods**

This server supports two authentication methods:

- **OAuth (Recommended):** Set `SALESFORCE_ACCESS_TOKEN` and `SALESFORCE_INSTANCE_URL` as environment variables. 
- **Username/Password (Legacy):** If `SALESFORCE_ACCESS_TOKEN` and `SALESFORCE_INSTANCE_URL` are not set, the server will fall back to using `SALESFORCE_USERNAME`, `SALESFORCE_PASSWORD`, and `SALESFORCE_SECURITY_TOKEN`.

## Available Tools

### Query and Search Tools
- **`run_soql_query`** - Execute SOQL queries against Salesforce
- **`run_sosl_search`** - Perform SOSL searches across objects

### Metadata Tools  
- **`get_object_fields`** - Retrieve field metadata for specific objects
- **`list_sobjects`** - List all available SObjects (standard and custom)

### Single Record Operations
- **`get_record`** - Retrieve a specific record by ID
- **`create_record`** - Create a new record
- **`update_record`** - Update an existing record  
- **`delete_record`** - Delete a record

### Bulk Operations
- **`bulk_create_records`** - Create up to 10,000 records in a single operation
- **`bulk_update_records`** - Update up to 10,000 records (must include Id field)
- **`bulk_delete_records`** - Delete up to 10,000 records using record IDs

### Advanced API Tools
- **`tooling_execute`** - Execute Tooling API requests
- **`apex_execute`** - Execute Apex REST requests
- **`restful`** - Make direct REST API calls to Salesforce

## Bulk Operations Details

### Benefits
- **Performance**: Significantly faster than individual record operations
- **API Limits**: Reduces API call consumption 
- **Efficiency**: Handles large datasets in single requests
- **Error Handling**: Provides detailed results for each record in the batch

### Usage Notes
- Bulk operations use Salesforce Bulk API 1.0
- Maximum of 10,000 records per operation
- For update operations, each record must contain the `Id` field
- For delete operations, provide an array of record IDs as strings
- Results include success/failure status for each record in the batch 
