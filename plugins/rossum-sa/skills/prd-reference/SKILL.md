---
name: prd-reference
description: prd2 CLI reference for managing Rossum configurations across environments. Covers pull, push, deploy, purge commands, credentials, deploy files, attribute overrides, and project structure. Use when working with prd2, deployment workflows, or Rossum environment management.
user-invocable: false
---

# prd2 (Project Rossum Deploy) Reference

This skill provides a comprehensive reference for the prd2 deployment CLI used to manage Rossum.ai configurations across environments. For complete details, see [reference.md](reference.md).

IMPORTANT: Always use prd2 (v2). The original prd (v1) from the `deployment-manager` package is deprecated and should not be used. prd2 uses a different project structure, configuration format, and deployment model.

Use this knowledge when:
- Working with `prd2` CLI commands (pull, push, deploy, purge, hook, etc.)
- Setting up deployment pipelines for Rossum configurations
- Pulling or pushing Rossum objects (schemas, hooks, queues, workspaces, rules, labels, engines)
- Deploying configurations between environments using deploy files
- Configuring `prd_config.yaml`, `credentials.yaml`, or deploy YAML files
- Using attribute overrides (static, regex with `/#/` separator, `$prd_ref`, `$source_value`)
- Debugging deployment or sync issues between environments
- Writing CI/CD pipelines that automate Rossum deployments
