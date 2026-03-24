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
- **MCP server tests must always stay in sync with the implementation.** When adding, removing, or changing tools in `server.py`, update `server_test.py` in the same commit. Run `pytest plugins/rossum-sa/mcp-servers/rossum-api/server_test.py` to verify.
