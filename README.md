# Rossum Claude Code Plugin

A [Claude Code plugin](https://code.claude.com/docs/en/plugins) for Rossum.ai workflows. Provides skills for generating Statements of Work, analyzing and documenting customer implementations, and a comprehensive Rossum platform reference that Claude can use automatically.

## Skills

### `/rossum:write-sow`

Generates a Statement of Work document from project requirements. Uses Rossum terminology, future tense ("Rossum will ..."), and defined terms from the legal contract (Cloud Based Technology, Dedicated Engine, Queue, Schema, etc.).

### `/rossum:analyze [path]`

Analyzes a locally downloaded Rossum implementation to find improvements and upsell opportunities. Reviews schemas, extensions, automation settings, master data hub config, export pipelines, and business rules. Produces a structured report with Quick Wins, Improvements, and Upsell Opportunities.

### `/rossum:document [path]`

Documents a locally downloaded Rossum implementation, explaining both what is configured and why each design decision was made. Produces a structured technical handoff document covering schemas, extensions, queues, master data hub, export pipeline, business rules, and a design decisions log.

### Rossum Reference (auto-loaded)

A comprehensive Rossum.ai platform reference (API, TxScript, Aurora AI, Master Data Hub, extensions, etc.) that Claude loads automatically when relevant. Not invocable as a slash command.

### MongoDB Reference (auto-loaded)

A MongoDB query language reference tailored for Rossum.ai Master Data Hub. Covers find queries, aggregation pipelines, Atlas Search, operators, and practical matching patterns for data matching configurations. Auto-loaded when relevant.

### prd2 Reference (auto-loaded)

A reference for the prd2 CLI tool used to manage Rossum configurations across environments. Covers pull, push, deploy, purge, and hook commands, deploy files, attribute overrides, credentials, and project structure. Auto-loaded when relevant.

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
    ├── shared/
    │   └── discovery-checklist.md
    └── write-sow/
        └── SKILL.md
```

To test changes, restart Claude Code with `--plugin-dir`.
