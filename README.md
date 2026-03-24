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

MCP server (`rossum-api`): access to Rossum APIs and Data Storage. Read-only tools are auto-approved; write tools (index creation) require explicit user approval via MCP tool annotations. Starts automatically when the plugin is enabled.

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
