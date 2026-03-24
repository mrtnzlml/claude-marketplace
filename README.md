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
| `rossum_list_queues` | List queues (filter by workspace, status) |
| `rossum_get_queue` | Get full queue details |
| `rossum_get_schema` | Get queue schema (datapoints, sections, tables) |
| `rossum_list_hooks` | List hooks/extensions (filter by queue, active) |
| `rossum_get_hook` | Get full hook details including code and config |
| `rossum_get_hook_secret_keys` | List secret key names on a hook |
| `rossum_get_annotation_content` | Get extracted data from an annotation |
| `rossum_list_users` | List organization users |
| `rossum_list_audit_logs` | Query audit logs (admin only) |
| **Data Storage** | |
| `data_storage_healthz` | Check API reachability |
| `data_storage_list_collections` | List collections |
| `data_storage_find` | Query documents with filter/projection/sort |
| `data_storage_aggregate` | Run MongoDB aggregation pipelines |
| `data_storage_list_indexes` | List collection indexes |
| `data_storage_list_search_indexes` | List Atlas Search indexes |
| `data_storage_create_index` | Create a database index *(write)* |
| `data_storage_create_search_index` | Create an Atlas Search index *(write)* |
| `data_storage_drop_index` | Drop a database index *(destructive)* |
| `data_storage_drop_search_index` | Drop an Atlas Search index *(destructive)* |
| `data_storage_update_search_index` | Update an Atlas Search index definition *(write)* |
