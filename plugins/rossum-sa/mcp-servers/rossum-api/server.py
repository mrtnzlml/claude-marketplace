#!/usr/bin/env python3
"""MCP server for Rossum APIs."""

import json
import ssl
import sys
import urllib.error
import urllib.request
from urllib.parse import urlencode, urlparse

try:
    import certifi
    _ssl_context = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _ssl_context = ssl.create_default_context()

_cached_base_url = None
_cached_token = None
_token_validated = False


# --- MCP protocol ---


def _log(msg):
    print(msg, file=sys.stderr, flush=True)


def read_message():
    line = sys.stdin.readline()
    if not line:
        return None
    try:
        return json.loads(line)
    except (json.JSONDecodeError, ValueError) as e:
        _log(f"Failed to parse message: {e}")
        return None


def write_message(msg):
    sys.stdout.write(json.dumps(msg, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def respond(request_id, result):
    write_message({"jsonrpc": "2.0", "id": request_id, "result": result})


def respond_error(request_id, code, message):
    write_message({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}})


def tool_result(request_id, text, is_error=False):
    result = {"content": [{"type": "text", "text": text}]}
    if is_error:
        result["isError"] = True
    respond(request_id, result)


# --- URL validation ---


def _validate_base_url(url):
    """Validate and normalize a base URL. Returns origin or None."""
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    if parsed.scheme != "https":
        return None
    if not parsed.hostname:
        return None
    origin = f"https://{parsed.hostname}"
    if parsed.port and parsed.port != 443:
        origin += f":{parsed.port}"
    return origin


# --- Connection state ---


def _check_health(base_url):
    """Check if the Data Storage API is reachable (no auth required)."""
    req = urllib.request.Request(
        f"{base_url}/svc/data-storage/api/healthz",
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10, context=_ssl_context) as resp:
            return resp.status == 200
    except Exception:
        return False


def _probe_token(base_url, token):
    """Validate a token with a lightweight API call. Returns (ok, error_detail)."""
    req = urllib.request.Request(
        f"{base_url}/svc/data-storage/api/v1/collections/list",
        data=json.dumps({"nameOnly": True}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10, context=_ssl_context) as resp:
            return (True, None)
    except urllib.error.HTTPError as e:
        return (False, f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:200]}")
    except ssl.SSLError as e:
        return (False, f"SSL error: {e}. Try: python3 -m pip install certifi")
    except Exception as e:
        return (False, f"{type(e).__name__}: {e}")


def _invalidate_connection():
    """Clear cached connection state."""
    global _cached_base_url, _cached_token, _token_validated
    _cached_base_url = None
    _cached_token = None
    _token_validated = False


def _ensure_connection(request_id):
    """Guard: return cached (base_url, token) or send an error directing to rossum_set_token."""
    if _token_validated and _cached_base_url and _cached_token:
        return (_cached_base_url, _cached_token)

    tool_result(
        request_id,
        "Not connected to Rossum. Call rossum_set_token(token='...', baseUrl='...') "
        "to establish a connection. Ask the user for the token and base URL if unknown.",
        is_error=True,
    )
    return (None, None)


# --- HTTP helpers ---


def _http_request(request_id, url, *, method="GET", body=None):
    """Make an authenticated HTTP request. Returns parsed JSON or None (error sent).

    Callers must call _ensure_connection first for correct URL construction.
    """
    token = _cached_token
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=130, context=_ssl_context) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        if e.code == 401:
            _invalidate_connection()
            tool_result(
                request_id,
                f"Authentication failed (HTTP 401). Token may be expired. "
                f"Ask the user for a new token, then call rossum_set_token.\n{error_body}",
                is_error=True,
            )
            return None
        tool_result(request_id, f"HTTP {e.code}: {error_body}", is_error=True)
        return None
    except Exception as e:
        tool_result(request_id, f"Error: {e}", is_error=True)
        return None


def _data_storage_call(request_id, path, body):
    """POST to a Data Storage API endpoint."""
    base_url, _ = _ensure_connection(request_id)
    if not base_url:
        return
    url = f"{base_url}/svc/data-storage/api{path}"
    result = _http_request(request_id, url, method="POST", body=body)
    if result is not None:
        tool_result(request_id, json.dumps(result, indent=2))


def _rossum_get(request_id, path):
    """GET a single Rossum API resource and return it as JSON."""
    base_url, _ = _ensure_connection(request_id)
    if not base_url:
        return
    result = _http_request(request_id, f"{base_url}{path}")
    if result is not None:
        tool_result(request_id, json.dumps(result, indent=2))


def _rossum_post(request_id, path, body):
    """POST to a Rossum API endpoint and return the result as JSON."""
    base_url, _ = _ensure_connection(request_id)
    if not base_url:
        return
    result = _http_request(request_id, f"{base_url}{path}", method="POST", body=body)
    if result is not None:
        tool_result(request_id, json.dumps(result, indent=2))


def _rossum_delete(request_id, path):
    """DELETE a Rossum API resource. Expects 204 No Content."""
    base_url, _ = _ensure_connection(request_id)
    if not base_url:
        return
    token = _cached_token
    req = urllib.request.Request(
        f"{base_url}{path}",
        headers={"Authorization": f"Bearer {token}"},
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=_ssl_context) as resp:
            tool_result(request_id, f"Deleted successfully (HTTP {resp.status}).")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        if e.code == 401:
            _invalidate_connection()
            tool_result(request_id, f"Authentication failed (HTTP 401). Token may be expired.\n{error_body}", is_error=True)
        else:
            tool_result(request_id, f"HTTP {e.code}: {error_body}", is_error=True)
    except Exception as e:
        tool_result(request_id, f"Error: {e}", is_error=True)


def _rossum_list(request_id, endpoint, params, *, pick_fields=None, max_results=None):
    """Paginate a Rossum API list endpoint and return collected results."""
    base_url, _ = _ensure_connection(request_id)
    if not base_url:
        return
    results = _paginate(
        request_id, f"{base_url}{endpoint}?{urlencode(params)}",
        max_results=max_results, pick_fields=pick_fields,
    )
    if results is not None:
        tool_result(request_id, json.dumps({"total": len(results), "results": results}, indent=2))


# --- Tool registration ---


TOOLS = {}
HANDLERS = {}


_READ_ONLY = {"readOnlyHint": True}
_WRITE = {"readOnlyHint": False, "destructiveHint": False}
_DESTRUCTIVE = {"readOnlyHint": False, "destructiveHint": True}


def _tool(name, description, schema, annotations=None):
    """Decorator: register a tool definition and its handler together."""
    def decorator(handler):
        tool_def = {"name": name, "description": description, "inputSchema": schema}
        if annotations:
            tool_def["annotations"] = annotations
        TOOLS[name] = tool_def
        HANDLERS[name] = handler
        return handler
    return decorator


# --- Tools ---


@_tool(
    "rossum_set_token",
    "Set the Rossum API connection for this session. Provide a token and base URL.",
    {
        "type": "object",
        "required": ["token", "baseUrl"],
        "properties": {
            "token": {
                "type": "string",
                "description": "Rossum API Bearer token.",
            },
            "baseUrl": {
                "type": "string",
                "description": (
                    "Base URL of the Rossum environment "
                    "(e.g. https://elis.rossum.ai, https://customer-dev.rossum.app)."
                ),
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_set_token(request_id, arguments):
    global _cached_base_url, _cached_token, _token_validated

    token = arguments.get("token", "")
    raw_url = arguments.get("baseUrl", "")

    if not token:
        return tool_result(request_id, "Missing 'token'.", is_error=True)

    base_url = _validate_base_url(raw_url)
    if not base_url:
        return tool_result(request_id, f"Invalid base URL: {raw_url}. Must be HTTPS.", is_error=True)

    ok, detail = _probe_token(base_url, token)
    if not ok:
        _invalidate_connection()
        return tool_result(
            request_id,
            f"Cannot connect to {base_url}: {detail}. "
            f"If this is not an auth error, the token may still be valid — check the error above.",
            is_error=True,
        )

    _cached_base_url = base_url
    _cached_token = token
    _token_validated = True
    return tool_result(request_id, f"Connected to {base_url}. Token validated for this session.")


@_tool(
    "rossum_whoami",
    "Returns the authenticated user's identity, organization, and role. "
    "Useful for checking permissions and orientation after connecting.",
    {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_whoami(request_id, arguments):
    _rossum_get(request_id, "/api/v1/auth/user")


@_tool(
    "data_storage_healthz",
    "Checks if the Rossum Data Storage API is reachable. Does not require authentication. "
    "Uses the connected environment if available, otherwise checks the default (elis.rossum.ai).",
    {
        "type": "object",
        "properties": {
            "baseUrl": {
                "type": "string",
                "description": "Base URL to check. Defaults to the connected environment or elis.rossum.ai.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_healthz(request_id, arguments):
    raw_url = arguments.get("baseUrl", "")
    if raw_url:
        validated = _validate_base_url(raw_url)
        if not validated:
            return tool_result(request_id, f"Invalid base URL: {raw_url}. Must be an HTTPS URL.", is_error=True)
        source = "provided"
    elif _cached_base_url:
        validated = _cached_base_url
        source = "connected environment"
    else:
        validated = "https://elis.rossum.ai"
        source = "default (no connection established)"

    if _check_health(validated):
        return tool_result(request_id, f"Data Storage API at {validated} is healthy ({source}).")

    return tool_result(request_id, f"Data Storage API at {validated} is not reachable ({source}).", is_error=True)


@_tool(
    "data_storage_list_collections",
    "Lists available collections in Rossum Data Storage.",
    {
        "type": "object",
        "properties": {
            "filter": {"type": "object", "description": "Optional query filter for collections."},
            "nameOnly": {"type": "boolean", "description": "Return only collection names (default: true)."},
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_list_collections(request_id, arguments):
    body = {}
    if "filter" in arguments:
        body["filter"] = arguments["filter"]
    if "nameOnly" in arguments:
        body["nameOnly"] = arguments["nameOnly"]
    return _data_storage_call(request_id, "/v1/collections/list", body)


@_tool(
    "data_storage_aggregate",
    "Performs a MongoDB aggregation pipeline on a Rossum Data Storage collection. "
    "Runtime is limited to 120 seconds. Always include a $limit stage to avoid unbounded results.",
    {
        "type": "object",
        "required": ["collectionName", "pipeline"],
        "properties": {
            "collectionName": {"type": "string", "description": "The name of the collection to aggregate on."},
            "pipeline": {
                "type": "array",
                "items": {"type": "object"},
                "description": "The MongoDB aggregation pipeline stages.",
            },
            "collation": {"type": "object", "description": "Collation settings for the aggregation."},
            "let": {"type": "object", "description": "Variables accessible in the pipeline."},
            "options": {"type": "object", "description": "Additional aggregation options."},
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_aggregate(request_id, arguments):
    body = {"pipeline": arguments.get("pipeline", []), "collectionName": arguments["collectionName"]}
    for key in ("collation", "let", "options"):
        if key in arguments:
            body[key] = arguments[key]
    return _data_storage_call(request_id, "/v1/data/aggregate", body)


_INDEX_LIST_SCHEMA = {
    "type": "object",
    "required": ["collectionName"],
    "properties": {
        "collectionName": {"type": "string", "description": "The name of the collection."},
        "nameOnly": {"type": "boolean", "description": "Return only index names (default: true)."},
    },
    "additionalProperties": False,
}


def _handle_index_list(request_id, arguments, path):
    body = {"collectionName": arguments.get("collectionName", "")}
    if "nameOnly" in arguments:
        body["nameOnly"] = arguments["nameOnly"]
    return _data_storage_call(request_id, path, body)


@_tool("data_storage_list_indexes", "Lists all indexes of a Rossum Data Storage collection.", _INDEX_LIST_SCHEMA, annotations=_READ_ONLY)
def handle_list_indexes(request_id, arguments):
    return _handle_index_list(request_id, arguments, "/v1/indexes/list")


@_tool(
    "data_storage_list_search_indexes",
    "Lists all Atlas Search indexes of a Rossum Data Storage collection.",
    _INDEX_LIST_SCHEMA,
    annotations=_READ_ONLY,
)
def handle_list_search_indexes(request_id, arguments):
    return _handle_index_list(request_id, arguments, "/v1/search_indexes/list")


@_tool(
    "data_storage_create_index",
    "Creates a database index on a Rossum Data Storage collection. "
    "This is a write operation that modifies the collection's index configuration.",
    {
        "type": "object",
        "required": ["collectionName", "indexName", "keys"],
        "properties": {
            "collectionName": {"type": "string", "description": "The name of the collection."},
            "indexName": {"type": "string", "description": "Name for the index."},
            "keys": {
                "type": "object",
                "description": (
                    "Index key specification. Keys are field paths, values are "
                    "1 (ascending), -1 (descending), or 'text'."
                ),
            },
            "options": {
                "type": "object",
                "description": "Index options (e.g. unique, sparse, expireAfterSeconds).",
            },
        },
        "additionalProperties": False,
    },
    annotations=_WRITE,
)
def handle_create_index(request_id, arguments):
    body = {
        "collectionName": arguments["collectionName"],
        "indexName": arguments["indexName"],
        "keys": arguments["keys"],
    }
    if "options" in arguments:
        body["options"] = arguments["options"]
    return _data_storage_call(request_id, "/v1/indexes/create", body)


@_tool(
    "data_storage_create_search_index",
    "Creates an Atlas Search index on a Rossum Data Storage collection. "
    "This is a write operation that modifies the collection's search index configuration.",
    {
        "type": "object",
        "required": ["collectionName", "mappings"],
        "properties": {
            "collectionName": {"type": "string", "description": "The name of the collection."},
            "mappings": {
                "type": "object",
                "description": "Atlas Search index mappings (e.g. {\"dynamic\": true}).",
            },
            "indexName": {
                "type": "string",
                "description": "Name for the search index. Defaults to 'default' if not specified.",
            },
            "analyzers": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Custom analyzer definitions for the search index.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_WRITE,
)
def handle_create_search_index(request_id, arguments):
    body = {"collectionName": arguments["collectionName"], "mappings": arguments["mappings"]}
    if "indexName" in arguments:
        body["indexName"] = arguments["indexName"]
    if "analyzers" in arguments:
        body["analyzers"] = arguments["analyzers"]
    return _data_storage_call(request_id, "/v1/search_indexes/create", body)


@_tool(
    "data_storage_drop_index",
    "Drops a database index from a Rossum Data Storage collection. "
    "This is a destructive write operation.",
    {
        "type": "object",
        "required": ["collectionName", "indexName"],
        "properties": {
            "collectionName": {"type": "string", "description": "The name of the collection."},
            "indexName": {"type": "string", "description": "The name of the index to drop."},
        },
        "additionalProperties": False,
    },
    annotations=_DESTRUCTIVE,
)
def handle_drop_index(request_id, arguments):
    return _data_storage_call(request_id, "/v1/indexes/drop", {
        "collectionName": arguments["collectionName"],
        "indexName": arguments["indexName"],
    })


@_tool(
    "data_storage_drop_search_index",
    "Drops an Atlas Search index from a Rossum Data Storage collection. "
    "This is a destructive write operation.",
    {
        "type": "object",
        "required": ["collectionName", "indexName"],
        "properties": {
            "collectionName": {"type": "string", "description": "The name of the collection."},
            "indexName": {"type": "string", "description": "The name of the search index to drop."},
        },
        "additionalProperties": False,
    },
    annotations=_DESTRUCTIVE,
)
def handle_drop_search_index(request_id, arguments):
    return _data_storage_call(request_id, "/v1/search_indexes/drop", {
        "collectionName": arguments["collectionName"],
        "indexName": arguments["indexName"],
    })


@_tool(
    "data_storage_find",
    "Queries documents in a Rossum Data Storage collection. Simpler than aggregate "
    "for basic lookups. Returns matching documents up to the specified limit.",
    {
        "type": "object",
        "required": ["collectionName"],
        "properties": {
            "collectionName": {"type": "string", "description": "The name of the collection."},
            "query": {"type": "object", "description": "MongoDB query filter (default: {} returns all)."},
            "projection": {"type": "object", "description": "Fields to include (1) or exclude (0)."},
            "sort": {"type": "object", "description": "Sort specification (e.g. {\"createdAt\": -1})."},
            "limit": {
                "type": "integer",
                "description": "Maximum documents to return (default: 50, max: 1000).",
            },
            "skip": {
                "type": "integer",
                "description": "Number of documents to skip before returning results.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_find(request_id, arguments):
    body = {"collectionName": arguments["collectionName"], "query": arguments.get("query", {})}
    if "projection" in arguments:
        body["projection"] = arguments["projection"]
    if "sort" in arguments:
        body["sort"] = arguments["sort"]
    body["limit"] = min(arguments.get("limit", 50), 1000)
    if "skip" in arguments:
        body["skip"] = arguments["skip"]
    return _data_storage_call(request_id, "/v1/data/find", body)


def _paginate(request_id, url, *, max_results=None, pick_fields=None):
    """Auto-paginate a Rossum list endpoint. Returns list of results or None on error."""
    all_results = []
    while url:
        page = _http_request(request_id, url)
        if page is None:
            return None
        for item in page.get("results", []):
            if max_results and len(all_results) >= max_results:
                break
            all_results.append({k: item[k] for k in pick_fields if k in item} if pick_fields else item)
        if max_results and len(all_results) >= max_results:
            break
        next_url = page.get("pagination", {}).get("next")
        if not next_url:
            break
        if _validate_base_url(next_url) != _validate_base_url(url):
            break
        url = next_url
    return all_results


_USER_FIELDS = ("id", "email", "first_name", "last_name", "is_active")


@_tool(
    "rossum_list_users",
    "Lists all users in the Rossum organization. Auto-paginates to return every user.",
    {
        "type": "object",
        "properties": {
            "is_active": {"type": "boolean", "description": "Filter by active status. Omit to return all users."},
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_list_users(request_id, arguments):
    params = [("page_size", 100)]
    if "is_active" in arguments:
        params.append(("is_active", "true" if arguments["is_active"] else "false"))
    _rossum_list(request_id, "/api/v1/users", params, pick_fields=_USER_FIELDS)


@_tool(
    "rossum_list_audit_logs",
    "List audit log entries. Requires admin or organization group admin role. "
    "Logs are retained for 1 year. Returns up to max_results entries (default 100).",
    {
        "type": "object",
        "required": ["object_type"],
        "properties": {
            "object_type": {
                "type": "string",
                "description": "Object type to query: 'document', 'annotation', or 'user'.",
            },
            "action": {
                "type": "string",
                "description": (
                    "Filter by action. Allowed values depend on object_type: "
                    "document: 'create'. "
                    "annotation: 'update-status'. "
                    "user: 'create', 'delete', 'purge', 'update', 'destroy', "
                    "'app_load', 'reset-password', 'change-password'."
                ),
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum entries to return (default: 100, max: 1000).",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_list_audit_logs(request_id, arguments):
    max_results = min(arguments.get("max_results", 100), 1000)
    params = [("page_size", min(max_results, 100)), ("object_type", arguments["object_type"])]
    if "action" in arguments:
        params.append(("action", arguments["action"]))
    _rossum_list(request_id, "/api/v1/audit_logs", params, max_results=max_results)


@_tool(
    "rossum_get_hook_secret_keys",
    "Retrieves the list of secret key names configured on a hook. "
    "Only key names are returned — values are encrypted and cannot be retrieved via the API.",
    {
        "type": "object",
        "required": ["hook_id"],
        "properties": {
            "hook_id": {
                "type": "integer",
                "description": "The hook ID.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_get_hook_secret_keys(request_id, arguments):
    _rossum_get(request_id, f"/api/v1/hooks/{arguments['hook_id']}/secrets_keys")


_ANNOTATION_FIELDS = ("id", "queue", "status", "document", "modifier", "modified_at", "confirmed_at", "exported_at")


@_tool(
    "rossum_list_annotations",
    "Lists annotations in a queue. Annotations represent documents being processed. "
    "Use this to find annotation IDs for rossum_get_annotation_content.",
    {
        "type": "object",
        "required": ["queue"],
        "properties": {
            "queue": {
                "type": "integer",
                "description": "Queue ID to list annotations from.",
            },
            "status": {
                "type": "string",
                "description": (
                    "Filter by status: 'to_review', 'reviewing', 'confirmed', "
                    "'rejected', 'exporting', 'exported', 'failed_export', "
                    "'postponed', 'deleted', 'purged', 'split', 'importing'."
                ),
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum annotations to return (default: 50, max: 500).",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_list_annotations(request_id, arguments):
    max_results = min(arguments.get("max_results", 50), 500)
    params = [("page_size", min(max_results, 100)), ("queue", arguments["queue"])]
    if "status" in arguments:
        params.append(("status", arguments["status"]))
    _rossum_list(
        request_id, "/api/v1/annotations", params,
        max_results=max_results, pick_fields=_ANNOTATION_FIELDS,
    )


@_tool(
    "rossum_get_annotation_content",
    "Retrieves the extracted data (content) of a single annotation. "
    "Returns the annotation's data tree: sections containing datapoints and multivalues (tables).",
    {
        "type": "object",
        "required": ["annotation_id"],
        "properties": {
            "annotation_id": {
                "type": "integer",
                "description": "The annotation ID.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_get_annotation_content(request_id, arguments):
    _rossum_get(request_id, f"/api/v1/annotations/{arguments['annotation_id']}/content")


_QUEUE_FIELDS = ("id", "name", "workspace", "schema", "hooks", "status", "dedicated_engine")


@_tool(
    "rossum_list_queues",
    "Lists all queues in the Rossum organization. Queues are the core processing unit — "
    "each represents a document intake pipeline with its own schema and hooks.",
    {
        "type": "object",
        "properties": {
            "workspace": {
                "type": "integer",
                "description": "Filter by workspace ID.",
            },
            "status": {
                "type": "string",
                "description": "Filter by status: 'active', 'inactive', or 'deletion_requested'.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_list_queues(request_id, arguments):
    params = [("page_size", 100)]
    if "workspace" in arguments:
        params.append(("workspace", arguments["workspace"]))
    if "status" in arguments:
        params.append(("status", arguments["status"]))
    _rossum_list(request_id, "/api/v1/queues", params, pick_fields=_QUEUE_FIELDS)


@_tool(
    "rossum_get_queue",
    "Retrieves full details of a single queue including inbox, connector, locale, "
    "and all configuration. Use rossum_list_queues first to find queue IDs.",
    {
        "type": "object",
        "required": ["queue_id"],
        "properties": {
            "queue_id": {
                "type": "integer",
                "description": "The queue ID.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_get_queue(request_id, arguments):
    _rossum_get(request_id, f"/api/v1/queues/{arguments['queue_id']}")


_HOOK_FIELDS = ("id", "name", "type", "events", "queues", "active", "run_after", "token_owner")


@_tool(
    "rossum_list_hooks",
    "Lists all hooks (extensions) in the Rossum organization. Hooks are serverless functions "
    "or webhook endpoints triggered by queue events.",
    {
        "type": "object",
        "properties": {
            "queue": {
                "type": "integer",
                "description": "Filter by queue ID — return only hooks attached to this queue.",
            },
            "active": {
                "type": "boolean",
                "description": "Filter by active status.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_list_hooks(request_id, arguments):
    params = [("page_size", 100)]
    if "queue" in arguments:
        params.append(("queue", arguments["queue"]))
    if "active" in arguments:
        params.append(("active", "true" if arguments["active"] else "false"))
    _rossum_list(request_id, "/api/v1/hooks", params, pick_fields=_HOOK_FIELDS)


@_tool(
    "rossum_get_hook",
    "Retrieves full details of a single hook (extension) including its code, URL, "
    "settings, secrets key names, and configuration. Use rossum_list_hooks first to find hook IDs.",
    {
        "type": "object",
        "required": ["hook_id"],
        "properties": {
            "hook_id": {
                "type": "integer",
                "description": "The hook ID.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_get_hook(request_id, arguments):
    _rossum_get(request_id, f"/api/v1/hooks/{arguments['hook_id']}")


@_tool(
    "rossum_create_hook",
    "Creates a new hook (extension) in the Rossum organization. Hooks can be serverless functions "
    "(type='function') executed in Python 3.12 or webhooks (type='webhook') that POST to an external URL. "
    "This is a write operation.",
    {
        "type": "object",
        "required": ["name", "type", "events", "config"],
        "properties": {
            "name": {
                "type": "string",
                "description": "Display name for the hook.",
            },
            "type": {
                "type": "string",
                "description": "Hook type: 'function' (serverless Python 3.12) or 'webhook' (external HTTP endpoint).",
            },
            "events": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Events that trigger this hook. Common values: "
                    "'annotation_content.initialize', 'annotation_content.started', "
                    "'annotation_content.updated', 'annotation_content.confirm', "
                    "'annotation_content.export', 'annotation_content.user_update', "
                    "'email.received', 'invocation.manual'."
                ),
            },
            "config": {
                "type": "object",
                "description": (
                    "Type-specific configuration. "
                    "For function: {\"runtime\": \"python3.12\", \"code\": \"def rossum_hook_request_handler(payload):\\n    return payload\"}. "
                    "For webhook: {\"url\": \"https://example.com/webhook\"}. "
                    "Optional config keys: timeout_s (default 30), retry_count, payload_logging_enabled."
                ),
            },
            "queue_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Queue IDs to attach this hook to. Omit to create unattached.",
            },
            "active": {
                "type": "boolean",
                "description": "Whether the hook is active (default: true).",
            },
            "run_after": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Hook IDs that must run before this one (execution ordering).",
            },
            "sideload": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Additional data to include in payloads (e.g. ['schemas']).",
            },
            "token_owner": {
                "type": "integer",
                "description": "User ID whose permissions the hook uses for API calls.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_WRITE,
)
def handle_create_hook(request_id, arguments):
    base_url, _ = _ensure_connection(request_id)
    if not base_url:
        return
    body = {
        "name": arguments["name"],
        "type": arguments["type"],
        "events": arguments["events"],
        "config": arguments["config"],
        "active": arguments.get("active", True),
        "queues": [f"{base_url}/api/v1/queues/{qid}" for qid in arguments.get("queue_ids", [])],
    }
    if "run_after" in arguments:
        body["run_after"] = [f"{base_url}/api/v1/hooks/{hid}" for hid in arguments["run_after"]]
    if "sideload" in arguments:
        body["sideload"] = arguments["sideload"]
    if "token_owner" in arguments:
        body["token_owner"] = f"{base_url}/api/v1/users/{arguments['token_owner']}"
    _rossum_post(request_id, "/api/v1/hooks", body)


@_tool(
    "rossum_delete_hook",
    "Deletes a hook (extension) from the Rossum organization. "
    "This is a destructive operation that cannot be undone.",
    {
        "type": "object",
        "required": ["hook_id"],
        "properties": {
            "hook_id": {
                "type": "integer",
                "description": "The hook ID to delete.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_DESTRUCTIVE,
)
def handle_delete_hook(request_id, arguments):
    _rossum_delete(request_id, f"/api/v1/hooks/{arguments['hook_id']}")


@_tool(
    "rossum_get_schema",
    "Retrieves the full schema definition of a queue. The schema defines all datapoints "
    "(fields), sections, multivalue (table) structures, and their validation rules.",
    {
        "type": "object",
        "required": ["schema_id"],
        "properties": {
            "schema_id": {
                "type": "integer",
                "description": "The schema ID (found in queue.schema URL).",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_get_schema(request_id, arguments):
    _rossum_get(request_id, f"/api/v1/schemas/{arguments['schema_id']}")


_SCHEMA_FIELDS = ("id", "name", "queues")


@_tool(
    "rossum_list_schemas",
    "Lists all schemas in the Rossum organization. Schemas define the data structure "
    "(fields, sections, tables) for document extraction in queues.",
    {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_list_schemas(request_id, arguments):
    _rossum_list(request_id, "/api/v1/schemas", [("page_size", 100)], pick_fields=_SCHEMA_FIELDS)


_WORKSPACE_FIELDS = ("id", "name", "organization", "queues", "autopilot")


@_tool(
    "rossum_list_workspaces",
    "Lists all workspaces in the Rossum organization. Workspaces group queues "
    "and define organizational boundaries.",
    {
        "type": "object",
        "properties": {
            "organization": {
                "type": "integer",
                "description": "Filter by organization ID.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_list_workspaces(request_id, arguments):
    params = [("page_size", 100)]
    if "organization" in arguments:
        params.append(("organization", arguments["organization"]))
    _rossum_list(request_id, "/api/v1/workspaces", params, pick_fields=_WORKSPACE_FIELDS)


@_tool(
    "rossum_get_workspace",
    "Retrieves full details of a single workspace including its queues, organization, "
    "and autopilot settings. Use rossum_list_workspaces first to find workspace IDs.",
    {
        "type": "object",
        "required": ["workspace_id"],
        "properties": {
            "workspace_id": {
                "type": "integer",
                "description": "The workspace ID.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_get_workspace(request_id, arguments):
    _rossum_get(request_id, f"/api/v1/workspaces/{arguments['workspace_id']}")


@_tool(
    "rossum_get_organization",
    "Retrieves details of the organization including name, trial status, and feature flags. "
    "The organization ID can be found in rossum_whoami output.",
    {
        "type": "object",
        "required": ["organization_id"],
        "properties": {
            "organization_id": {
                "type": "integer",
                "description": "The organization ID.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_get_organization(request_id, arguments):
    _rossum_get(request_id, f"/api/v1/organizations/{arguments['organization_id']}")


@_tool(
    "rossum_get_document",
    "Retrieves metadata of a document (original file name, MIME type, creation time, "
    "annotations). Documents are referenced by annotations — extract the document ID "
    "from the annotation's document URL.",
    {
        "type": "object",
        "required": ["document_id"],
        "properties": {
            "document_id": {
                "type": "integer",
                "description": "The document ID.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_get_document(request_id, arguments):
    _rossum_get(request_id, f"/api/v1/documents/{arguments['document_id']}")


_ANNOTATION_DETAIL_FIELDS = (
    "id", "queue", "status", "document", "modifier", "modified_at", "confirmed_at",
    "exported_at", "automated", "messages", "metadata", "created_at", "started_at",
    "relations", "email",
)


@_tool(
    "rossum_get_annotation",
    "Retrieves full metadata of a single annotation including status, messages (validation "
    "errors and automation blockers), metadata (hook state flags), timestamps, and email info. "
    "Use rossum_list_annotations first to find annotation IDs.",
    {
        "type": "object",
        "required": ["annotation_id"],
        "properties": {
            "annotation_id": {
                "type": "integer",
                "description": "The annotation ID.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_get_annotation(request_id, arguments):
    _rossum_get(request_id, f"/api/v1/annotations/{arguments['annotation_id']}")


@_tool(
    "rossum_get_inbox",
    "Retrieves details of a queue's inbox including email address, bounce email, "
    "and document processing settings. The inbox ID is found in the queue detail response.",
    {
        "type": "object",
        "required": ["inbox_id"],
        "properties": {
            "inbox_id": {
                "type": "integer",
                "description": "The inbox ID.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_get_inbox(request_id, arguments):
    _rossum_get(request_id, f"/api/v1/inboxes/{arguments['inbox_id']}")


_CONNECTOR_FIELDS = ("id", "name", "queues", "service_url", "authorization_type", "asynchronous")


@_tool(
    "rossum_list_connectors",
    "Lists all connectors (export integrations) in the Rossum organization. "
    "Connectors define where confirmed documents are exported to.",
    {
        "type": "object",
        "properties": {
            "queue": {
                "type": "integer",
                "description": "Filter by queue ID.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_list_connectors(request_id, arguments):
    params = [("page_size", 100)]
    if "queue" in arguments:
        params.append(("queue", arguments["queue"]))
    _rossum_list(request_id, "/api/v1/connectors", params, pick_fields=_CONNECTOR_FIELDS)


@_tool(
    "rossum_get_connector",
    "Retrieves full details of a single connector (export integration) including "
    "service URL, authorization, parameters, and queue mapping. "
    "Use rossum_list_connectors first to find connector IDs.",
    {
        "type": "object",
        "required": ["connector_id"],
        "properties": {
            "connector_id": {
                "type": "integer",
                "description": "The connector ID.",
            },
        },
        "additionalProperties": False,
    },
    annotations=_READ_ONLY,
)
def handle_get_connector(request_id, arguments):
    _rossum_get(request_id, f"/api/v1/connectors/{arguments['connector_id']}")


# --- Main loop ---


def main():
    while True:
        message = read_message()
        if message is None:
            break

        if not isinstance(message, dict):
            continue

        method = message.get("method")
        request_id = message.get("id")

        try:
            if method == "initialize":
                respond(request_id, {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "rossum-api", "version": "0.1.0"},
                })
            elif method == "notifications/initialized":
                pass
            elif method == "tools/list":
                respond(request_id, {"tools": list(TOOLS.values())})
            elif method == "tools/call":
                params = message.get("params", {})
                name = params.get("name")
                handler = HANDLERS.get(name)
                if handler:
                    handler(request_id, params.get("arguments") or {})
                else:
                    tool_result(request_id, f"Unknown tool: {name}", is_error=True)
            elif method == "ping":
                respond(request_id, {})
            elif request_id is not None:
                respond_error(request_id, -32601, f"Method not found: {method}")
        except Exception as e:
            _log(f"Error handling {method}: {e}")
            if request_id is not None:
                respond_error(request_id, -32603, f"Internal error: {e}")


if __name__ == "__main__":
    main()
