---
name: data-storage-reference
description: Rossum Data Storage API reference — MongoDB-compatible REST API for collections, CRUD operations, find, aggregate, bulk_write, indexes, and Atlas Search indexes. Use when querying or managing data in Rossum's Data Storage service directly via API.
user-invocable: false
---

# Rossum Data Storage API Reference

This skill provides the complete REST API reference for Rossum's Data Storage service — a MongoDB-compatible data layer used by the Master Data Hub and available for direct API access. For complete details, see [reference.md](reference.md).

Use this knowledge when:
- Querying Data Storage collections via the REST API (find, aggregate)
- Performing CRUD operations on documents (insert, update, delete, replace)
- Running bulk write operations
- Managing collections (create, rename, drop)
- Managing indexes (create, drop, list) and Atlas Search indexes
- Understanding async operation patterns (202 responses, operation status polling)
- Debugging Data Storage API calls or understanding response schemas
- Building integrations that read/write data to Rossum's Data Storage

Note: The `rossum-api` MCP server provides convenient tool wrappers for some of these endpoints (aggregate, list collections, list indexes). Use the MCP tools for interactive exploration; use this reference when building configurations or understanding the full API surface.
