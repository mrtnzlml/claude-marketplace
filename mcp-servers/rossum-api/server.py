#!/usr/bin/env python3
"""MCP server for Rossum APIs (read-only)."""

import json
import sys
import urllib.error
import urllib.request
from urllib.parse import urlencode, urlparse

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
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False


def _probe_token(base_url, token):
    """Validate a token with a lightweight API call."""
    req = urllib.request.Request(
        f"{base_url}/svc/data-storage/api/v1/collections/list",
        data=json.dumps({"nameOnly": True}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False


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
        with urllib.request.urlopen(req, timeout=130) as resp:
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


# --- Tool registration ---


TOOLS = {}
HANDLERS = {}


def _tool(name, description, schema):
    """Decorator: register a tool definition and its handler together."""
    def decorator(handler):
        TOOLS[name] = {"name": name, "description": description, "inputSchema": schema}
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
    },
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

    if not _probe_token(base_url, token):
        _invalidate_connection()
        return tool_result(
            request_id,
            f"Token is invalid or expired for {base_url}. Ask the user for a fresh token.",
            is_error=True,
        )

    _cached_base_url = base_url
    _cached_token = token
    _token_validated = True
    return tool_result(request_id, f"Connected to {base_url}. Token validated for this session.")


@_tool(
    "data_storage_healthz",
    "Checks if the Rossum Data Storage API is reachable. Does not require authentication.",
    {"type": "object", "properties": {}},
)
def handle_healthz(request_id, arguments):
    base_url = _cached_base_url or "https://elis.rossum.ai"
    validated = _validate_base_url(base_url)
    if not validated:
        return tool_result(request_id, f"Invalid base URL: {base_url}. Must be an HTTPS URL.", is_error=True)

    if _check_health(validated):
        return tool_result(request_id, f"Data Storage API at {validated} is healthy.")

    return tool_result(request_id, f"Data Storage API at {validated} is not reachable.", is_error=True)


@_tool(
    "data_storage_list_collections",
    "Lists available collections in Rossum Data Storage.",
    {
        "type": "object",
        "properties": {
            "filter": {"type": "object", "description": "Optional query filter for collections."},
            "nameOnly": {"type": "boolean", "description": "Return only collection names (default: true)."},
        },
    },
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
    "Runtime is limited to 120 seconds.",
    {
        "type": "object",
        "required": ["pipeline"],
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
    },
)
def handle_aggregate(request_id, arguments):
    body = {"pipeline": arguments.get("pipeline", [])}
    for key in ("collectionName", "collation", "let", "options"):
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
}


def _handle_index_list(request_id, arguments, path):
    body = {"collectionName": arguments.get("collectionName", "")}
    if "nameOnly" in arguments:
        body["nameOnly"] = arguments["nameOnly"]
    return _data_storage_call(request_id, path, body)


@_tool("data_storage_list_indexes", "Lists all indexes of a Rossum Data Storage collection.", _INDEX_LIST_SCHEMA)
def handle_list_indexes(request_id, arguments):
    return _handle_index_list(request_id, arguments, "/v1/indexes/list")


@_tool(
    "data_storage_list_search_indexes",
    "Lists all Atlas Search indexes of a Rossum Data Storage collection.",
    _INDEX_LIST_SCHEMA,
)
def handle_list_search_indexes(request_id, arguments):
    return _handle_index_list(request_id, arguments, "/v1/search_indexes/list")


_USER_FIELDS = ("id", "email", "first_name", "last_name", "is_active")


@_tool(
    "rossum_list_users",
    "Lists all users in the Rossum organization. Auto-paginates to return every user.",
    {
        "type": "object",
        "properties": {
            "is_active": {"type": "boolean", "description": "Filter by active status. Omit to return all users."},
        },
    },
)
def handle_list_users(request_id, arguments):
    base_url, _ = _ensure_connection(request_id)
    if not base_url:
        return
    params = ["page_size=100"]
    if "is_active" in arguments:
        params.append(f"is_active={'true' if arguments['is_active'] else 'false'}")

    url = f"{base_url}/api/v1/users?{'&'.join(params)}"
    all_results = []

    while url:
        page = _http_request(request_id, url)
        if page is None:
            return
        for user in page.get("results", []):
            all_results.append({k: user[k] for k in _USER_FIELDS if k in user})
        next_url = page.get("pagination", {}).get("next")
        if not next_url:
            break
        if _validate_base_url(next_url) != _validate_base_url(url):
            break
        url = next_url

    tool_result(request_id, json.dumps({"total": len(all_results), "results": all_results}, indent=2))


@_tool(
    "rossum_list_audit_logs",
    "List audit log entries. Supports filtering by date range, user, action type, and object type. "
    "Returns up to max_results entries (default 100).",
    {
        "type": "object",
        "required": ["object_type"],
        "properties": {
            "object_type": {
                "type": "string",
                "description": "Object type to query (e.g. 'annotation', 'queue', 'hook', 'schema', 'workspace', 'user', 'organization').",
            },
            "timestamp_after": {
                "type": "string",
                "description": "ISO 8601 datetime. Only logs after this time (e.g. '2025-01-01T00:00:00Z').",
            },
            "timestamp_before": {
                "type": "string",
                "description": "ISO 8601 datetime. Only logs before this time.",
            },
            "user": {"type": "integer", "description": "Filter by user ID."},
            "action": {
                "type": "string",
                "description": "Filter by action (e.g. 'create', 'update', 'delete', 'export').",
            },
            "ordering": {
                "type": "string",
                "description": "Sort order. Default: '-id' (newest first). Use 'id' for oldest first.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum entries to return (default: 100, max: 1000).",
            },
        },
    },
)
def handle_list_audit_logs(request_id, arguments):
    base_url, _ = _ensure_connection(request_id)
    if not base_url:
        return

    max_results = min(arguments.get("max_results", 100), 1000)
    page_size = min(max_results, 100)
    params = [("page_size", page_size)]
    for key in ("timestamp_after", "timestamp_before", "user", "action", "object_type", "ordering"):
        if key in arguments:
            params.append((key, arguments[key]))

    url = f"{base_url}/api/v1/audit_logs?{urlencode(params)}"
    all_results = []

    while url and len(all_results) < max_results:
        page = _http_request(request_id, url)
        if page is None:
            return
        for entry in page.get("results", []):
            if len(all_results) >= max_results:
                break
            all_results.append(entry)
        next_url = page.get("pagination", {}).get("next")
        if not next_url:
            break
        if _validate_base_url(next_url) != _validate_base_url(url):
            break
        url = next_url

    tool_result(request_id, json.dumps({"total": len(all_results), "results": all_results}, indent=2))


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
