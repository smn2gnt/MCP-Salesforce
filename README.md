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

## Troubleshooting

### `Failed to spawn process: No such file or directory`

Claude Desktop does not inherit your shell's PATH, so it may not find `uvx` even if it works in your terminal. To fix this:

1. Find the full path to `uvx`:
   ```bash
   which uvx
   ```
2. Use the full path as the `"command"` in your config. For example:
   ```json
   "command": "/Users/yourname/.local/bin/uvx"
   ```

Alternatively, create a symlink in a directory Claude Desktop can see:
```bash
sudo ln -s $(which uvx) /usr/local/bin/uvx
```

### Authentication errors / `Salesforce connection failed`

- **Expired access token:** Salesforce access tokens expire (typically 2–12 hours depending on session settings). Generate a fresh one using the Salesforce CLI:
  ```bash
  sf org display --target-org <your-org-alias>
  ```
  Copy the new **Access Token** value into your config and restart Claude Desktop.

- **Wrong domain:** If connecting to a sandbox, make sure `"SALESFORCE_DOMAIN": "test"` is set. Omit it or leave it empty for production orgs.

- **Invalid instance URL:** Verify your `SALESFORCE_INSTANCE_URL` matches your org. You can find it in Setup > Company Information or in the `sf org display` output.

### Server disconnects immediately

Check the Claude Desktop logs for details:
```
~/Library/Logs/Claude/
```

Common causes:
- Missing Python 3.11+ (`uvx` requires it)
- Network issues reaching your Salesforce org
- Malformed JSON in `claude_desktop_config.json` — validate with `python -m json.tool < ~/Library/Application\ Support/Claude/claude_desktop_config.json`
