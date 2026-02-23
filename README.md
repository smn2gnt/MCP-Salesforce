# MCP Salesforce Connector (Read-Only)

A read-only fork of [MCP-Salesforce](https://github.com/smn2gnt/MCP-Salesforce). All write, mutate, delete, and code execution tools have been removed so there is zero possibility of an AI agent accidentally modifying Salesforce data.

## Features

- Execute SOQL (Salesforce Object Query Language) queries
- Perform SOSL (Salesforce Object Search Language) searches
- Retrieve metadata for Salesforce objects, including field names, labels, and types
- Retrieve a specific record by ID


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
                "SALESFORCE_DOMAIN": "SALESFORCE_DOMAIN"
                }
            }
        }
    }



**Note on Salesforce Authentication Methods**

This server supports two authentication methods:

- **OAuth (Recommended):** Set `SALESFORCE_ACCESS_TOKEN` and `SALESFORCE_INSTANCE_URL` as environment variables.
- **Username/Password (Legacy):** If `SALESFORCE_ACCESS_TOKEN` and `SALESFORCE_INSTANCE_URL` are not set, the server will fall back to using `SALESFORCE_USERNAME`, `SALESFORCE_PASSWORD`, and `SALESFORCE_SECURITY_TOKEN`.

**Environment Configuration**

- **`SALESFORCE_DOMAIN` (Optional):** Set to `test` to connect to a Salesforce sandbox environment. If not set or left empty, the server will connect to the production environment.
