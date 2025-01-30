# MCP Salesforce Connector

[![smithery badge](https://smithery.ai/badge/mcp-salesforce-connector)](https://smithery.ai/server/mcp-salesforce-connector)

A Model Context Protocol (MCP) server implementation for Salesforce integration, allowing LLMs to interact with Salesforce data through SOQL queries and SOSL searches.

## Features

- Execute SOQL (Salesforce Object Query Language) queries
- Perform SOSL (Salesforce Object Search Language) searches
- Retrieve metadata for Salesforce objects, including field names, labels, and types
- Retrieve, create, update, and delete records
- Execute Tooling API requests
- Execute Apex REST requests
- Make direct REST API calls to Salesforce

## Installation

### Installing via Smithery

To install Salesforce for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mcp-salesforce-connector):

```bash
npx -y @smithery/cli install mcp-salesforce-connector --client claude
```

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
                "SALESFORCE_USERNAME": "YOUR_SALESFORCE_USERNAME",
                "SALESFORCE_PASSWORD": "YOUR_SALESFORCE_PASSWORD",
                "SALESFORCE_SECURITY_TOKEN": "YOUR_SALESFORCE_SECURITY_TOKEN"
                }
            }
        }
    }
    
Replace `YOUR_SALESFORCE_USERNAME`, `YOUR_SALESFORCE_PASSWORD`, and `YOUR_SALESFORCE_SECURITY_TOKEN` with your Salesforce credentials.

