# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Claude Code plugin marketplace for Rossum.ai workflows (https://code.claude.com/docs/en/plugin-marketplaces). Contains two plugins:

- **`rossum-sa`** — The main plugin: skills, reference packs, and an MCP server for Rossum SA work
- **`nerossum`** — A lightweight demo plugin with a single document-processing skill

## Architecture

**Marketplace** → **Plugins** → **Skills + MCP servers**

- `.claude-plugin/marketplace.json` lists available plugins
- Each plugin lives under `plugins/<name>/` with its own `.claude-plugin/plugin.json`
- Skills are Markdown files at `plugins/<name>/skills/<skill-name>/SKILL.md`
- The `rossum-sa` plugin has 5 invocable skills (analyze, document, implement, upgrade, write-sow) and 8 autoloaded reference packs (*-reference skills)

**MCP server** (`plugins/rossum-sa/mcp-servers/rossum-api/server.py`):
- Single-file Python, ~1500 lines, zero external dependencies (stdlib `urllib` + optional `certifi` for SSL)
- Implements MCP JSON-RPC over stdio (reads/writes newline-delimited JSON on stdin/stdout)
- Tools are registered via the `@_tool` decorator which populates `TOOLS` and `HANDLERS` dicts
- Three annotation levels control permission prompts: `_READ_ONLY`, `_WRITE`, `_DESTRUCTIVE`
- Manages its own auth state (`_cached_token`, `_cached_base_url`) — no persistent credentials
- All Rossum API calls go through `_http_request()` which handles auth, errors, and 401 invalidation
- Pagination is handled by `_paginate()` for list endpoints and `_rossum_list()` wrapper

## Rules

- **README.md and README-internal.md must always stay in sync with the project.** When adding, removing, or renaming skills or MCP tools, update README.md to reflect the change in the same commit. README-internal.md contains internal development prompts for maintaining the plugin.
- **Version strings must stay in sync.** When bumping the version, update both `plugins/rossum-sa/.claude-plugin/plugin.json` and the `serverInfo` version in `plugins/rossum-sa/mcp-servers/rossum-api/server.py`.
- **New or modified MCP tools must be tested against the real API.** After implementing or updating a tool, call it via the MCP connection with valid arguments derived from live data (use IDs from list endpoints to feed into get endpoints, use existing collection names for Data Storage calls). For write/destructive tools, create a temporary resource, verify it exists, then clean it up. Do not consider a tool done until it passes a live call.
