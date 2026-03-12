# Rossum Claude Code Plugin

A [Claude Code plugin](https://code.claude.com/docs/en/plugins) for Rossum.ai workflows. Provides skills for generating Statements of Work, analyzing and documenting customer implementations, and a comprehensive Rossum platform reference that Claude can use automatically.

## Skills

### `/rossum:write-sow`

Generates a Statement of Work document from project requirements. Uses Rossum terminology, future tense ("Rossum will ..."), and defined terms from the legal contract (Cloud Based Technology, Dedicated Engine, Queue, Schema, etc.).

### `/rossum:analyze [path]`

Analyzes a Rossum implementation for common configuration errors and issues. Discovers the full implementation first, then checks for known problems in schemas, automation, extensions, formulas, rules, and deployment. Produces an issue report with severity levels and fix guidance.

### `/rossum:document [path]`

Analyzes a locally downloaded Rossum implementation and produces a queue-focused reference document. Describes every queue's purpose, document type, ingestion method, extension chain, formulas, rules, automation settings, and export destination — giving you a clear picture of what the implementation does at a glance.

### Rossum Reference (auto-loaded)

A comprehensive Rossum.ai platform reference (API, TxScript, Aurora AI, Master Data Hub, extensions, etc.) that Claude loads automatically when relevant. Not invocable as a slash command.

### MongoDB Reference (auto-loaded)

A MongoDB query language reference tailored for Rossum.ai Master Data Hub. Covers find queries, aggregation pipelines, Atlas Search, operators, and practical matching patterns for data matching configurations. Auto-loaded when relevant.

### prd2 Reference (auto-loaded)

A reference for the prd2 CLI tool used to manage Rossum configurations across environments. Covers pull, push, deploy, purge, and hook commands, deploy files, attribute overrides, credentials, and project structure. Auto-loaded when relevant.

## MCP Servers

### `rossum-api`

A read-only MCP server for Rossum APIs. Starts automatically when the plugin is enabled (requires `python3`). Supports any Rossum environment (elis.rossum.ai, *.rossum.app, etc.).

**Connection** — Claude discovers the API token and base URL (e.g. from prd2 project files or by asking the user), then passes them to `rossum_set_token`. The MCP server itself has no knowledge of prd2 or any project structure.

#### Data Storage

| Tool | Description |
|------|-------------|
| `data_storage_healthz` | Check if the Data Storage API is reachable (no auth required). |
| `data_storage_list_collections` | List available collections. Optional `filter` and `nameOnly` (default: true). |
| `data_storage_list_indexes` | List MongoDB indexes on a collection. |
| `data_storage_list_search_indexes` | List Atlas Search indexes on a collection. |
| `data_storage_aggregate` | Run a MongoDB aggregation pipeline. Supports `collectionName`, `pipeline`, `collation`, `let`, `options`. Runtime limited to 120 s. |

#### Rossum API

| Tool | Description |
|------|-------------|
| `rossum_set_token` | Set the API connection. Requires `token` and `baseUrl`. |
| `rossum_list_users` | List all users in the organization. Auto-paginates. Optional `is_active` filter. |
| `rossum_list_audit_logs` | List audit log entries. Filter by date range, user, action type, object type. Auto-paginates up to `max_results` (default 100, max 1000). |

## Installation

### Test locally

```bash
claude --plugin-dir /path/to/rossum-claude-plugin
```

### Install from marketplace

If added to a marketplace, team members can install with:

```bash
claude plugin install rossum@<marketplace-name>
```

### Per-project (shared via git)

Add to `.claude/settings.json`:

```json
{
  "enabledPlugins": ["rossum@<marketplace-name>"]
}
```

## Development

```
rossum-claude-plugin/
├── .claude-plugin/
│   └── plugin.json
├── mcp-servers/
│   └── rossum-api/
│       └── server.py
└── skills/
    ├── analyze/
    │   └── SKILL.md
    ├── document/
    │   └── SKILL.md
    ├── mongodb-reference/
    │   ├── SKILL.md
    │   └── reference.md
    ├── prd-reference/
    │   ├── SKILL.md
    │   └── reference.md
    ├── rossum-reference/
    │   ├── SKILL.md
    │   └── reference.md
    ├── __shared/
    │   └── discovery-checklist.md
    └── write-sow/
        └── SKILL.md
```

To test changes, restart Claude Code with `--plugin-dir`.
