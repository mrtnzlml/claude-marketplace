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

### `rossum-data-storage`

An MCP server that wraps the Rossum Data Storage API. Tools: `data_storage_healthz` (connectivity check), `data_storage_set_token` (configure environment and auth), `data_storage_list_collections`, `data_storage_list_indexes`, `data_storage_list_search_indexes`, and `data_storage_aggregate`.

Supports any Rossum environment (e.g. `https://elis.rossum.ai`, `https://customer-dev.rossum.app`). Set `ROSSUM_TOKEN` and optionally `ROSSUM_API_BASE` as environment variables, or provide them interactively via `data_storage_set_token`.

The server starts automatically when the plugin is enabled (requires `python3`).

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
│   └── data-storage/
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
