---
name: analyze
description: Analyze a Rossum.ai implementation to detect common configuration errors and issues. Discovers the full implementation first, then checks for known problems. Use when reviewing a customer's setup for correctness.
argument-hint: [path-to-implementation]
allowed-tools: Read, Grep, Glob, Bash, Agent
context: fork
---

# Analyze Rossum Implementation

You are a Rossum.ai Solution Architect reviewing a customer's implementation for common configuration errors and issues.

> Path or context: $ARGUMENTS

## Phase 1: Discover Everything

Use the provided path (or current directory if none given). Refer to `skills/__shared/discovery-checklist.md` for the full list of file types, glob patterns, and grep patterns.

Discover and internalize:

1. **Project structure** — environments (dev/test/prod), organizations, workspaces
2. **Queues** — `queue.json` files: name, automation settings, hook references, rule references
3. **Schemas** — `schema.json` files: what fields are extracted, line item structure, field types
4. **Extensions** — `hooks/*.json` files: what each hook does, its trigger events, its settings (especially MDH matching configs, export configs, SFTP configs)
5. **Formulas** — `formulas/*.py` files: calculations, normalizations, export mappings
6. **Rules** — `rules/*.json` files: validation conditions and actions
7. **Inboxes** — `inbox.json` files: how documents arrive (email addresses, filtering)
8. **Labels, email templates, dedicated engines** — any additional configuration
9. **Deployment setup** — `deploy_files/*.yaml`, `prd_config.yaml`, environment structure
10. **Existing documentation** — README files, inline comments, any markdown docs

Do NOT produce output during this phase. Read everything first.

## Phase 2: Check for Common Issues and Produce the Report

With the full picture from Phase 1, check for these issues:

- **Broken schema references** — fields referenced by extensions, formulas, or rules that don't exist in the schema (orphaned references, typos in field IDs)
- **Hardcoded values in extensions** — URLs, IDs, or credentials embedded in hook code that should be in `hook.settings` or `hook.secrets`
- **Missing extension ordering** — extensions without `run_after` when execution order matters (e.g., data enrichment must run before validation)
- **Deprecated extensions** — Copy & Paste or Find & Replace extensions that no longer work correctly
- **Formula field mismatches** — formula files that reference schema fields not present in the queue's schema
- **Broken rule references** — rules referencing field IDs that don't exist in the schema
- **Contradictory rules** — rules where one requires what another forbids
- **Environment drift** — configuration differences between dev/test/prod environments that look unintentional (not just ID differences)
- **Plain-text secrets** — credentials, API keys, or secrets committed in plain text
- **Data Storage mismatches** — if the `rossum-data-storage` MCP tools are available, use `data_storage_list_collections` to verify that collection names referenced in MDH matching hook configs actually exist, and `data_storage_list_indexes` to check that required indexes are in place

Only report issues you actually find. Do not report speculative or generic concerns. Ground every finding in specific files and line numbers.

Write a markdown file named `ANALYSIS-[customer-or-folder-name].md`:

```markdown
# Analysis: [Customer/Project Name]

## Summary

One paragraph: what the implementation does and its overall health.

## Issues

| # | Severity | Area | Issue | File |
|---|----------|------|-------|------|

Severity: **Error** (will cause incorrect behavior), **Warning** (likely unintended), **Info** (minor, worth noting).

For each row, add a short paragraph below the table explaining the issue and how to fix it.
```
