# MCP Salesforce Connector

A comprehensive Model Context Protocol (MCP) server implementation for Salesforce integration, providing **25 specialized tools** for complete Salesforce data management, schema operations, reporting, user management, and field-level security.

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
- **Enhanced metadata tools** - Get record types and user permissions
- **Field-level security management** - Set and retrieve field permissions
- **Schema management** - Create and update custom fields with detailed metadata
- **Data export capabilities** - Export query results to CSV format
- **Reporting and analytics** - Access and execute Salesforce reports
- **User and organization management** - List users and get organizational limits


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
- **`get_record_types`** - Retrieve all record types for a specific SObject
- **`get_user_permissions`** - Get current user's object and field-level permissions

### Single Record Operations
- **`get_record`** - Retrieve a specific record by ID
- **`create_record`** - Create a new record
- **`update_record`** - Update an existing record  
- **`delete_record`** - Delete a record

### Bulk Operations
- **`bulk_create_records`** - Create up to 10,000 records in a single operation
- **`bulk_update_records`** - Update up to 10,000 records (must include Id field)
- **`bulk_delete_records`** - Delete up to 10,000 records using record IDs

### Schema Management Tools
- **`create_custom_field`** - Create new custom fields with various types and settings
- **`update_custom_field`** - Update settings of existing custom fields (unique, external ID, etc.)
- **`get_field_details`** - Retrieve detailed metadata for specific fields including FLS settings

### Field-Level Security Tools
- **`set_field_permissions`** - Set read/edit permissions for fields on profiles or permission sets
- **`get_field_permissions`** - Retrieve current field permissions across all profiles and permission sets

### Data Export Tools
- **`export_data_csv`** - Export SOQL query results to CSV format with customizable filename

### Reporting & Analytics Tools
- **`list_reports`** - Get all available reports and folders in the organization

### User & Organization Management Tools
- **`list_users`** - Get all users with profiles, roles, and status information
- **`get_org_limits`** - Get current API usage limits and organizational features

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

## Enhanced Metadata Features

### Record Types Management
- **`get_record_types`** retrieves all record types for any SObject
- Returns Id, Name, DeveloperName, Description, and IsActive status
- Useful for understanding data model structure and building dynamic UIs

### User Permissions Analysis
- **`get_user_permissions`** provides comprehensive permission analysis
- Object-level permissions: create, read, update, delete, query capabilities
- Field-level security: createable, updateable, nillable, filterable, sortable
- Essential for building permission-aware applications

### Custom Field Management
- **`create_custom_field`** supports multiple field types:
  - Text, Number, Date, DateTime, Checkbox
  - Picklist, Email, Phone, URL, TextArea, LongTextArea
- Configure field properties: unique, external ID, required
- Automatic length/precision handling for different field types

- **`update_custom_field`** allows modification of:
  - Field labels and descriptions
  - Unique constraints
  - External ID settings
  - Required field settings


### Field-Level Security Management

- **`set_field_permissions`** configures field access:
  - Works with both profiles and permission sets
  - Set readable and editable permissions independently
  - Automatically handles existing permission updates

- **`get_field_permissions`** provides visibility into:
  - Current field permissions across all profiles/permission sets
  - Read and edit access levels
  - Permission type (Profile vs Permission Set)

- **`get_field_details`** offers comprehensive field metadata:
  - External ID and unique settings
  - Required field status
  - Field type, length, and constraints
  - Custom field identification

### Usage Notes for Schema Management
- Custom field operations require **System Administrator** or appropriate permissions
- Field creation uses Salesforce Tooling API
- Changes may require deployment in production environments
- Always test schema changes in sandbox environments first
- Field-level security changes take effect immediately

## Complete Tool Reference

### All 25 Available Tools

| Category | Tool Name | Description |
|----------|-----------|-------------|
| **Query & Search** | `run_soql_query` | Execute SOQL queries |
| | `run_sosl_search` | Perform SOSL searches |
| **Metadata** | `get_object_fields` | Get field metadata for objects |
| | `list_sobjects` | List all available SObjects |
| | `get_record_types` | Get record types for SObjects |
| | `get_user_permissions` | Get user's object/field permissions |
| | `get_field_details` | Get detailed field metadata |
| **CRUD Operations** | `get_record` | Retrieve specific record |
| | `create_record` | Create new record |
| | `update_record` | Update existing record |
| | `delete_record` | Delete record |
| **Bulk Operations** | `bulk_create_records` | Create up to 10K records |
| | `bulk_update_records` | Update up to 10K records |
| | `bulk_delete_records` | Delete up to 10K records |
| **Schema Management** | `create_custom_field` | Create custom fields |
| | `update_custom_field` | Update custom field settings |
| **Field Security** | `set_field_permissions` | Set field read/edit permissions |
| | `get_field_permissions` | Get current field permissions |
| **Data Export** | `export_data_csv` | Export query results to CSV |
| **Reporting** | `list_reports` | List available reports and folders |
| **User Management** | `list_users` | Get users with profiles and roles |
| **Organization** | `get_org_limits` | Get API limits and org features |
| **Advanced APIs** | `tooling_execute` | Execute Tooling API requests |
| | `apex_execute` | Execute Apex REST requests |
| | `restful` | Make direct REST API calls | 
