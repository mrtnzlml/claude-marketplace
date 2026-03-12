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


def _find_prd2_root():
    """Walk up from CWD to find the prd2 project root (contains prd_config.yaml)."""
    current = os.getcwd()
    while True:
        if os.path.isfile(os.path.join(current, "prd_config.yaml")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def _discover_prd2_credentials():
    """Discover credentials from prd2 project structure.

    Returns list of (org_name, base_url, token) tuples.
    """
    project_root = _find_prd2_root()
    if not project_root:
        return []

    config = _parse_prd_config(os.path.join(project_root, "prd_config.yaml"))

    results = []
    for org_name, api_base in config.items():
        creds_path = os.path.join(project_root, org_name, "credentials.yaml")
        token = _parse_credentials(creds_path)
        if not token:
            continue
        base_url = _validate_base_url(api_base)
        if base_url:
            results.append((org_name, base_url, token))

    return results


def _persist_token_to_prd2(base_url, token):
    """Write token to the prd2 org whose api_base matches base_url.

    Silently does nothing if there is no prd2 project or no matching org.
    """
    project_root = _find_prd2_root()
    if not project_root:
        return

    config = _parse_prd_config(os.path.join(project_root, "prd_config.yaml"))
    for org_name, api_base in config.items():
        if _validate_base_url(api_base) != base_url:
            continue

        creds_path = os.path.join(project_root, org_name, "credentials.yaml")

        # Update existing token line or append
        lines = []
        found = False
        try:
            with open(creds_path) as f:
                lines = f.readlines()
        except OSError:
            pass

        new_lines = []
        for line in lines:
            if line.strip().startswith("token:"):
                new_lines.append(f"token: {token}\n")
                found = True
            else:
                new_lines.append(line)

        if not found:
            new_lines.append(f"token: {token}\n")

        try:
            with open(creds_path, "w") as f:
                f.writelines(new_lines)
            _log(f"Token saved to {creds_path}")
        except OSError as e:
            _log(f"Failed to write token to {creds_path}: {e}")
        return


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


def _sort_prd2_preference(creds):
    """Sort prd2 credentials: sandbox/dev/test first, production last."""
    def _rank(entry):
        name = entry[0].lower()
        if any(kw in name for kw in ("sandbox", "dev", "test", "staging")):
            return 0
        if any(kw in name for kw in ("prod", "production")):
            return 2
        return 1
    return sorted(creds, key=_rank)


def _ensure_connection(request_id):
    """Resolve base_url + token together. Returns (base_url, token) or (None, None) with error sent.

    Resolution order:
    1. Cached (already validated)
    2. Environment variables: ROSSUM_TOKEN + ROSSUM_API_BASE
    3. prd2 project credentials (prefers sandbox/dev over production)
    4. Error — asks user to call rossum_set_token
    """
    global _cached_base_url, _cached_token, _token_validated

    if _token_validated and _cached_base_url and _cached_token:
        return (_cached_base_url, _cached_token)

    # 1. Environment variables (both from the same source)
    env_token = os.environ.get("ROSSUM_TOKEN", "") or None
    if env_token:
        env_base = os.environ.get("ROSSUM_API_BASE", "") or None
        base_url = _validate_base_url(env_base) if env_base else "https://elis.rossum.ai"
        if base_url and _probe_token(base_url, env_token):
            _cached_base_url = base_url
            _cached_token = env_token
            _token_validated = True
            return (base_url, env_token)

    # 2. prd2 project credentials (prefer sandbox/dev over production)
    prd2_creds = _discover_prd2_credentials()
    if prd2_creds:
        for org_name, base_url, token in _sort_prd2_preference(prd2_creds):
            if _probe_token(base_url, token):
                _cached_base_url = base_url
                _cached_token = token
                _token_validated = True
                _log(f"Auto-connected to '{org_name}' ({base_url})")
                return (base_url, token)

    # 3. No valid credentials
    _invalidate_connection()
    tool_result(
        request_id,
        "No valid API credentials found. "
        "Checked: ROSSUM_TOKEN + ROSSUM_API_BASE env vars, prd2 project credentials. "
        "Ask the user for their Rossum API token and call rossum_set_token, "
        "or run from a prd2 project directory.",
        is_error=True,
    )
    return (None, None)


# --- Tools ---

TOOLS = {}

TOOLS["rossum_set_token"] = {
    "name": "rossum_set_token",
    "description": (
        "Sets the Rossum API connection for this session. Either provide a token directly, "
        "or specify a prd2 organization name to read credentials from the project's "
        "credentials.yaml and prd_config.yaml automatically."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "org": {
                "type": "string",
                "description": (
                    "Name of a prd2 organization directory (e.g. 'sandbox-org'). "
                    "Reads the token from <org>/credentials.yaml and the base URL "
                    "from prd_config.yaml. Cannot be combined with 'token'."
                ),
            },
            "baseUrl": {
                "type": "string",
                "description": (
                    "Base URL of the Rossum environment "
                    "(e.g. https://elis.rossum.ai, https://customer-dev.rossum.app). "
                    "Defaults to ROSSUM_API_BASE env var or https://elis.rossum.ai. "
                    "Ignored when 'org' is provided."
                ),
            },
            "token": {
                "type": "string",
                "description": "The Rossum API Bearer token. Required unless 'org' is provided.",
            },
        },
    },
}

TOOLS["data_storage_healthz"] = {
    "name": "data_storage_healthz",
    "description": "Checks if the Rossum Data Storage API is reachable. Does not require authentication.",
    "inputSchema": {
        "type": "object",
        "properties": {},
    },
}

TOOLS["data_storage_list_collections"] = {
    "name": "data_storage_list_collections",
    "description": "Lists available collections in Rossum Data Storage.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "filter": {
                "type": "object",
                "description": "Optional query filter for collections.",
            },
            "nameOnly": {
                "type": "boolean",
                "description": "Return only collection names (default: true).",
            },
        },
    },
}

TOOLS["data_storage_aggregate"] = {
    "name": "data_storage_aggregate",
    "description": (
        "Performs a MongoDB aggregation pipeline on a Rossum Data Storage collection. "
        "Runtime is limited to 120 seconds."
    ),
    "inputSchema": {
        "type": "object",
        "required": ["pipeline"],
        "properties": {
            "collectionName": {
                "type": "string",
                "description": "The name of the collection to aggregate on.",
            },
            "pipeline": {
                "type": "array",
                "items": {"type": "object"},
                "description": "The MongoDB aggregation pipeline stages.",
            },
            "collation": {
                "type": "object",
                "description": "Collation settings for the aggregation.",
            },
            "let": {
                "type": "object",
                "description": "Variables accessible in the pipeline.",
            },
            "options": {
                "type": "object",
                "description": "Additional aggregation options.",
            },
        },
    },
}

_INDEX_LIST_SCHEMA = {
    "type": "object",
    "required": ["collectionName"],
    "properties": {
        "collectionName": {
            "type": "string",
            "description": "The name of the collection.",
        },
        "nameOnly": {
            "type": "boolean",
            "description": "Return only index names (default: true).",
        },
    },
}

TOOLS["data_storage_list_indexes"] = {
    "name": "data_storage_list_indexes",
    "description": "Lists all indexes of a Rossum Data Storage collection.",
    "inputSchema": _INDEX_LIST_SCHEMA,
}

TOOLS["data_storage_list_search_indexes"] = {
    "name": "data_storage_list_search_indexes",
    "description": "Lists all Atlas Search indexes of a Rossum Data Storage collection.",
    "inputSchema": _INDEX_LIST_SCHEMA,
}

TOOLS["rossum_list_users"] = {
    "name": "rossum_list_users",
    "description": "Lists all users in the Rossum organization. Auto-paginates to return every user.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "is_active": {
                "type": "boolean",
                "description": "Filter by active status. Omit to return all users.",
            },
        },
    },
}


# --- Handlers ---


def _http_request(request_id, url, *, method="GET", body=None):
    """Make an authenticated HTTP request. Returns parsed JSON or None (error sent).

    Connection must be ensured before calling (for correct URL construction).
    Uses the cached token for authentication.
    """
    if not (_token_validated and _cached_token):
        _, token = _ensure_connection(request_id)
        if not token:
            return None
    token = _cached_token

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


def api_call(request_id, path, body):
    base_url, _ = _ensure_connection(request_id)
    if not base_url:
        return
    url = f"{base_url}/svc/data-storage/api{path}"
    result = _http_request(request_id, url, method="POST", body=body)
    if result is not None:
        tool_result(request_id, json.dumps(result, indent=2))


def handle_healthz(request_id, arguments):
    base_url = _cached_base_url or os.environ.get("ROSSUM_API_BASE", "https://elis.rossum.ai")
    validated = _validate_base_url(base_url)
    if not validated:
        return tool_result(request_id, f"Invalid base URL: {base_url}. Must be an HTTPS URL.", is_error=True)

    if _check_health(validated):
        return tool_result(request_id, f"Data Storage API at {validated} is healthy.")

    return tool_result(request_id, f"Data Storage API at {validated} is not reachable.", is_error=True)


def handle_set_token(request_id, arguments):
    global _cached_base_url, _cached_token, _token_validated

    org = arguments.get("org", "")
    token = arguments.get("token", "")

    # Resolve credentials from prd2 org
    if org:
        prd2_creds = _discover_prd2_credentials()
        match = [(name, url, tok) for name, url, tok in prd2_creds if name == org]
        if not match:
            available = ", ".join(f"'{name}'" for name, _, _ in prd2_creds) if prd2_creds else "none"
            return tool_result(
                request_id,
                f"Organization '{org}' not found in prd2 project. Available: {available}.",
                is_error=True,
            )
        _, base_url, token = match[0]
    else:
        if not token:
            return tool_result(
                request_id,
                "Provide either 'token' or 'org'. "
                "Use 'org' to read credentials from a prd2 project, or 'token' for manual auth.",
                is_error=True,
            )
        raw_url = arguments.get("baseUrl") or os.environ.get("ROSSUM_API_BASE", "https://elis.rossum.ai")
        base_url = _validate_base_url(raw_url)
        if not base_url:
            return tool_result(
                request_id,
                f"Invalid base URL: {raw_url}. Must be an HTTPS URL (e.g. https://elis.rossum.ai).",
                is_error=True,
            )

    if _probe_token(base_url, token):
        _cached_base_url = base_url
        _cached_token = token
        _token_validated = True
        # Persist manually provided tokens back to prd2 credentials
        if not org:
            _persist_token_to_prd2(base_url, token)
        label = f" (org '{org}')" if org else ""
        return tool_result(request_id, f"Connected to {base_url}{label}. Token is valid and saved for this session.")

    _invalidate_connection()
    return tool_result(
        request_id,
        f"Token is invalid or expired for {base_url}. Check the token and try again.",
        is_error=True,
    )


def handle_list_collections(request_id, arguments):
    body = {}
    if "filter" in arguments:
        body["filter"] = arguments["filter"]
    if "nameOnly" in arguments:
        body["nameOnly"] = arguments["nameOnly"]
    return api_call(request_id, "/v1/collections/list", body)


def handle_aggregate(request_id, arguments):
    body = {"pipeline": arguments.get("pipeline", [])}
    for key in ("collectionName", "collation", "let", "options"):
        if key in arguments:
            body[key] = arguments[key]
    return api_call(request_id, "/v1/data/aggregate", body)


def _handle_index_list(request_id, arguments, path):
    body = {"collectionName": arguments.get("collectionName", "")}
    if "nameOnly" in arguments:
        body["nameOnly"] = arguments["nameOnly"]
    return api_call(request_id, path, body)


def handle_list_indexes(request_id, arguments):
    return _handle_index_list(request_id, arguments, "/v1/indexes/list")


def handle_list_search_indexes(request_id, arguments):
    return _handle_index_list(request_id, arguments, "/v1/search_indexes/list")


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
        _USER_FIELDS = ("id", "email", "first_name", "last_name", "is_active")
        for user in page.get("results", []):
            all_results.append({k: user[k] for k in _USER_FIELDS if k in user})
        next_url = page.get("pagination", {}).get("next")
        # Follow relative or absolute next URLs; stop if missing
        if not next_url:
            break
        # The API returns absolute URLs — validate to prevent SSRF via pagination
        if _validate_base_url(next_url) != _validate_base_url(url):
            break
        url = next_url

    tool_result(request_id, json.dumps({"total": len(all_results), "results": all_results}, indent=2))


HANDLERS = {
    "data_storage_healthz": handle_healthz,
    "rossum_set_token": handle_set_token,
    "data_storage_list_collections": handle_list_collections,
    "data_storage_aggregate": handle_aggregate,
    "data_storage_list_indexes": handle_list_indexes,
    "data_storage_list_search_indexes": handle_list_search_indexes,
    "rossum_list_users": handle_list_users,
}


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
