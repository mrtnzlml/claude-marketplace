---
name: mongodb-reference
description: MongoDB query language reference tailored for Rossum.ai Master Data Hub. Covers find queries, aggregation pipelines, Atlas Search, operators, and practical matching patterns. Use when writing or debugging Master Data Hub matching configurations.
user-invocable: false
---

# MongoDB Reference for Rossum Master Data Hub

This skill provides a comprehensive MongoDB query language reference specifically tailored for Rossum.ai Master Data Hub usage. For complete details, see [reference.md](reference.md).

Use this knowledge when:
- Writing Master Data Hub matching queries (find or aggregate)
- Debugging data matching configurations that use MongoDB syntax
- Building fuzzy matching, regex matching, or scored matching pipelines
- Optimizing matching performance or accuracy
- Understanding MongoDB operators available in Rossum's matching engine
- Working with `$search`, `$lookup`, `$function`, or other advanced pipeline stages

When writing or debugging queries, if the dataset structure is not already known from context, ask the user for a sample record from the dataset before writing queries. This ensures correct field names and appropriate query behavior for the actual data.
