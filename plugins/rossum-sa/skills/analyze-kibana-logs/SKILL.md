---
name: analyze-kibana-logs 
description: "Search Elasticsearch logs via Teleport mTLS. Use when asked to search logs, trace requests across services, debug webhook failures, or investigate job errors."
---
# Elasticsearch Log Search via Teleport

## Access Setup

Logs are accessed via Teleport mTLS (NOT API keys). The `$AGENT_ELK_TOKEN` env var exists but is NOT used.

### Step 1: Login to Teleport App

```bash
tsh app login logging-es-<cluster>
```

### Step 2: Determine Cert Paths

```bash
# User email determines cert path
USER_EMAIL=$(git config user.email)
CERT_DIR=~/.tsh/keys/teleport.rossum.cloud/${USER_EMAIL}-app/teleport.rossum.cloud
```

### Step 3: Query with curl

```bash
curl -s --cert "${CERT_DIR}/logging-es-<cluster>.crt" \
     --key "${CERT_DIR}/logging-es-<cluster>.key" \
     "https://logging-es-<cluster>.teleport.rossum.cloud/<index>/_search" \
     -H 'Content-Type: application/json' \
     -d '<query>'
```

## Available Clusters

| Cluster | Purpose |
|---------|---------|
| `dev-eu` | Development environment |
| `prod-eu` | Production EU |
| `prod-eu2` | Production EU2 |
| `prod-us2` | Production US2 |
| `prod-jp` | Production Japan |
| `dhl-eu` | DHL-specific EU cluster |
| `train-eu` | Training environment |
| `rossum-cicd` | CI/CD infrastructure |

## Index Patterns

| Index | Contents |
|-------|----------|
| `fluentd-*` | Kubernetes service logs (most common) |
| `lambdas-*` | AWS Lambda function logs |
| `ses-*` | SES email logs |

## Log Structure (fluentd-\*)

The `log` field in `fluentd-*` indices contains raw structlog JSON. Key parsed fields inside `log`:

| Field | Description |
|-------|-------------|
| `event` | Structlog event name (e.g., `webhook_processed`, `creating_default_index`) |
| `level` | Log level: `debug`, `info`, `warning`, `error`, `critical` |
| `logger` | Python logger name (module path) |
| `trace_id` | OpenTelemetry trace ID (32-char hex, propagated across services) |
| `span_id` | OpenTelemetry span ID (16-char hex) |
| `request_id` | Per-request UUID (from webhook body or generated) |
| `correlation_id` | Correlation ID for cross-service tracking |
| `organization_id` | Elis organization ID |
| `annotation_id` | Elis annotation ID |
| `queue_id` | Elis queue ID |
| `hook_id` | Elis hook ID |
| `hook_event` | Hook event type (e.g., `invocation.started`) |
| `timestamp` | ISO timestamp from structlog |
| `request_method` | HTTP method (GET, POST, etc.) |
| `request_path` | HTTP request path |
| `request_processing_time_ms` | Processing time in milliseconds |
| `status_code` | HTTP response status code |
| `request_source` | Request origin |

## Filter Fields

| Field | Description | Examples |
|-------|-------------|----------|
| `kubernetes_container_name.keyword` | Service name (matches `svc/` dirs) | `master-data-hub`, `data-storage`, `job-enqueuer`, `job-tracker`, `worker`, `einvoice-dispatcher`, `coupa-integration-service`, `file-storage-export`, `task-manager` |
| `kubernetes_namespace_name.keyword` | Environment/namespace | `master-se`, `develop-se`, `master-pexe`, `review-*` |

## Query Templates

### Basic: Search by Service and Event

```bash
curl -s --cert "${CERT_DIR}/logging-es-<cluster>.crt" \
     --key "${CERT_DIR}/logging-es-<cluster>.key" \
     "https://logging-es-<cluster>.teleport.rossum.cloud/fluentd-*/_search" \
     -H 'Content-Type: application/json' \
     -d '{
  "size": 50,
  "sort": [{"@timestamp": "desc"}],
  "query": {
    "bool": {
      "must": [
        {"term": {"kubernetes_container_name.keyword": "<service-name>"}},
        {"term": {"kubernetes_namespace_name.keyword": "<namespace>"}},
        {"match_phrase": {"log": "\"event\": \"<event_name>\""}}
      ],
      "filter": [
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ]
    }
  }
}'
```

### Search by Log Level

```bash
curl -s --cert "${CERT_DIR}/logging-es-<cluster>.crt" \
     --key "${CERT_DIR}/logging-es-<cluster>.key" \
     "https://logging-es-<cluster>.teleport.rossum.cloud/fluentd-*/_search" \
     -H 'Content-Type: application/json' \
     -d '{
  "size": 50,
  "sort": [{"@timestamp": "desc"}],
  "query": {
    "bool": {
      "must": [
        {"term": {"kubernetes_container_name.keyword": "<service-name>"}},
        {"match_phrase": {"log": "\"level\": \"error\""}}
      ],
      "filter": [
        {"range": {"@timestamp": {"gte": "now-24h"}}}
      ]
    }
  }
}'
```

### Search by Trace ID (Cross-Service)

```bash
curl -s --cert "${CERT_DIR}/logging-es-<cluster>.crt" \
     --key "${CERT_DIR}/logging-es-<cluster>.key" \
     "https://logging-es-<cluster>.teleport.rossum.cloud/fluentd-*/_search" \
     -H 'Content-Type: application/json' \
     -d '{
  "size": 100,
  "sort": [{"@timestamp": "asc"}],
  "query": {
    "bool": {
      "must": [
        {"match_phrase": {"log": "\"trace_id\": \"<trace_id>\""}}
      ],
      "filter": [
        {"term": {"kubernetes_namespace_name.keyword": "<namespace>"}}
      ]
    }
  }
}'
```

### Search by Organization ID

```bash
curl -s --cert "${CERT_DIR}/logging-es-<cluster>.crt" \
     --key "${CERT_DIR}/logging-es-<cluster>.key" \
     "https://logging-es-<cluster>.teleport.rossum.cloud/fluentd-*/_search" \
     -H 'Content-Type: application/json' \
     -d '{
  "size": 50,
  "sort": [{"@timestamp": "desc"}],
  "query": {
    "bool": {
      "must": [
        {"match_phrase": {"log": "\"organization_id\": <org_id>"}}
      ],
      "filter": [
        {"range": {"@timestamp": {"gte": "now-6h"}}}
      ]
    }
  }
}'
```

## Troubleshooting Playbooks

### Playbook 1: Trace a Failed Webhook

1. **Find error logs for the hook:**

```bash
# Filter by hook_id and error level
curl ... -d '{
  "size": 20,
  "sort": [{"@timestamp": "desc"}],
  "query": {
    "bool": {
      "must": [
        {"match_phrase": {"log": "\"hook_id\": <hook_id>"}},
        {"match_phrase": {"log": "\"level\": \"error\""}}
      ],
      "filter": [
        {"term": {"kubernetes_namespace_name.keyword": "<namespace>"}},
        {"range": {"@timestamp": {"gte": "now-24h"}}}
      ]
    }
  }
}'
```

2. **Extract the `correlation_id` from the error log.**

1. **Follow the correlation_id across services:**

```bash
# Search all services for the same correlation_id
curl ... -d '{
  "size": 100,
  "sort": [{"@timestamp": "asc"}],
  "query": {
    "bool": {
      "must": [
        {"match_phrase": {"log": "\"correlation_id\": \"<correlation_id>\""}}
      ],
      "filter": [
        {"term": {"kubernetes_namespace_name.keyword": "<namespace>"}}
      ]
    }
  }
}'
```

4. **Check the full request flow:** Look at `request_processing_time_ms` and `status_code` fields to identify where the failure occurred.

### Playbook 2: Trace a Job Failure

1. **Search job-worker logs for the correlation_id:**

```bash
curl ... -d '{
  "size": 50,
  "sort": [{"@timestamp": "asc"}],
  "query": {
    "bool": {
      "must": [
        {"term": {"kubernetes_container_name.keyword": "worker"}},
        {"match_phrase": {"log": "\"correlation_id\": \"<correlation_id>\""}}
      ],
      "filter": [
        {"term": {"kubernetes_namespace_name.keyword": "<namespace>"}},
        {"range": {"@timestamp": {"gte": "now-24h"}}}
      ]
    }
  }
}'
```

2. **Look for error events** in the results — check `event` field for failure indicators.

1. **Cross-reference with job-enqueuer and job-tracker** logs using the same `correlation_id`.

### Playbook 3: Cross-Service Request Tracing

Use `trace_id` (OpenTelemetry) to follow a request across all services:

1. **Get the trace_id** from any log entry in the request flow.

1. **Search across all services** using the trace_id (see "Search by Trace ID" template above).

1. **Sort by timestamp ascending** to see the chronological flow.

1. **Check `kubernetes_container_name.keyword`** to see which services were involved.

## Structlog Configuration

The logging setup is in `lib/lib-observability/sex/lib_observability/logging.py`:

- **OpenTelemetry trace context** is added to every log via `_add_otel_trace_context` (adds `trace_id` and `span_id`)
- **Timestamps** are ISO format via `structlog.processors.TimeStamper(fmt="iso")`
- **Request details** (org_id, annotation_id, queue_id, hook_id) come from webhook body parsing via `get_request_details()`
- **JSON format** in production, console format for local development
- **Sentry integration** is enabled for ERROR-level logs when `SENTRY_ENABLED=True`

## Tips

- Always use `.keyword` suffix for exact match on `kubernetes_container_name` and `kubernetes_namespace_name`
- Use `match_phrase` with the JSON-encoded field pattern when searching inside the `log` field
- Time ranges: `now-1h`, `now-24h`, `now-7d` are the most common
- Add `"_source": ["@timestamp", "log", "kubernetes_container_name"]` to limit response size
- Use `"size": 0` with aggregations to get counts without documents