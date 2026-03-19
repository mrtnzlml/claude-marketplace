---
name: mongodb-reference
description: MongoDB query language reference tailored for Rossum. Covers find operators, regex patterns, aggregation pipeline stages, expression operators, Atlas Search ($search with fuzzy, compound, dynamic thresholds, embedded documents), $function, $lookup, $unionWith, practical matching patterns, data type handling, performance tips, and debugging. Use when writing or debugging MongoDB queries in any Rossum context (MDH matching, Data Storage, aggregation pipelines).
user-invocable: false
---

# MongoDB Query Reference

This skill provides a comprehensive MongoDB query language reference for use across Rossum — in Master Data Hub matching configurations, Data Storage API calls, or any context that uses MongoDB-style queries. For complete details, see [reference.md](reference.md).

Use this knowledge when:
- Writing MongoDB find queries or aggregation pipelines
- Using `$search` with fuzzy matching, compound queries, or score filtering
- Using `$lookup`, `$unionWith`, `$function`, or other advanced pipeline features
- Building regex patterns for data matching
- Understanding MongoDB operators (comparison, logical, element, array, evaluation)
- Working with Atlas Search (dynamic thresholds, embedded document search)
- Debugging query syntax, performance, or unexpected results
- Handling data type coercion in queries

When writing or debugging queries, if the dataset structure is not already known from context, try to discover it using the `rossum-api` MCP tools: `data_storage_list_collections` to find available collections and `data_storage_aggregate` with `[{"$sample": {"size": 1}}]` to retrieve a sample record. Fall back to asking the user only if the MCP tools are not available.
