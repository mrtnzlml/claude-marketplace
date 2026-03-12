#!/usr/bin/env python3
"""MCP server for Rossum APIs (read-only)."""

import json
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

_cached_base_url = None
_cached_token = None
_token_validated = False
_cached_prd2_root = None


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


# --- prd2 credential discovery ---


def _parse_credentials(path):
    """Parse a prd2 credentials.yaml file. Returns token string or None."""
    try:
        with open(path) as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("token:"):
                    return stripped.split(":", 1)[1].strip().strip("'\"")
    except OSError:
        pass
    return None


def _parse_prd_config(path):
    """Parse prd_config.yaml to extract org directories and their api_base URLs.

    Returns dict: {org_name: api_base_url}
    """
    result = {}
    try:
        with open(path) as f:
            lines = f.readlines()
    except OSError:
        return result

    in_directories = False
    current_org = None

    for line in lines:
        stripped = line.rstrip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        if indent == 0 and stripped.startswith("directories"):
            in_directories = True
            current_org = None
            continue

        if indent == 0:
            in_directories = False
            continue

        if not in_directories:
            continue

        if indent == 2 and stripped.endswith(":"):
            current_org = stripped.rstrip(":").strip()
            continue

        if indent == 4 and current_org and stripped.startswith("api_base:"):
            api_base = stripped.split(":", 1)[1].strip().strip("'\"")
            result[current_org] = api_base

    return result


def _find_prd2_root(start=None):
    """Walk up from start (or CWD) to find the prd2 project root (contains prd_config.yaml).

    Caches the result so subsequent calls return immediately.
    """
    global _cached_prd2_root
    if _cached_prd2_root:
        return _cached_prd2_root

    current = start or os.getcwd()
    while True:
        if os.path.isfile(os.path.join(current, "prd_config.yaml")):
            _cached_prd2_root = current
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def _load_prd2_config(start=None):
    """Find prd2 project root and parse its config.

    Returns (project_root, config_dict) or (None, {}).
    """
    project_root = _find_prd2_root(start)
    if not project_root:
        return (None, {})
    config = _parse_prd_config(os.path.join(project_root, "prd_config.yaml"))
    return (project_root, config)


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
        "Not connected to Rossum. Call rossum_set_token to establish a connection. "
        "Pass cwd='<user-project-path>' to discover available prd2 environments, "
        "or token='<token>' and baseUrl='<url>' for manual connection.",
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
    "Establish a Rossum API connection for this session. Three modes: "
    "(1) pass cwd to discover prd2 environments, "
    "(2) pass org (+ optional cwd) to connect via prd2, "
    "(3) pass token + baseUrl for manual connection. "
    "Always confirm the chosen environment with the user before connecting.",
    {
        "type": "object",
        "properties": {
            "cwd": {
                "type": "string",
                "description": (
                    "Path to the user's working directory (or any path inside a prd2 project). "
                    "Used to locate prd_config.yaml. Always pass the user's project directory."
                ),
            },
            "org": {
                "type": "string",
                "description": (
                    "Name of a prd2 organization directory (e.g. 'sandbox-org'). "
                    "Reads the base URL from prd_config.yaml and token from credentials.yaml. "
                    "If 'token' is also provided, uses it instead of credentials.yaml."
                ),
            },
            "baseUrl": {
                "type": "string",
                "description": (
                    "Base URL of the Rossum environment "
                    "(e.g. https://elis.rossum.ai, https://customer-dev.rossum.app). "
                    "Defaults to https://elis.rossum.ai. Ignored when 'org' is provided."
                ),
            },
            "token": {
                "type": "string",
                "description": "Rossum API Bearer token. If omitted with 'org', reads from credentials.yaml.",
            },
        },
    },
)
def handle_set_token(request_id, arguments):
    global _cached_base_url, _cached_token, _token_validated

    cwd = arguments.get("cwd")
    org = arguments.get("org")
    token = arguments.get("token")
    base_url_arg = arguments.get("baseUrl")

    # --- Phase 1: Discovery (cwd without org) → list environments for user selection ---

    if cwd and not org and not token:
        project_root, config = _load_prd2_config(cwd)
        if not project_root:
            return tool_result(request_id, f"No prd_config.yaml found at or above {cwd}.", is_error=True)
        if not config:
            return tool_result(request_id, "prd_config.yaml found but contains no organizations.", is_error=True)
        orgs = ", ".join(f"'{name}' ({url})" for name, url in config.items())
        return tool_result(
            request_id,
            f"Found prd2 project at {project_root} with environments: {orgs}. "
            "Ask the user which environment to connect to, then call "
            f"rossum_set_token(cwd='{cwd}', org='<chosen-org>').",
        )

    # --- Phase 2: Resolve base_url + token ---

    if org:
        # Org-based: resolve from prd2 project
        project_root, config = _load_prd2_config(cwd)
        if not project_root or not config:
            return tool_result(request_id, "No prd2 project found.", is_error=True)
        if org not in config:
            available = ", ".join(f"'{n}'" for n in config)
            return tool_result(
                request_id,
                f"Organization '{org}' not found. Available: {available}.",
                is_error=True,
            )
        base_url = _validate_base_url(config[org])
        if not base_url:
            return tool_result(request_id, f"Invalid URL for '{org}': {config[org]}.", is_error=True)
        if not token:
            token = _parse_credentials(os.path.join(project_root, org, "credentials.yaml"))
            if not token:
                return tool_result(
                    request_id,
                    f"No token in {org}/credentials.yaml. "
                    f"Ask the user for a Rossum API token, then call "
                    f"rossum_set_token(cwd='{cwd}', org='{org}', token='<token>').",
                    is_error=True,
                )
    elif token:
        # Manual: token provided directly
        raw_url = base_url_arg or "https://elis.rossum.ai"
        base_url = _validate_base_url(raw_url)
        if not base_url:
            return tool_result(request_id, f"Invalid URL: {raw_url}. Must be HTTPS.", is_error=True)
    else:
        return tool_result(
            request_id,
            "Pass 'cwd' to discover prd2 environments, "
            "'org' to connect to a known environment, "
            "or 'token' + 'baseUrl' for manual connection.",
            is_error=True,
        )

    # --- Phase 3: Validate and cache ---

    if not _probe_token(base_url, token):
        _invalidate_connection()
        source = f"'{org}' ({base_url})" if org else base_url
        return tool_result(
            request_id,
            f"Token is invalid or expired for {source}. "
            "Ask the user for a fresh token and retry.",
            is_error=True,
        )

    _cached_base_url = base_url
    _cached_token = token
    _token_validated = True
    label = f" (org '{org}')" if org else ""
    return tool_result(request_id, f"Connected to {base_url}{label}. Token validated for this session.")


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
