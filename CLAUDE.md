# Rossum Claude Plugin Marketplace

This is a Claude Code plugin marketplace for Rossum.ai workflows. It follows the marketplace structure defined at https://code.claude.com/docs/en/plugin-marketplaces.

## Project structure

- `.claude-plugin/marketplace.json` — Marketplace manifest (name, owner, plugin catalog)
- `plugins/rossum-sa/` — The Rossum plugin
  - `.claude-plugin/plugin.json` — Plugin manifest (name, version, metadata)
  - `skills/` — All skills as `<name>/SKILL.md` directories
  - `mcp-servers/` — MCP server implementations
- `README.md` — Public-facing documentation

## Rules

- **README.md must always stay in sync with the project.** When adding, removing, or renaming skills or MCP tools, update README.md to reflect the change in the same commit.
- **New or modified MCP tools must be tested against the real API.** After implementing or updating a tool, call it via the MCP connection with valid arguments derived from live data (use IDs from list endpoints to feed into get endpoints, use existing collection names for Data Storage calls). For write/destructive tools, create a temporary resource, verify it exists, then clean it up. Do not consider a tool done until it passes a live call.
