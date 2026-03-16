---
name: txscript-reference
description: TxScript and serverless function guide for Rossum hooks. Covers the TxScript Python 3.12 API (TxScript class, field access, messages, automation blockers), validation patterns, and common schema field conventions. Use when writing or debugging Rossum serverless functions (hooks).
user-invocable: false
---

# TxScript & Serverless Functions Reference

This skill provides a practical guide for writing Rossum serverless functions using the TxScript API. It covers the entry point pattern, field access, utility functions, validation recipes, and common schema field conventions. For complete details, see [reference.md](reference.md).

Use this knowledge when:
- Writing new Rossum serverless functions (hooks) using TxScript
- Understanding the `rossum_hook_request_handler` entry point pattern
- Using the `TxScript` class API (field read/write, messages, automation blockers)
- Implementing validation logic (face value checks, required fields, date ranges)
- Deciding between formula fields and serverless functions for a given task
- Looking up common schema field IDs and their conventions (document_id, sender_name, etc.)
- Debugging serverless function behavior

Note: The rossum-reference skill covers TxScript syntax in detail (field access, conditionals, string operations, messaging). This reference complements it with the `TxScript` class wrapper pattern and practical validation recipes.
