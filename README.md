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

MCP server (`rossum-api`): read-only access to Rossum APIs and Data Storage. Starts automatically when the plugin is enabled.

### `rossum`

Document processing for transactional workflows.

| Skill | Description |
|-------|-------------|
| `/rossum:document-processing` | Extract structured data from invoices, POs, and receipts with validation and anomaly detection |

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
