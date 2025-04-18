# MCP Salesforce Connector

A Model Context Protocol (MCP) server implementation for Salesforce integration, allowing LLMs to interact with Salesforce data through SOQL queries and SOSL searches.

## Features

- Execute SOQL (Salesforce Object Query Language) queries
- Perform SOSL (Salesforce Object Search Language) searches
- Retrieve metadata for Salesforce objects, including field names, labels, and types
- Retrieve, create, update, and delete records
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
    
Replace `SALESFORCE_ACCESS_TOKEN`, `SALESFORCE_INSTANCE_URL` with your oAuth Salesforce credentials.

