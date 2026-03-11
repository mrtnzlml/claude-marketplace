#!/usr/bin/env python3
"""MCP server for Rossum Data Storage API."""

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


# --- Connection state ---


def _get_base_url():
    return _cached_base_url or os.environ.get("ROSSUM_API_BASE", "https://elis.rossum.ai")


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


def _invalidate_token():
    """Clear token state. Preserves base URL so only a new token is needed."""
    global _cached_token, _token_validated
    _cached_token = None
    _token_validated = False


def _try_validate(request_id, base_url, token):
    """Validate a base_url + token pair. On success, cache and return the token."""
    global _cached_base_url, _cached_token, _token_validated

    validated = _validate_base_url(base_url)
    if not validated:
        return None

    if _probe_token(validated, token):
        _cached_base_url = validated
        _cached_token = token
        _token_validated = True
        return token

    return None


def ensure_token(request_id):
    """Return a validated token or send an error and return None."""
    if _token_validated and _cached_token:
        return _cached_token

    # 1. Try env var
    token = os.environ.get("ROSSUM_TOKEN", "") or None
    if token:
        base_url = _get_base_url()
        if _try_validate(request_id, base_url, token):
            return _cached_token

    # 2. Try prd2 credentials
    prd2_creds = _discover_prd2_credentials()
    if len(prd2_creds) == 1:
        org_name, base_url, token = prd2_creds[0]
        if _try_validate(request_id, base_url, token):
            _log(f"Auto-connected using prd2 credentials from org '{org_name}'")
            return _cached_token

    if len(prd2_creds) > 1:
        orgs = ", ".join(f"'{name}' ({url})" for name, url, _ in prd2_creds)
        tool_result(
            request_id,
            f"Found multiple prd2 organizations: {orgs}. "
            "Call data_storage_set_token with the 'org' parameter to select one "
            "(e.g. data_storage_set_token(org='sandbox-org')).",
            is_error=True,
        )
        return None

    # 3. No token found
    _invalidate_token()
    tool_result(
        request_id,
        "No API token found. Checked: ROSSUM_TOKEN env var, prd2 credentials.yaml files. "
        "Ask the user for their Rossum API token and call data_storage_set_token, "
        "or run from a prd2 project directory.",
        is_error=True,
    )
    return None


# --- Tools ---

TOOLS = {}

TOOLS["data_storage_set_token"] = {
    "name": "data_storage_set_token",
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


# --- Handlers ---


def api_call(request_id, path, body):
    token = ensure_token(request_id)
    if not token:
        return

    req = urllib.request.Request(
        f"{_get_base_url()}/svc/data-storage/api{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=130) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return tool_result(request_id, json.dumps(result, indent=2))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        if e.code == 401:
            _invalidate_token()
            return tool_result(
                request_id,
                f"Authentication failed (HTTP 401). Token may be expired. "
                f"Ask the user for a new token, then call data_storage_set_token.\n{error_body}",
                is_error=True,
            )
        return tool_result(request_id, f"HTTP {e.code}: {error_body}", is_error=True)
    except Exception as e:
        return tool_result(request_id, f"Error: {e}", is_error=True)


def handle_healthz(request_id, arguments):
    base_url = _get_base_url()
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

    if not _check_health(base_url):
        return tool_result(
            request_id,
            f"Data Storage API at {base_url} is not reachable. Check the base URL.",
            is_error=True,
        )

    if _probe_token(base_url, token):
        _cached_base_url = base_url
        _cached_token = token
        _token_validated = True
        label = f" (org '{org}')" if org else ""
        return tool_result(request_id, f"Connected to {base_url}{label}. Token is valid and saved for this session.")

    _cached_token = None
    _cached_base_url = None
    _token_validated = False
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


HANDLERS = {
    "data_storage_healthz": handle_healthz,
    "data_storage_set_token": handle_set_token,
    "data_storage_list_collections": handle_list_collections,
    "data_storage_aggregate": handle_aggregate,
    "data_storage_list_indexes": handle_list_indexes,
    "data_storage_list_search_indexes": handle_list_search_indexes,
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
                    "serverInfo": {"name": "rossum-data-storage", "version": "0.1.0"},
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
