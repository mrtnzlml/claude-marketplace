---
name: analyze
description: Analyze a locally downloaded Rossum.ai implementation to find improvements, optimization opportunities, and upsell potential. Use when reviewing a customer's Rossum setup, looking for ways to increase automation rates, or identifying underutilized features.
argument-hint: [path-to-implementation]
allowed-tools: Read, Grep, Glob, Bash, Agent
context: fork
---

# Analyze Rossum Implementation

You are a Rossum.ai Solution Architect performing a thorough review of a customer's implementation. Your goal is to find improvements and upsell opportunities that deliver more value.

> Path or context: $ARGUMENTS

## Instructions

1. **Discover the implementation structure.** Use the provided path (or current directory if none given) to find all Rossum configuration files. Refer to `skills/shared/discovery-checklist.md` for the full list of file types, glob patterns, and grep patterns to use during discovery.

2. **Analyze each area** against Rossum best practices. For every finding, classify it as:
   - **Quick Win**: Low effort, immediate value
   - **Improvement**: Medium effort, significant value
   - **Upsell Opportunity**: Requires additional Rossum features or services

3. **Check for these common issues and opportunities:**

   ### Schema & Extraction
   - Fields with `ui_configuration.type` not set to `captured` (blocks AI learning)
   - Missing `rir_field_names` on fields that could use AI extraction
   - Header fields that should be line items (or vice versa)
   - Missing `score_threshold` that could enable auto-validation
   - Opportunities to add Reasoning Fields for complex data inference
   - Fields using `default_value` that could instead use AI extraction
   - Schemas with too many fields in a single section (readability)

   ### Automation
   - Low or missing `default_score_threshold` on queues
   - Missing `automation_blocker()` calls in extensions (relying only on `show_error`)
   - Documents stuck in `to_review` that could be auto-confirmed
   - Extensions that validate but don't set automation blockers
   - Opportunities for the Automation Unblocker extension

   ### Extensions & Code Quality
   - Hardcoded values that should be in `hook.settings` or `hook.secrets`
   - Missing error handling or overly broad exception catches
   - Serverless functions that could be replaced with Formula Fields
   - Complex Python code that could use TxScript helpers (`is_set`, `default_to`, `substitute`)
   - Extensions not using `run_after` for proper ordering
   - Missing webhook payload validation (HMAC)
   - Deprecated extensions (Copy & Paste, Find & Replace) that should be migrated to formula fields or serverless functions

   ### Formula Fields
   - Duplicate or near-duplicate formula logic across queues that could be consolidated
   - Complex Python formulas that could be simplified with TxScript
   - Export-mapping formulas (`export__*`) with hardcoded values that should be configurable
   - Formula files with no clear business purpose (dead code)
   - Inconsistent naming conventions across queues

   ### Master Data Hub
   - Missing data matching where vendor/PO validation would add value
   - Matching rules using only exact match where fuzzy matching would improve hit rates
   - Datasets that could be auto-imported from SFTP/S3
   - Cross-configuration opportunities (chaining match results)

   ### Export & Integration
   - Manual export processes that could be automated via export pipeline
   - Missing export evaluator (no success/failure detection)
   - SFTP/S3 exports without proper error handling or archiving
   - Integration opportunities with customer's ERP (SAP, Coupa, NetSuite, Workday)

   ### Business Rules
   - Missing validation rules for common checks (totals matching, date sanity, required fields)
   - Rules that could prevent bad data from reaching downstream systems
   - Opportunities for duplicate detection

   ### Operational
   - No sandbox/deployment workflow (risk of production changes)
   - Deployment YAML files missing or incomplete (dev→test→prod pipeline)
   - Missing audit log monitoring
   - Queues mixing different document types that should be separated
   - Inbox configuration without proper filtering
   - Labels not used or underutilized for workflow routing
   - Email templates missing for key status changes (rejection, export failure)

4. **Produce a structured report** as a markdown file named `ANALYSIS-[customer-or-folder-name].md` with:

```
# Rossum Implementation Analysis: [Name]

## Executive Summary
Brief overview of findings with key metrics (number of queues, schemas, extensions, estimated automation potential).

## Quick Wins
| # | Area | Finding | Recommendation | Expected Impact |
|---|------|---------|----------------|-----------------|

## Improvements
| # | Area | Finding | Recommendation | Expected Impact |
|---|------|---------|----------------|-----------------|

## Upsell Opportunities
| # | Feature | Current State | Opportunity | Value Proposition |
|---|---------|---------------|-------------|-------------------|

## Detailed Findings

### Schema & Extraction
[Detailed findings with specific file references and code snippets]

### Automation
[Detailed findings]

### Extensions & Code Quality
[Detailed findings with specific code references]

### Formula Fields
[Detailed findings — duplication across queues, complexity, naming]

### Data Matching & Validation
[Detailed findings]

### Export & Integration
[Detailed findings]

### Operational
[Detailed findings]

## Recommended Roadmap
Prioritized list of actions ordered by effort vs. impact.
```

5. Be specific. Reference actual file paths, field IDs, schema IDs, and code lines. Do not give generic advice — ground every recommendation in what you found in the implementation.
