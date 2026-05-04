# 🧰 Rossum toolkit for Claude Code

Turn Claude into a Rossum implementation partner — audit hooks, analyze schemas, query Data Storage, extract documents, and generate SOWs, all from your terminal.

7 skills · 9 reference packs · 53 MCP tools — [Claude Code plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces) for Rossum.ai.

<!-- TODO: add a terminal demo GIF here (e.g. invoice extraction or hook audit) -->

## 🚀 Quick start

You need [Claude Code CLI](https://code.claude.com/) and a Rossum API token.

```bash
/plugin marketplace add mrtnzlml/claude-marketplace
/plugin install rossum-sa@mrtnzlml-claude-marketplace
```

Then connect and go:

```
Connect to Rossum (token: <TOKEN>, base URL: https://elis.rossum.ai).
Map out the entire org — workspaces, queues, hooks, schemas — and draw
an ASCII architecture diagram. Add emoji health indicators next to each
component (🟢 healthy, 🟡 warning, 🔴 broken).
```

> **Note:** Auto-updates are off by default for third-party marketplaces. Enable them in `/plugin` → **Marketplaces** tab.

**Optional:** For a better experience when developing and implementing projects, install the [superpowers](https://github.com/obra/superpowers) plugin — it adds structured planning, TDD workflows, and code review skills that pair well with `rossum-sa`:

```bash
/plugin install superpowers@claude-plugins-official
```

### Running from a local checkout (feature branch)

To test a feature branch before it's published to the marketplace, clone the repo and point Claude Code at the plugin directories with `--plugin-dir`.

Example using the [`teamd-hackathon`](https://github.com/mrtnzlml/claude-marketplace/tree/teamd-hackathon) branch:

```bash
git clone -b teamd-hackathon https://github.com/mrtnzlml/claude-marketplace.git rossum-claude-plugin

claude --plugin-dir rossum-claude-plugin/plugins/rossum-sa \
       --plugin-dir rossum-claude-plugin/plugins/nerossum
```

Each `--plugin-dir` loads one plugin; omit the ones you don't need.

## ⚡ Skills

### `rossum-sa`

| Skill | Description |
|-------|-------------|
| `/rossum-sa:write-sow` | Generate a Statement of Work from project requirements |
| `/rossum-sa:analyze [path]` | Check an implementation for configuration errors |
| `/rossum-sa:document [path]` | Produce a queue-focused reference document |
| `/rossum-sa:implement` | Plan and execute an integration project end-to-end |
| `/rossum-sa:refine-deployment [deploy-file] [impl-path]` | Enhance prd2 deploy files with target IDs and attribute overrides |
| `/rossum-sa:upgrade [path]` | Upgrade deprecated extensions to formula fields and bump old Python runtimes on function hooks to `python3.12` |
| `/rossum-sa:dead-code [path]` | Find unused hooks, formulas, rules, labels, and engines with a deterministic detector |

### `nerossum`

| Skill | Description |
|-------|-------------|
| `/nerossum:document-processing` | Extract structured data from invoices, POs, and receipts with validation and anomaly detection |

## 📚 Autoloaded references

When `rossum-sa` is enabled, Claude automatically gets domain knowledge for:

- **Rossum platform** — queues, schemas, hooks, annotations, workflows
- **MongoDB** — query syntax, aggregation pipelines
- **Master Data Hub (MDH)** — matching, scoring, collections
- **Data Storage API** — CRUD, indexing, search
- **TxScript & Serverless Functions** — formula fields, extension development
- **SAP Integration** — connector setup, mapping
- **Export Pipeline (Request Processor)** — multi-stage API integration engine, SFTP export, auth, response handling
- **Coupa Integration Baseline (CIB)** — schema, MDH matching, export pipeline, business rules
- **prd2 CLI** — deployment and management commands
- **Structured Formats Import (SFI)** — XML/JSON import setup, XPath/JMESPath selectors, e-invoicing (ZUGFeRD, X-Rechnung)

## 💡 What can you do with this?

**🕵️ Who's been busy?** — Pull a year of audit logs and surface suspicious activity patterns.
```
Connect to Rossum (token: <TOKEN>, base URL: https://elis.rossum.ai), pull all audit logs
for the last year, and print a histogram of user activity. Highlight suspicious patterns.
```

**🔗 Find broken hooks** — Audit your hook chains across all queues.
```
Connect to Rossum and list all hooks. Group them by queue and flag any that are inactive,
have no queues attached, or have a broken run_after chain.
```

**📊 Spot missing indexes** — Catch Data Storage performance problems before they bite.
```
Connect to Rossum and check all Data Storage collections. List their indexes and search
indexes, flag any missing __dynamic_index or duplicate/redundant indexes.
```

**🎯 Tune fuzzy matching** — Optimize MDH search scores with real data.
```
Connect to Rossum and find the $search query in the MDH matching extension. Verify and
calibrate the score thresholds against real data in the collection. Use at least 1000 samples.
```

**🔀 Detect schema drift** — Find fields that diverged across queues.
```
Connect to Rossum and compare schemas across all active queues. List fields that exist in
one schema but not another.
```

## 🔌 MCP tools (`rossum-api`)

The MCP server starts automatically when `rossum-sa` is enabled. Write and destructive tools require explicit user approval.

#### Connection

| Tool | Description |
|------|-------------|
| `rossum_set_token` | Authenticate with a Rossum environment (API token, username+password, or pasted curl connection string) |
| `rossum_whoami` | Show authenticated user, organization, and role |

#### Rossum API

| Tool | Description |
|------|-------------|
| `rossum_list_workspaces` | List workspaces |
| `rossum_get_workspace` | Get full workspace details |
| `rossum_list_queues` | List queues (filter by workspace, status) |
| `rossum_get_queue` | Get full queue details |
| `rossum_get_schema` | Get queue schema (datapoints, sections, tables) |
| `rossum_patch_schema` | ✏️ Update a schema (name, content, metadata) |
| `rossum_list_schemas` | List all schemas |
| `rossum_list_hooks` | List hooks/extensions (filter by queue, active) |
| `rossum_get_hook` | Get full hook details including code and config |
| `rossum_create_hook` | ✏️ Create a new hook (serverless function or webhook) |
| `rossum_delete_hook` | ⚠️ Delete a hook |
| `rossum_patch_hook` | ✏️ Update an existing hook (code, events, active, queues) |
| `rossum_get_hook_secret_keys` | List secret key names on a hook |
| `rossum_list_hook_logs` | List hook execution logs (filter by hook, annotation, queue, status) |
| `rossum_list_annotations` | List annotations in a queue (filter by status) |
| `rossum_search_annotations` | Search annotations across queues (filter by status, date range, workspace) |
| `rossum_get_annotation` | Get annotation metadata, messages, and state |
| `rossum_patch_annotation` | ✏️ Update annotation status or metadata (confirm, reject, export) |
| `rossum_get_annotation_content` | Get extracted data from an annotation |
| `rossum_get_document` | Get document metadata (filename, MIME type) |
| `rossum_get_inbox` | Get inbox details (email address, config) |
| `rossum_list_connectors` | List export connectors (filter by queue) |
| `rossum_get_connector` | Get full connector details |
| `rossum_list_emails` | List emails (filter by queue, type) |
| `rossum_get_email` | Get full email details (subject, body, attachments) |
| `rossum_list_email_threads` | List email threads (filter by queue) |
| `rossum_get_email_thread` | Get email thread details (replies, annotations) |
| `rossum_get_organization` | Get organization details and feature flags |
| `rossum_list_groups` | List available user roles (groups) and their IDs |
| `rossum_list_users` | List organization users |
| `rossum_create_user` | ✏️ Create a new user in the organization |
| `rossum_list_audit_logs` | Query audit logs (admin only) |

#### Data Storage

| Tool | Description |
|------|-------------|
| `data_storage_healthz` | Check API reachability |
| `data_storage_list_collections` | List collections |
| `data_storage_find` | Query documents with filter/projection/sort |
| `data_storage_aggregate` | Run MongoDB aggregation pipelines |
| `data_storage_list_indexes` | List collection indexes |
| `data_storage_list_search_indexes` | List Atlas Search indexes |
| `data_storage_insert` | ✏️ Insert one or more documents into a collection |
| `data_storage_update_one` | ✏️ Update first document matching a filter |
| `data_storage_update_many` | ✏️ Update all documents matching a filter |
| `data_storage_replace_one` | ✏️ Replace first document matching a filter |
| `data_storage_delete_one` | ⚠️ Delete first document matching a filter |
| `data_storage_delete_many` | ⚠️ Delete all documents matching a filter |
| `data_storage_bulk_write` | ✏️ Perform multiple write operations atomically |
| `data_storage_create_index` | ✏️ Create a database index |
| `data_storage_create_search_index` | ✏️ Create an Atlas Search index |
| `data_storage_drop_index` | ⚠️ Drop a database index |
| `data_storage_drop_collection` | ⚠️ Drop a collection and all its indexes |
| `data_storage_rename_collection` | ⚠️ Rename a collection |
| `data_storage_drop_search_index` | ⚠️ Drop an Atlas Search index |

✏️ = write (requires approval) · ⚠️ = destructive (requires approval)
