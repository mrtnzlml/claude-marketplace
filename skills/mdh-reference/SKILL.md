---
name: mdh-reference
description: Master Data Hub (MDH) complete reference — MDH API (dataset CRUD, fuzzy search), hook configuration model (MatchConfig, mapping, result actions, query cascades), MongoDB query syntax (operators, aggregation stages, Atlas Search), query design rules, score normalization, and real-world matching examples. Use when building or debugging MDH matching configurations, writing MongoDB queries for Rossum, or working with the MDH API.
user-invocable: false
---

# Master Data Hub (MDH) Reference

This skill provides comprehensive reference documentation for Rossum's Master Data Hub — the matching engine that connects extracted document data to master data records. It covers the MDH management API, the hook configuration model, MongoDB query syntax, and query design patterns.

**Reference files:**
- [mdh-api-reference.md](mdh-api-reference.md) — MDH API endpoints (dataset CRUD, fuzzy search, operation status) and hook configuration schema (MatchConfig, DMDatasetSource, Mapping, ResultActions, query cascade model)
- [mdh-matching-queries.md](mdh-matching-queries.md) — Query design rules (DO/DON'T), score normalization patterns, unique-result filters, GL coding dropdown pre-selection, real-world examples (supplier matching, PO line items, delivery address resolution), and Atlas Search index recommendations
- [mongodb-query-reference.md](mongodb-query-reference.md) — MongoDB query syntax reference: find operators, regex patterns, aggregation pipeline stages, expression operators, `$function`, `$lookup`, `$unionWith`, Atlas Search (`$search` with fuzzy, compound, dynamic thresholds, embedded documents), 14 practical matching patterns, data type handling, performance tips, and debugging

Use this knowledge when:
- Building MDH matching configurations (hook JSON with source, mapping, result_actions)
- Designing query cascades (exact → fuzzy → fallback)
- Writing MongoDB find queries or aggregation pipelines
- Using `$search` with compound queries, score normalization, or `$setWindowFields`
- Using `$lookup`, `$unionWith`, `$function`, or other advanced pipeline features
- Configuring memorization via `$unionWith` patterns
- Managing MDH datasets via the API (upload, replace, update, delete)
- Enabling fuzzy search on datasets
- Debugging matching hook configurations, query syntax, or performance issues

When writing or debugging queries, if the dataset structure is not already known from context, try to discover it using the `rossum-api` MCP tools: `data_storage_list_collections` to find available collections and `data_storage_aggregate` with `[{"$sample": {"size": 1}}]` to retrieve a sample record. Fall back to asking the user only if the MCP tools are not available.
