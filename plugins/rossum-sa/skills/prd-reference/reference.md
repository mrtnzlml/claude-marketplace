# prd2 (Project Rossum Deploy) Reference

prd2 is a CLI tool for tracking changes, deploying, and releasing Rossum platform configurations across environments. Source: https://github.com/rossumai/prd

IMPORTANT: The original prd (v1) from the `deployment-manager` package is deprecated. Always use prd2. Key differences: prd2 uses `prd_config.yaml` (not `credentials.json`), per-directory `credentials.yaml` (not centralized JSON), deploy YAML files (not `mapping.yaml`-based release), and supports additional object types (rules, labels, engines, email templates, workflows).

## Terms

- **source** — dev/test environment where the project is built and tested
- **target** — production (or next-stage) environment where the project is deployed
- **local** — files on the local machine (git repository)
- **remote** — objects in Rossum platform (the API)
- **org directory** — local directory mapped to a Rossum organization (e.g., `sandbox-org/`, `production-org/`)
- **subdirectory** — environment within an org directory (e.g., `dev/`, `test/`, `default/`)

## Prerequisites

- git
- Python 3.12+
- Rossum account with admin role credentials

## Installation

```bash
brew install pipx
pipx ensurepath
pipx install project-rossum-deploy
```

Reinstall: `pipx install project-rossum-deploy --force`

Self-update: `prd2 update`

## Commands

### `prd2 init [name]`

Creates a new project directory with basic files, initializes a git repo, and creates a `.gitignore`. Interactively prompts for organization directories, org IDs, API base URLs, tokens, and subdirectories with optional regex filters.

Default name: `.` (current directory).

### `prd2 pull [destinations...] [options]`

Downloads Rossum objects from remote organizations to local files.

```bash
prd2 pull sandbox-org --all        # pull entire org, overwrite local
prd2 pull sandbox-org/dev          # pull specific subdirectory
prd2 pull sandbox-org production-org  # pull multiple orgs
```

| Option | Description |
|--------|-------------|
| `-a` / `--all` | Download all remote files, overwriting local |
| `-c` / `--commit` | Auto-commit pulled changes |
| `-m` / `--message` | Custom commit message (default: "Sync changes to local") |
| `-s` / `--skip-objects-without-subdir` | Skip objects whose subdirectory cannot be determined |
| `--concurrency` | Max concurrent API requests |

Behavior:
- Compares `modified_at` timestamps to avoid overwriting unversioned local changes
- Removes local files for objects deleted in Rossum
- Extracts formula field code into separate `.py` files in `formulas/` directories
- Extracts hook code into separate `.py`/`.js` files alongside hook JSON
- **Editing rule:** Always edit the extracted `.py` file, never the JSON. This applies to both hook code (`.py` file next to the hook JSON — never edit the `code` field) AND formula code (`formulas/*.py` — never edit the `formula` property in `schema.json`). The `.py` file is the single source of truth — `prd2 push` merges it back into the JSON automatically.
- Supports all object types: organizations, workspaces, queues, inboxes, schemas, hooks, labels, rules, engines, engine fields, email templates, workflows, workflow steps

### `prd2 push [destinations...] [options]`

Uploads locally changed files to Rossum. Push handles four operation kinds:

- **CREATE** — new files marked with the `_[]` placeholder convention (see below)
- **UPDATE** — modifications to files with an existing `_[<id>]`
- **DELETE** — `git rm` (or `git mv` to a non-resource path) of tracked files
- **RENAME** — `git mv` of an `_[<id>]` file/folder; collapses to a single UPDATE that preserves the remote object

```bash
prd2 push sandbox-org/dev          # push changes to dev
prd2 push sandbox-org/dev -y       # auto-apply structural changes (CI / non-TTY)
prd2 push sandbox-org/dev -f       # force push, ignore timestamps
prd2 push sandbox-org/dev -io      # push only git-indexed files
```

| Option | Description |
|--------|-------------|
| `-a` / `--all` | Upload all local files, not just modified ones |
| `-f` / `--force` | Ignore newer remote timestamps, overwrite remote |
| `-io` / `--indexed-only` | Push only files added to git index |
| `-y` / `--yes` | Skip the interactive confirmation prompt for plans containing CREATE or DELETE |
| `-c` / `--commit` | Auto-commit after push (skipped if any directory failed) |
| `-m` / `--message` | Custom commit message (default: "Pushed changes to remote") |
| `--concurrency` | Max concurrent API requests |

Pipeline (per directory):

1. **Detect** — uses `git status -s` to find changed files (`R*` rename op codes are split into a (D old, ?? new) pair).
2. **Merge** — folds `.py` / `.js` hook code and `formulas/*.py` formula code back into their JSON. New hooks created with both `.json` and `.py` are deduplicated to a single CREATE.
3. **Classify** — decides CREATE vs UPDATE vs DELETE vs RENAME for each change. Pairs `(D old_id, ?? new_id)` from `git mv` into a single UPDATE so the remote object is not destroyed and recreated.
4. **Validate** — pre-flight checks before any API call: required fields, sibling-schema-for-new-queue, parent-queue-for-new-schema/inbox, parent-engine-for-new-engine-field, hook runtime/code consistency, duplicate names within parent, and delete-under-create conflicts. Validation errors abort the push for that directory before any API call is made.
5. **Plan** — renders a CREATE/UPDATE/DELETE plan to the terminal.
6. **Confirm** — if the plan contains structural changes (any CREATE or DELETE), prompts for confirmation. UPDATE-only plans skip the prompt. `--yes` skips the prompt unconditionally. **In a non-TTY shell (CI, piped runs, agents) without `--yes`, the push aborts cleanly with a "stdin is non-interactive" message — pass `--yes` for automation.**
7. **Apply** — executes the plan:
   - **CREATEs** are sequential in topo order (Workspace → Engine → EngineField → Schema → Queue → Inbox → Hook → Rule). On any CREATE failure, the rest of the CREATE phase is aborted (UPDATEs and DELETEs do not run for that directory).
   - **UPDATEs** run concurrently. The `modified_at` timestamp is compared unless `-f` is used (skipped for renames since the path-based timestamp key won't exist post-rename).
   - **DELETEs** run by-type-bucket in reverse topo order (Rule → Hook → Inbox → Queue → Schema → EngineField → Engine → Workspace). Within a bucket, concurrent. **Queues use `?delete_after=0` (hard delete) and poll until the row is gone**, so the schema/inbox DELETEs that follow don't 409 against a deletion-pending queue. If the queue isn't gone within 30s, the push aborts and can be re-run.
   - 404 responses on DELETE are treated as success (cascade-already-deleted).
8. **Pull** — after a successful push, automatically pulls the directory to sync timestamps and write back any server-generated state (e.g. new IDs into `_[<id>]` filenames).

If any directory fails, both the post-push pull and the auto-commit step (`-c`) are skipped — the working tree is left dirty for inspection.

#### Creating new objects with `_[]` placeholders

To create a new Rossum object via push, write the local file with `_[]` instead of an ID. The placeholder marks the file as "create this on remote." Push will POST the object, receive the real ID, and rename the placeholder to `_[<real_id>]` on disk.

```
workspaces/My New WS_[]/workspace.json                    # creates a workspace
workspaces/My New WS_[]/queues/My New Queue_[]/queue.json # nested in same push
workspaces/My New WS_[]/queues/My New Queue_[]/schema.json
hooks/My New Hook_[].json                                 # creates a hook
hooks/My New Hook_[].py                                   # code for it
rules/My New Rule_[].json
engines/My New Engine_[1234]/engine_fields/My Field_[].json  # field under existing engine
```

Rules:

- The placeholder is `_[]` (open + close brackets, empty between). Folder-based types (`Workspace`, `Queue`, `Engine`) carry `_[]` on their parent folder; file-based types (`Hook`, `Rule`, `EngineField`) carry it on the file stem.
- A new file's JSON must NOT contain `id` or `url` fields — push will reject it with a clear error. Strip them from any pulled-then-renamed file.
- A new queue requires a sibling `schema.json` in the same `_[]` folder.
- Required fields the user must hand-write in the JSON (validation catches missing ones pre-flight):
  - **Workspace:** `name`, `organization` (the organization URL — there's no filesystem analog, must be supplied)
  - **Queue:** `name` (`workspace` and `schema` URLs are auto-resolved from the parent folder and sibling `schema.json`)
  - **Schema:** `name`, `content`
  - **Inbox:** `name`, plus **one of** `email_prefix` or `email` (the API enforces this cross-field rule; `queues` is auto-resolved from the parent queue folder)
  - **Hook:** `name`, `events`, `queues` (may be `[]`), `config`. The `type` field is optional and defaults to `webhook`. For `webhook`-type hooks, `config` must contain a `url`. For `function`-type hooks, `config` must contain a `runtime` (e.g. `python3.12`).
  - **Rule:** `name`
  - **Engine:** `name`, `description`
  - **EngineField:** `name` (`engine` URL is auto-resolved from the parent engine folder)
- Cross-references between newly-created sibling objects (e.g. queue → workspace URL, queue → schema URL, inbox → queue URL, engine_field → engine URL) are resolved automatically from the local filesystem. You don't need to fill them in.
- Inbox is a special case: filenames don't carry `_[]` (they're literally `inbox.json`). A no-id `inbox.json` under an existing `_[<queue_id>]/` folder is recognized as a CREATE.

#### Deleting objects

`git rm` (or `git rm -r`) the tracked file/folder, then push:

```bash
git rm -r "workspaces/Old Workspace_[1234]"
prd2 push sandbox-org/dev
```

- The file must be **tracked** (committed at least once) for the DELETE to be detected. Removing untracked files just makes them disappear from git's view; push won't notice.
- Schema and Inbox files don't carry IDs in their filenames — push recovers their IDs from git history (staged version first, then HEAD).
- DELETE skips the `modified_at` timestamp check (the local file is gone, so there's nothing to compare). Reaching the apply phase implies the user confirmed the plan.

#### Renaming objects

`git mv` an `_[<id>]` file or folder to a new name:

```bash
git mv "hooks/Old Hook_[706813].json" "hooks/Renamed Hook_[706813].json"
git mv "hooks/Old Hook_[706813].py" "hooks/Renamed Hook_[706813].py"
# Update the "name" field in the JSON to match
prd2 push sandbox-org/dev
```

- Push collapses the `(D old, ?? new)` pair from `git mv` into a single UPDATE that preserves the remote object's ID. The remote object is **not** destroyed and recreated.
- The file's `name` field must be updated to match the new local name; the rename only affects on-disk paths, not the remote `name` attribute.
- Companion `.py` / `.js` files for hooks should be renamed alongside the JSON.

### `prd2 deploy template create [options]`

Interactive wizard that creates a deploy YAML file. Prompts for source/target directories, workspace selection, queue selection (with schema/inbox auto-detection), hook selection, rule selection, engine selection, attribute overrides, secrets file, and deploy state file.

| Option | Description |
|--------|-------------|
| `-mf` / `--mapping-file` | PRD v1 mapping file for reusing IDs and attribute overrides |

### `prd2 deploy template update <deploy_file> [options]`

Updates an existing deploy YAML file, adding new objects or modifying existing ones.

```bash
prd2 deploy template update -i ./deploy_files/dev_test.yaml
```

| Option | Description |
|--------|-------------|
| `-i` / `--interactive` | Allow interactive changes |
| `-mf` / `--mapping-file` | PRD v1 mapping file for reusing IDs |

### `prd2 deploy template reverse <deploy_file>`

Creates a reversed deploy file (swaps source and target) for reverse deployment.

### `prd2 deploy run <deploy_file> [options]`

Executes a deployment based on a deploy YAML file.

```bash
prd2 deploy run --prefer=source ./deploy_files/dev_test.yaml
prd2 deploy run -y ./deploy_files/test_prod.yaml  # auto-apply
```

| Option | Description |
|--------|-------------|
| `--prefer` | Conflict resolution: `source` or `target` |
| `--no-rebase` | Skip rebase prompts from target |
| `-y` / `--auto-apply` | Apply plan without confirmation |
| `-c` / `--commit` | Auto-commit after deploy |
| `-m` / `--message` | Custom commit message (default: "Deployed changes to target organization") |
| `--concurrency` | Max concurrent API requests |

Behavior:
1. Validates deploy file
2. Authenticates source and target clients
3. Initializes all deploy objects (org, hooks, labels, email templates, rules, engines, workspaces, queues)
4. Performs 3-way merge comparison (last applied state vs current source vs remote target)
5. Shows deploy plan with colorized diffs for each object
6. Two-phase deploy: first creates/updates objects, second pass resolves cross-references
7. Saves deploy state and timestamps
8. Pulls target directory to sync local files

Not automatically migrated (must be set manually for newly created objects):
- `queue.dedicated_engine` and `queue.generic_engine`
- `queue.users` and `queue.workflows`
- `hook.secrets` (use `secrets_file` in deploy file instead)

### `prd2 deploy revert <deploy_file> [options]`

Deletes all target objects found in the deploy file. Shows a plan first and requires confirmation.

| Option | Description |
|--------|-------------|
| `-c` / `--commit` | Auto-commit after revert |
| `-m` / `--message` | Custom commit message |

### `prd2 hook payload <hook_path> [options]`

Generates a hook payload by calling the Rossum API.

| Option | Description |
|--------|-------------|
| `-au` / `--annotation-url` | URL or ID of annotation for payload |

### `prd2 hook test <hook_path> [options]`

Tests a hook locally using the Rossum API test endpoint. Uses the latest local `.py` code if available.

| Option | Description |
|--------|-------------|
| `-pp` / `--payload-path` | Path to payload JSON |
| `-au` / `--annotation-url` | Annotation URL for auto-generated payload |

### `prd2 hook sync template`

Creates a new sync template YAML for hook synchronization with a remote Git repository.

### `prd2 hook sync run <sync_file>`

Syncs local hook Python files with a remote Git source.

### `prd2 purge [object_types...] [options]`

Destructive deletion of objects from a Rossum organization. Shows a deletion plan and prompts for confirmation.

```bash
prd2 purge all                    # delete everything
prd2 purge unused_schemas         # delete schemas not assigned to queues
prd2 purge hooks workspaces       # delete specific object types
```

Object types: `workspaces`, `queues`, `hooks`, `schemas`, `inboxes`, `email_templates`, `labels`, `rules`, `engines`, `engine_fields`, `workflows`, `workflow_steps`, `all`, `unused_schemas`.

| Option | Description |
|--------|-------------|
| `--concurrency` | Max concurrent API requests |

### `prd2 update [version_tag]`

Self-updates prd2 from GitHub releases. Optionally specify a version tag.

## Configuration Files

### prd_config.yaml

Main project configuration. Created by `prd2 init`. Maps local directories to Rossum organizations.

```yaml
directories:
  sandbox-org:
    org_id: '285704'
    api_base: https://my-org.rossum.app/api/v1
    subdirectories:
      dev:
        regex: ''
      test:
        regex: ''
  production-org:
    org_id: '293441'
    api_base: https://my-org.rossum.app/api/v1
    subdirectories:
      default:
        regex: ''
```

- Each key under `directories` is a local folder name
- `org_id` — Rossum organization ID
- `api_base` — Rossum API base URL
- `subdirectories` — environments within the org, each with optional `regex` filter for routing objects

### credentials.yaml

Per-organization directory. Contains the API token. Never committed to git (auto-added to `.gitignore`).

```yaml
token: <YOUR_TOKEN>
```

Each org directory (and optionally each subdirectory) has its own `credentials.yaml`.

### Deploy File (YAML)

Stored in `deploy_files/`. Defines what to deploy from source to target and how.

```yaml
target_url: https://my-org.rossum.app/api/v1
source_dir: sandbox-org/dev
target_dir: sandbox-org/test
source_url: https://my-org.rossum.app/api/v1

token_owner_id:
deployed_org_id: 285704
patch_target_org: false

secrets_file: deploy_secrets/dev_test_secrets.json
deploy_state_file: deploy_states/dev_test_fb3154.json
last_deployed_at: '2026-03-02T09:58:46.704109Z'

workspaces:
  - id: 700852
    name: DEV Workspace
    targets:
      - id: 743213
        attribute_override:
          name: TEST Workspace

queues:
  - id: 2137275
    name: Cost Invoices (AT)
    base_path: sandbox-org/dev/workspaces/DEV Workspace_[700852]
    ignore_deploy_warnings: false
    targets:
      - id: 2278122
        attribute_override: {}
    schema:
      id: 1824379
      targets:
        - id: 1917224
          attribute_override: {}
    inbox:
      id: 813566
      targets:
        - id: 771322
          attribute_override: {}

hooks:
  - id: 856489
    name: 'Validator: invoices (DEV)'
    targets:
      - id: 898551
        attribute_override:
          name: \(DEV\)$/#/(TEST)

rules:
  - id: 2597
    name: E-invoice Validation Warning
    targets:
      - id: 2716
        attribute_override: {}

engines: []
unselected_hooks: []
```

Key fields:
- `target_url` / `source_url` — API base URLs
- `source_dir` / `target_dir` — local directory paths
- `deployed_org_id` — auto-set on first deploy, validates subsequent deploys go to the same org
- `patch_target_org` — whether to update target org attributes from source
- `secrets_file` — path to deploy secrets JSON
- `deploy_state_file` — path to deploy state snapshot (for 3-way merge)
- `targets` — array of target mappings (supports 1:N deployment)
- `target_id: null` — object will be created on first deploy
- `base_path` — for queues, the local filesystem path to the queue's parent workspace
- `ignore_deploy_warnings` — suppress non-critical warnings for this object
- `unselected_hooks` — hook IDs to exclude from deployment even if attached to selected queues

### Deploy Secrets (JSON)

Stored in `deploy_secrets/`. Maps hook names to their secrets (SFTP keys, API tokens, etc.). Never committed to git.

```json
{
  "SFTP import: hourly master data (DEV)_[847529]": {
    "type": "sftp",
    "ssh_key": "-----BEGIN RSA PRIVATE KEY-----\n..."
  }
}
```

### Deploy State (JSON)

Stored in `deploy_states/`. Snapshot of the last deployed state for each object. Used for 3-way merge during subsequent deploys to detect conflicts between local changes and remote changes.

## Attribute Override

Used in deploy files under `targets[].attribute_override` to modify attributes when deploying to target.

### Static override

Directly set a value:

```yaml
attribute_override:
  name: My Production Hook
```

### Regex replacement with `/#/` separator

Replace parts of a value using regex. Pattern: `<regex_match>/#/<replacement>`.

```yaml
attribute_override:
  name: \(DEV\)$/#/(TEST)
  # "Validator: invoices (DEV)" → "Validator: invoices (TEST)"
```

Can also match at the start of strings:

```yaml
attribute_override:
  settings.import_rules[*].dataset_name: ^DEV_/#/TEST_
  # "DEV_vendors" → "TEST_vendors"
```

### `$prd_ref`

Replaces source IDs or URLs with their target counterparts from the deploy mapping:

```yaml
attribute_override:
  settings.configurations[*].queue_ids: $prd_ref
```

### `$source_value`

References the original source value. Useful for composing target-specific values:

```yaml
attribute_override:
  name: "$source_value - PROD"
```

Override keys use JMESPath query syntax for nested paths and array wildcards (e.g., `settings.configurations[*].queue_ids`, `content[*].children[?(@.id == 'my_field')].formula`).

## Project Folder Structure

```
project_root/
  prd_config.yaml                        # main project configuration
  deploy_files/                          # deploy YAML templates
    dev_test.yaml
    test_prod.yaml
  deploy_secrets/                        # secrets for deployments (gitignored)
    dev_test_secrets.json
  deploy_states/                         # state snapshots from past deploys
    dev_test_abc123.json
  sandbox-org/                           # org directory
    credentials.yaml                     # API token (gitignored)
    organization.json                    # org-level metadata
    dev/                                 # subdirectory (environment)
      organization.json
      non_versioned_object_attributes.json
      hooks/
        HookName_[ID].json
        HookName_[ID].py                 # or .js (serverless code)
      labels/
        LabelName_[ID].json
      rules/
        RuleName_[ID].json
      engines/
        EngineName_[ID].json
      workspaces/
        WorkspaceName_[ID]/
          workspace.json
          queues/
            QueueName_[ID]/
              queue.json
              schema.json
              inbox.json
              formulas/                  # formula field code
                field_id.py
              email_templates/
                TemplateName_[ID].json
    test/                                # another subdirectory
      (same structure as dev)
  production-org/                        # another org directory
    credentials.yaml
    organization.json
    default/
      (same structure)
```

Key differences from prd v1:
- Schemas are stored inside queue directories as `schema.json` (not in a separate `schemas/` directory)
- Rules, labels, engines, and email templates are tracked as separate object types
- Each org directory has its own `credentials.yaml`
- No top-level `mapping.yaml` — deployment mappings are in `deploy_files/`

## Important Notes

- prd2 does NOT automatically make git commits — use `-c` flag to opt in
- Always run `prd2 pull` before making local edits to ensure latest remote state
- After creating or modifying resources via MCP/API (not through prd2), always run `prd2 pull` to sync local files — never hand-write hook JSON files, let prd2 be the source of truth for local file state
- Use `prd2 deploy run --prefer=source` to prefer local source changes over remote target on conflicts
- Use `prd2 deploy run -p` (plan-only equivalent) or review the shown plan before confirming
- The concurrency limit defaults to 5 parallel requests (override with `--concurrency` or `PRD2_CONCURRENCY` env var)
- After `prd2 purge`, run `prd2 pull` to sync local state

## Typical Workflow

1. `prd2 init my-project` — create project, configure orgs and subdirectories
2. Add API tokens to `credentials.yaml` in each org directory
3. `prd2 pull sandbox-org --all` — download current state
4. Make changes:
   - To **edit existing** objects: edit the local files (`.py` for code, JSON for everything else) — IDs are already in the filenames.
   - To **create new** objects: write the file under a `_[]`-suffixed folder/filename (see "Creating new objects" above). Push will POST and rename to `_[<real_id>]`.
   - To **rename** an object: `git mv` the `_[<id>]` file/folder, update the JSON's `name` field. Push collapses to a single UPDATE.
   - To **delete** an object: `git rm` the file/folder. Must be tracked first.
5. `prd2 pull sandbox-org/dev` — sync any remote changes (or skip if you only made local changes)
6. `prd2 push sandbox-org/dev` — upload local changes; review the plan and confirm. In CI / non-TTY contexts, pass `-y`.
7. Test in source environment
8. `prd2 deploy template create` — create deploy file (first time)
9. `prd2 deploy template update -i ./deploy_files/dev_test.yaml` — update deploy file if objects changed
10. `prd2 deploy run --prefer=source ./deploy_files/dev_test.yaml` — deploy to target
11. Verify in target environment
