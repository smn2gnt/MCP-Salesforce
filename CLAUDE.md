# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server implementation for Salesforce integration. The server provides MCP tools that allow LLMs to interact with Salesforce data through SOQL queries, SOSL searches, and REST API operations.

## Architecture

The project follows a simple two-file architecture:

- `src/salesforce/server.py` - Main MCP server implementation with all tools and Salesforce client
- `src/salesforce/__init__.py` - Package entry point that imports and runs the server

### Core Components

**SalesforceClient Class**: Handles Salesforce connection, authentication, and caching. Supports two authentication methods:
- OAuth (recommended): Uses `SALESFORCE_ACCESS_TOKEN` + `SALESFORCE_INSTANCE_URL`
- Username/Password (fallback): Uses `SALESFORCE_USERNAME` + `SALESFORCE_PASSWORD` + `SALESFORCE_SECURITY_TOKEN`

**MCP Server**: Implements 10 tools for Salesforce operations:
- Query tools: `run_soql_query`, `run_sosl_search`
- Metadata: `get_object_fields` 
- CRUD operations: `get_record`, `create_record`, `update_record`, `delete_record`
- Advanced APIs: `tooling_execute`, `apex_execute`, `restful`

## Development Commands

### Building and Publishing
```bash
# Build the package
python -m build

# Install locally for testing
pip install -e .

# Run the server directly
python src/salesforce/server.py

# Run via entry point
salesforce
```

### Testing MCP Server
```bash
# Test with uvx (recommended installation method)
uvx --from mcp-salesforce-connector salesforce

# Test with environment variables
export SALESFORCE_ACCESS_TOKEN="your_token"
export SALESFORCE_INSTANCE_URL="https://your-instance.salesforce.com"
uvx --from mcp-salesforce-connector salesforce
```

## Key Configuration

The server is configured as an MCP server in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "salesforce": {
      "command": "uvx",
      "args": ["--from", "mcp-salesforce-connector", "salesforce"],
      "env": {
        "SALESFORCE_ACCESS_TOKEN": "SALESFORCE_ACCESS_TOKEN",
        "SALESFORCE_INSTANCE_URL": "SALESFORCE_INSTANCE_URL"
      }
    }
  }
}
```

## Dependencies

- `mcp` - Model Context Protocol framework
- `simple-salesforce` - Salesforce API client
- `python-dotenv` - Environment variable management

## Important Notes

- All Salesforce operations require successful authentication via `SalesforceClient.connect()`
- Object metadata is cached in `sobjects_cache` to improve performance
- The server continues running even if initial Salesforce connection fails
- All tool responses are formatted as JSON for consistent parsing