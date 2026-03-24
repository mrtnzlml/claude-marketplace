# Rossum Claude Code Plugin Marketplace

A [Claude Code plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces) for Rossum.ai workflows.

## Plugins

### `rossum-sa`

Skills, references, and MCP tools for Rossum implementations.

| Skill | Description |
|-------|-------------|
| `/rossum-sa:write-sow` | Generate a Statement of Work from project requirements |
| `/rossum-sa:analyze [path]` | Check an implementation for configuration errors |
| `/rossum-sa:document [path]` | Produce a queue-focused reference document |
| `/rossum-sa:implement` | Plan and execute an integration project end-to-end |
| `/rossum-sa:upgrade [path]` | Upgrade deprecated extensions to modern formula fields |

Autoloaded references: Rossum platform, MongoDB, Master Data Hub, Data Storage API, TxScript & Serverless Functions, SAP Integration, prd2 CLI.

MCP server (`rossum-api`) — starts automatically when the plugin is enabled. Write tools require explicit user approval. See [MCP tools](#mcp-tools-rossum-api) below.

### `rossum`

Document processing for transactional workflows.

| Skill | Description |
|-------|-------------|
| `/rossum:document-processing` | Extract structured data from invoices, POs, and receipts with validation and anomaly detection |

## Prompt examples

> *Take the fuzzy match (`$search`) present in the "MDH (PO/GRN positions, Entity, MoO)" extension and run it against the MDH collections to fine-tune the matching score (`__searchScore`). The goal is to return as accurate documents as possible while correctly filtering garbage out. Use at least 100 MDH samples.*

> *Analyze all available audit logs for the last year and print a histogram of user activity. Highlight suspicious patterns.*

> *Are all indexes and search indexes set correctly on this project?*

### MCP tool integration test

```
Call rossum_set_token with the provided token and base URL, then systematically test every MCP tool
against the live API. For each tool:

1. Call it with valid arguments derived from real data (use IDs from list endpoints to feed into
   get endpoints; use existing collection names for Data Storage calls).
2. For write/destructive tools (create_index, create_search_index, update_search_index, drop_index,
   drop_search_index): create a temporary test resource, verify it exists, then clean it up.
3. Record pass/fail for each tool.

If a tool fails, diagnose whether the bug is in the server code (wrong field names, incorrect API path,
bad request body shape) or a real API error. Fix server bugs in-place — update server.py, server_test.py,
and README.md in the same pass. Run `pytest` after every fix.

After all tools pass, evaluate coverage gaps: are there Rossum API endpoints that would be high-value
additions for an SA debugging implementations? If so, add them (with tests and README updates).

Token: <ROSSUM_API_TOKEN>
Base URL: https://elis.rossum.ai
```

## Installation

```bash
# Add the marketplace
/plugin marketplace add mrtnzlml/claude-marketplace

# Install a plugin
/plugin install rossum-sa@mrtnzlml-claude-marketplace
/plugin install rossum@mrtnzlml-claude-marketplace
```

Test locally:

```bash
claude --plugin-dir /path/to/claude-marketplace/plugins/rossum-sa
claude --plugin-dir /path/to/claude-marketplace/plugins/rossum
```

Per-project (`.claude/settings.json`):

```json
{
  "enabledPlugins": [
    "rossum-sa@mrtnzlml-claude-marketplace",
    "rossum@mrtnzlml-claude-marketplace"
  ]
}
```

## MCP tools (`rossum-api`)

| Tool | Description |
|------|-------------|
| **Connection** | |
| `rossum_set_token` | Authenticate with a Rossum environment |
| `rossum_whoami` | Show authenticated user, organization, and role |
| **Rossum API** | |
| `rossum_list_workspaces` | List workspaces |
| `rossum_get_workspace` | Get full workspace details |
| `rossum_list_queues` | List queues (filter by workspace, status) |
| `rossum_get_queue` | Get full queue details |
| `rossum_get_schema` | Get queue schema (datapoints, sections, tables) |
| `rossum_list_schemas` | List all schemas |
| `rossum_list_hooks` | List hooks/extensions (filter by queue, active) |
| `rossum_get_hook` | Get full hook details including code and config |
| `rossum_get_hook_secret_keys` | List secret key names on a hook |
| `rossum_list_annotations` | List annotations in a queue (filter by status) |
| `rossum_get_annotation` | Get annotation metadata, messages, and state |
| `rossum_get_annotation_content` | Get extracted data from an annotation |
| `rossum_get_document` | Get document metadata (filename, MIME type) |
| `rossum_get_inbox` | Get inbox details (email address, config) |
| `rossum_list_connectors` | List export connectors (filter by queue) |
| `rossum_get_connector` | Get full connector details |
| `rossum_get_organization` | Get organization details and feature flags |
| `rossum_list_users` | List organization users |
| `rossum_list_audit_logs` | Query audit logs (admin only) |
| **Data Storage** | |
| `data_storage_healthz` | Check API reachability |
| `data_storage_list_collections` | List collections |
| `data_storage_find` | Query documents with filter/projection/sort |
| `data_storage_aggregate` | Run MongoDB aggregation pipelines |
| `data_storage_list_indexes` | List collection indexes |
| `data_storage_list_search_indexes` | List Atlas Search indexes |
| `data_storage_create_index` | :pencil2: Create a database index |
| `data_storage_create_search_index` | :pencil2: Create an Atlas Search index |
| `data_storage_drop_index` | :warning: Drop a database index |
| `data_storage_drop_search_index` | :warning: Drop an Atlas Search index |

:pencil2: = write (requires approval) · :warning: = destructive (requires approval)
