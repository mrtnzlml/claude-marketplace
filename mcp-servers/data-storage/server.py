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


def ensure_token(request_id):
    """Return a validated token or send an error and return None."""
    global _cached_base_url, _cached_token, _token_validated

    if _token_validated and _cached_token:
        return _cached_token

    token = _cached_token or os.environ.get("ROSSUM_TOKEN", "") or None

    if not token:
        tool_result(
            request_id,
            "No API token configured. Ask the user for their Rossum API token "
            "and the base URL of their Rossum environment (e.g. https://elis.rossum.ai), "
            "then call data_storage_set_token.",
            is_error=True,
        )
        return None

    base_url = _get_base_url()
    validated = _validate_base_url(base_url)
    if not validated:
        tool_result(
            request_id,
            f"Invalid base URL: {base_url}. Must be an HTTPS URL. "
            "Call data_storage_set_token with a valid baseUrl.",
            is_error=True,
        )
        return None

    if _probe_token(validated, token):
        _cached_base_url = validated
        _cached_token = token
        _token_validated = True
        return token

    _invalidate_token()
    tool_result(
        request_id,
        "The API token is invalid or expired. Ask the user for a valid Rossum API token "
        "and the base URL of their environment, then call data_storage_set_token.",
        is_error=True,
    )
    return None


# --- Tools ---

TOOLS = {}

TOOLS["data_storage_set_token"] = {
    "name": "data_storage_set_token",
    "description": (
        "Sets the Rossum API base URL and token for this session. "
        "Must be called before other data_storage tools if ROSSUM_TOKEN env var is not set. "
        "Different Rossum environments use different base URLs (e.g. "
        "https://elis.rossum.ai, https://customer-dev.rossum.app)."
    ),
    "inputSchema": {
        "type": "object",
        "required": ["token"],
        "properties": {
            "baseUrl": {
                "type": "string",
                "description": (
                    "Base URL of the Rossum environment "
                    "(e.g. https://elis.rossum.ai, https://customer-dev.rossum.app). "
                    "Defaults to ROSSUM_API_BASE env var or https://elis.rossum.ai."
                ),
            },
            "token": {
                "type": "string",
                "description": "The Rossum API Bearer token.",
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

    token = arguments.get("token", "")
    if not token:
        return tool_result(request_id, "Token cannot be empty.", is_error=True)

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
        return tool_result(request_id, f"Connected to {base_url}. Token is valid and saved for this session.")

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
