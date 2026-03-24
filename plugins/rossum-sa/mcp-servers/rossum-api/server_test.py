"""Tests for the Rossum API MCP server."""

import io
import json
import sys
import urllib.error
from unittest import mock

import pytest

sys.path.insert(0, __import__("os").path.dirname(__file__))
import server


# --- Fixtures ---


@pytest.fixture(autouse=True)
def _reset_connection():
    """Reset global connection state between tests."""
    server._cached_base_url = None
    server._cached_token = None
    server._token_validated = False
    yield
    server._cached_base_url = None
    server._cached_token = None
    server._token_validated = False


def _set_connected(base_url="https://example.rossum.ai", token="test-token"):
    """Simulate an authenticated session."""
    server._cached_base_url = base_url
    server._cached_token = token
    server._token_validated = True


class MessageCapture:
    """Capture JSON-RPC messages written to stdout."""

    def __init__(self):
        self.messages = []

    def install(self, monkeypatch):
        monkeypatch.setattr(server, "write_message", self.messages.append)
        return self

    @property
    def last(self):
        return self.messages[-1]

    @property
    def last_result(self):
        return self.last.get("result", {})

    @property
    def last_text(self):
        content = self.last_result.get("content", [{}])
        return content[0].get("text", "") if content else ""

    @property
    def last_is_error(self):
        return self.last_result.get("isError", False)


@pytest.fixture
def capture(monkeypatch):
    return MessageCapture().install(monkeypatch)


def _mock_urlopen(response_body, status=200):
    """Create a mock for urllib.request.urlopen returning JSON."""
    resp = mock.MagicMock()
    resp.status = status
    resp.read.return_value = json.dumps(response_body).encode("utf-8")
    resp.__enter__ = mock.MagicMock(return_value=resp)
    resp.__exit__ = mock.MagicMock(return_value=False)
    return mock.patch("urllib.request.urlopen", return_value=resp)


# --- URL validation ---


class TestValidateBaseUrl:
    def test_valid_https(self):
        assert server._validate_base_url("https://elis.rossum.ai") == "https://elis.rossum.ai"

    def test_valid_https_with_path(self):
        assert server._validate_base_url("https://elis.rossum.ai/foo/bar") == "https://elis.rossum.ai"

    def test_rejects_http(self):
        assert server._validate_base_url("http://elis.rossum.ai") is None

    def test_rejects_no_scheme(self):
        assert server._validate_base_url("elis.rossum.ai") is None

    def test_rejects_empty(self):
        assert server._validate_base_url("") is None

    def test_custom_port(self):
        assert server._validate_base_url("https://localhost:8443") == "https://localhost:8443"

    def test_default_port_stripped(self):
        assert server._validate_base_url("https://elis.rossum.ai:443") == "https://elis.rossum.ai"


# --- Tool registration ---


class TestToolRegistration:
    def test_all_tools_registered(self):
        expected = {
            "rossum_set_token",
            "rossum_whoami",
            "data_storage_healthz",
            "data_storage_list_collections",
            "data_storage_aggregate",
            "data_storage_find",
            "data_storage_list_indexes",
            "data_storage_list_search_indexes",
            "data_storage_create_index",
            "data_storage_create_search_index",
            "data_storage_drop_index",
            "data_storage_drop_search_index",
            "rossum_list_users",
            "rossum_list_audit_logs",
            "rossum_get_hook_secret_keys",
            "rossum_list_annotations",
            "rossum_get_annotation",
            "rossum_get_annotation_content",
            "rossum_list_queues",
            "rossum_get_queue",
            "rossum_list_hooks",
            "rossum_get_hook",
            "rossum_create_hook",
            "rossum_delete_hook",
            "rossum_get_schema",
            "rossum_list_schemas",
            "rossum_list_workspaces",
            "rossum_get_workspace",
            "rossum_get_organization",
            "rossum_get_document",
            "rossum_get_inbox",
            "rossum_list_connectors",
            "rossum_get_connector",
        }
        assert set(server.TOOLS.keys()) == expected

    def test_all_tools_have_handlers(self):
        assert set(server.TOOLS.keys()) == set(server.HANDLERS.keys())

    def test_annotations(self):
        write_tools = {"data_storage_create_index", "data_storage_create_search_index", "rossum_create_hook"}
        destructive_tools = {"data_storage_drop_index", "data_storage_drop_search_index", "rossum_delete_hook"}
        for name, tool_def in server.TOOLS.items():
            ann = tool_def.get("annotations", {})
            if name in destructive_tools:
                assert ann.get("readOnlyHint") is False, f"{name} should be write"
                assert ann.get("destructiveHint") is True, f"{name} should be destructive"
            elif name in write_tools:
                assert ann.get("readOnlyHint") is False, f"{name} should be write"
                assert ann.get("destructiveHint") is False, f"{name} should not be destructive"
            else:
                assert ann.get("readOnlyHint") is True, f"{name} should be read-only"

    def test_tool_schemas_are_valid(self):
        for name, tool_def in server.TOOLS.items():
            schema = tool_def["inputSchema"]
            assert schema["type"] == "object", f"{name} schema must be object"
            assert "properties" in schema, f"{name} must have properties"


# --- Connection state ---


class TestConnectionState:
    def test_ensure_connection_when_disconnected(self, capture):
        base, token = server._ensure_connection("req-1")
        assert base is None
        assert token is None
        assert capture.last_is_error

    def test_ensure_connection_when_connected(self, capture):
        _set_connected()
        base, token = server._ensure_connection("req-1")
        assert base == "https://example.rossum.ai"
        assert token == "test-token"
        assert len(capture.messages) == 0

    def test_invalidate_connection(self):
        _set_connected()
        server._invalidate_connection()
        assert server._cached_base_url is None
        assert server._cached_token is None
        assert server._token_validated is False


# --- MCP protocol (integration) ---


class TestMCPProtocol:
    def test_initialize(self, capture):
        server.respond("req-1", {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "rossum-api", "version": "0.1.0"},
        })
        msg = capture.last
        assert msg["jsonrpc"] == "2.0"
        assert msg["result"]["serverInfo"]["name"] == "rossum-api"

    def test_tools_list_returns_all(self, capture):
        server.respond("req-1", {"tools": list(server.TOOLS.values())})
        tools = capture.last_result["tools"]
        assert len(tools) == len(server.TOOLS)

    def test_unknown_tool(self, capture):
        server.tool_result("req-1", "Unknown tool: fake_tool", is_error=True)
        assert capture.last_is_error
        assert "Unknown tool" in capture.last_text

    def test_respond_error(self, capture):
        server.respond_error("req-1", -32601, "Method not found")
        assert capture.last["error"]["code"] == -32601


# --- HTTP helpers ---


class TestHttpRequest:
    def test_returns_none_without_token(self):
        result = server._http_request("req-1", "https://example.com/api")
        assert result is None

    def test_successful_request(self, capture):
        _set_connected()
        with _mock_urlopen({"ok": True}):
            result = server._http_request("req-1", "https://example.rossum.ai/api/v1/test")
        assert result == {"ok": True}

    def test_401_invalidates_connection(self, capture):
        _set_connected()
        error = urllib.error.HTTPError(
            "https://example.com", 401, "Unauthorized", {}, io.BytesIO(b"expired")
        )
        with mock.patch("urllib.request.urlopen", side_effect=error):
            result = server._http_request("req-1", "https://example.rossum.ai/api")
        assert result is None
        assert server._token_validated is False
        assert capture.last_is_error
        assert "401" in capture.last_text

    def test_other_http_error(self, capture):
        _set_connected()
        error = urllib.error.HTTPError(
            "https://example.com", 500, "Server Error", {}, io.BytesIO(b"oops")
        )
        with mock.patch("urllib.request.urlopen", side_effect=error):
            result = server._http_request("req-1", "https://example.rossum.ai/api")
        assert result is None
        assert capture.last_is_error
        assert "500" in capture.last_text
        # Connection should still be valid
        assert server._token_validated is True

    def test_generic_exception(self, capture):
        _set_connected()
        with mock.patch("urllib.request.urlopen", side_effect=ConnectionError("timeout")):
            result = server._http_request("req-1", "https://example.rossum.ai/api")
        assert result is None
        assert capture.last_is_error


# --- Pagination ---


class TestPaginate:
    def _mock_pages(self, pages):
        """Mock _http_request to return successive pages."""
        call_count = [0]
        def fake_http(request_id, url, **kwargs):
            if call_count[0] >= len(pages):
                return None
            page = pages[call_count[0]]
            call_count[0] += 1
            return page
        return mock.patch.object(server, "_http_request", side_effect=fake_http)

    def test_single_page(self):
        _set_connected()
        page = {"results": [{"id": 1}, {"id": 2}], "pagination": {"next": None}}
        with self._mock_pages([page]):
            results = server._paginate("req-1", "https://example.rossum.ai/api/v1/items?page_size=100")
        assert results == [{"id": 1}, {"id": 2}]

    def test_multiple_pages(self):
        _set_connected()
        pages = [
            {"results": [{"id": 1}], "pagination": {"next": "https://example.rossum.ai/api/v1/items?page=2"}},
            {"results": [{"id": 2}], "pagination": {"next": None}},
        ]
        with self._mock_pages(pages):
            results = server._paginate("req-1", "https://example.rossum.ai/api/v1/items?page_size=100")
        assert results == [{"id": 1}, {"id": 2}]

    def test_max_results(self):
        _set_connected()
        page = {"results": [{"id": i} for i in range(10)], "pagination": {"next": "https://example.rossum.ai/next"}}
        with self._mock_pages([page]):
            results = server._paginate("req-1", "https://example.rossum.ai/api/v1/items", max_results=3)
        assert len(results) == 3

    def test_pick_fields(self):
        _set_connected()
        page = {"results": [{"id": 1, "name": "a", "secret": "x"}], "pagination": {"next": None}}
        with self._mock_pages([page]):
            results = server._paginate(
                "req-1", "https://example.rossum.ai/api/v1/items",
                pick_fields=("id", "name"),
            )
        assert results == [{"id": 1, "name": "a"}]

    def test_cross_origin_pagination_blocked(self):
        _set_connected()
        pages = [
            {"results": [{"id": 1}], "pagination": {"next": "https://evil.example.com/api/v1/items?page=2"}},
        ]
        with self._mock_pages(pages):
            results = server._paginate("req-1", "https://example.rossum.ai/api/v1/items")
        assert results == [{"id": 1}]

    def test_http_error_returns_none(self):
        _set_connected()
        with self._mock_pages([None]):
            results = server._paginate("req-1", "https://example.rossum.ai/api/v1/items")
        assert results is None


# --- Tool handlers ---


class TestSetToken:
    def test_missing_token(self, capture):
        server.handle_set_token("req-1", {"baseUrl": "https://elis.rossum.ai"})
        assert capture.last_is_error
        assert "Missing" in capture.last_text

    def test_invalid_url(self, capture):
        server.handle_set_token("req-1", {"token": "tok", "baseUrl": "http://bad.com"})
        assert capture.last_is_error
        assert "Invalid base URL" in capture.last_text

    def test_successful_connection(self, capture):
        with mock.patch.object(server, "_probe_token", return_value=(True, None)):
            server.handle_set_token("req-1", {"token": "tok", "baseUrl": "https://elis.rossum.ai"})
        assert not capture.last_is_error
        assert "Connected" in capture.last_text
        assert server._token_validated is True

    def test_probe_failure(self, capture):
        with mock.patch.object(server, "_probe_token", return_value=(False, "HTTP 403: Forbidden")):
            server.handle_set_token("req-1", {"token": "tok", "baseUrl": "https://elis.rossum.ai"})
        assert capture.last_is_error
        assert "Cannot connect" in capture.last_text
        assert server._token_validated is False


class TestWhoami:
    def test_whoami(self, capture):
        _set_connected()
        with _mock_urlopen({"id": 1, "email": "admin@example.com", "organization": "https://api/orgs/1"}):
            server.handle_whoami("req-1", {})
        data = json.loads(capture.last_text)
        assert data["email"] == "admin@example.com"

    def test_whoami_not_connected(self, capture):
        server.handle_whoami("req-1", {})
        assert capture.last_is_error


class TestHealthz:
    def test_healthy(self, capture):
        with mock.patch.object(server, "_check_health", return_value=True):
            server.handle_healthz("req-1", {"baseUrl": "https://elis.rossum.ai"})
        assert "healthy" in capture.last_text

    def test_unreachable(self, capture):
        with mock.patch.object(server, "_check_health", return_value=False):
            server.handle_healthz("req-1", {"baseUrl": "https://elis.rossum.ai"})
        assert capture.last_is_error
        assert "not reachable" in capture.last_text

    def test_invalid_url(self, capture):
        server.handle_healthz("req-1", {"baseUrl": "http://bad"})
        assert capture.last_is_error

    def test_uses_connected_env(self, capture):
        _set_connected("https://custom.rossum.app")
        with mock.patch.object(server, "_check_health", return_value=True) as m:
            server.handle_healthz("req-1", {})
        m.assert_called_once_with("https://custom.rossum.app")
        assert "connected environment" in capture.last_text

    def test_defaults_to_elis(self, capture):
        with mock.patch.object(server, "_check_health", return_value=True) as m:
            server.handle_healthz("req-1", {})
        m.assert_called_once_with("https://elis.rossum.ai")


class TestDataStorageTools:
    def test_list_collections_not_connected(self, capture):
        server.handle_list_collections("req-1", {})
        assert capture.last_is_error

    def test_list_collections(self, capture):
        _set_connected()
        with _mock_urlopen({"collections": ["a", "b"]}):
            server.handle_list_collections("req-1", {"nameOnly": True})
        assert "collections" in capture.last_text

    def test_aggregate(self, capture):
        _set_connected()
        with _mock_urlopen({"results": []}):
            server.handle_aggregate("req-1", {"collectionName": "test", "pipeline": [{"$limit": 1}]})
        assert not capture.last_is_error

    def test_list_indexes(self, capture):
        _set_connected()
        with _mock_urlopen({"indexes": ["_id_"]}):
            server.handle_list_indexes("req-1", {"collectionName": "test"})
        assert not capture.last_is_error

    def test_create_index(self, capture):
        _set_connected()
        with _mock_urlopen({"ok": True}) as m:
            server.handle_create_index("req-1", {
                "collectionName": "test", "indexName": "field_1", "keys": {"field": 1},
            })
        assert not capture.last_is_error
        body = json.loads(m.call_args[0][0].data)
        assert body["indexName"] == "field_1"

    def test_create_search_index(self, capture):
        _set_connected()
        with _mock_urlopen({"ok": True}) as m:
            server.handle_create_search_index("req-1", {
                "collectionName": "test",
                "mappings": {"dynamic": True},
                "indexName": "my_index",
            })
        assert not capture.last_is_error
        body = json.loads(m.call_args[0][0].data)
        assert body["indexName"] == "my_index"
        assert body["mappings"] == {"dynamic": True}

    def test_drop_index(self, capture):
        _set_connected()
        with _mock_urlopen({"ok": True}):
            server.handle_drop_index("req-1", {"collectionName": "test", "indexName": "field_1"})
        assert not capture.last_is_error

    def test_drop_search_index(self, capture):
        _set_connected()
        with _mock_urlopen({"ok": True}) as m:
            server.handle_drop_search_index("req-1", {"collectionName": "test", "indexName": "default"})
        assert not capture.last_is_error
        body = json.loads(m.call_args[0][0].data)
        assert body["indexName"] == "default"

    def test_find(self, capture):
        _set_connected()
        with _mock_urlopen({"results": [{"_id": "abc", "name": "test"}]}):
            server.handle_find("req-1", {
                "collectionName": "test",
                "query": {"name": "test"},
                "projection": {"name": 1},
                "sort": {"name": 1},
                "limit": 10,
            })
        data = json.loads(capture.last_text)
        assert data["results"][0]["name"] == "test"

    def test_find_defaults(self, capture):
        _set_connected()
        with _mock_urlopen({"results": []}) as m:
            server.handle_find("req-1", {"collectionName": "c"})
        body = json.loads(m.call_args[0][0].data)
        assert body["limit"] == 50
        assert body["query"] == {}

    def test_find_limit_capped(self, capture):
        _set_connected()
        with _mock_urlopen({"results": []}) as m:
            server.handle_find("req-1", {"collectionName": "c", "limit": 9999})
        body = json.loads(m.call_args[0][0].data)
        assert body["limit"] == 1000


class TestRossumApiTools:
    def _mock_list_response(self, results, next_url=None):
        return _mock_urlopen({"results": results, "pagination": {"next": next_url}})

    def test_list_users(self, capture):
        _set_connected()
        users = [{"id": 1, "email": "a@b.com", "first_name": "A", "last_name": "B", "is_active": True}]
        with self._mock_list_response(users):
            server.handle_list_users("req-1", {})
        data = json.loads(capture.last_text)
        assert data["total"] == 1
        assert data["results"][0]["email"] == "a@b.com"

    def test_list_users_filter(self, capture):
        _set_connected()
        with self._mock_list_response([]) as m:
            server.handle_list_users("req-1", {"is_active": True})
        call_url = m.call_args[0][0].full_url
        assert "is_active=true" in call_url

    def test_list_audit_logs(self, capture):
        _set_connected()
        entries = [{"id": 1, "action": "create"}]
        with self._mock_list_response(entries):
            server.handle_list_audit_logs("req-1", {"object_type": "document"})
        data = json.loads(capture.last_text)
        assert data["total"] == 1

    def test_list_audit_logs_max_results_capped(self, capture):
        _set_connected()
        with self._mock_list_response([{"id": i} for i in range(5)]):
            server.handle_list_audit_logs("req-1", {"object_type": "user", "max_results": 2})
        data = json.loads(capture.last_text)
        assert data["total"] == 2

    def test_get_hook_secret_keys(self, capture):
        _set_connected()
        with _mock_urlopen({"keys": ["SECRET_1"]}):
            server.handle_get_hook_secret_keys("req-1", {"hook_id": 42})
        assert "SECRET_1" in capture.last_text

    def test_list_annotations(self, capture):
        _set_connected()
        annotations = [{"id": 100, "queue": "https://api/queues/10", "status": "to_review",
                        "document": "https://api/documents/1", "modifier": None,
                        "modified_at": "2026-01-01T00:00:00Z", "confirmed_at": None,
                        "exported_at": None, "extra": "ignored"}]
        with self._mock_list_response(annotations):
            server.handle_list_annotations("req-1", {"queue": 10})
        data = json.loads(capture.last_text)
        assert data["total"] == 1
        assert data["results"][0]["status"] == "to_review"
        assert "extra" not in data["results"][0]

    def test_list_annotations_filter(self, capture):
        _set_connected()
        with self._mock_list_response([]) as m:
            server.handle_list_annotations("req-1", {"queue": 10, "status": "exported", "max_results": 5})
        call_url = m.call_args[0][0].full_url
        assert "queue=10" in call_url
        assert "status=exported" in call_url

    def test_get_annotation_content(self, capture):
        _set_connected()
        with _mock_urlopen({"content": [{"category": "section_header"}]}):
            server.handle_get_annotation_content("req-1", {"annotation_id": 99})
        assert "section_header" in capture.last_text

    def test_list_queues(self, capture):
        _set_connected()
        queues = [{"id": 10, "name": "Invoices", "workspace": "https://api/ws/1",
                   "schema": "https://api/schemas/5", "hooks": [], "status": "active",
                   "dedicated_engine": None, "extra_field": "ignored"}]
        with self._mock_list_response(queues):
            server.handle_list_queues("req-1", {})
        data = json.loads(capture.last_text)
        assert data["results"][0]["name"] == "Invoices"
        assert "extra_field" not in data["results"][0]

    def test_list_hooks(self, capture):
        _set_connected()
        hooks = [{"id": 5, "name": "Validator", "type": "function", "events": ["annotation_content"],
                  "queues": [], "active": True, "run_after": [], "token_owner": "https://api/users/1"}]
        with self._mock_list_response(hooks):
            server.handle_list_hooks("req-1", {})
        data = json.loads(capture.last_text)
        assert data["results"][0]["name"] == "Validator"

    def test_list_hooks_filter(self, capture):
        _set_connected()
        with self._mock_list_response([]) as m:
            server.handle_list_hooks("req-1", {"queue": 10, "active": False})
        call_url = m.call_args[0][0].full_url
        assert "queue=10" in call_url
        assert "active=false" in call_url

    def test_get_queue(self, capture):
        _set_connected()
        with _mock_urlopen({"id": 10, "name": "Invoices", "locale": "en_US"}) as m:
            server.handle_get_queue("req-1", {"queue_id": 10})
        data = json.loads(capture.last_text)
        assert data["name"] == "Invoices"
        assert "/queues/10" in m.call_args[0][0].full_url

    def test_get_hook(self, capture):
        _set_connected()
        hook_data = {"id": 5, "name": "Validator", "config": {"code": "def rossum_hook(...):"}}
        with _mock_urlopen(hook_data) as m:
            server.handle_get_hook("req-1", {"hook_id": 5})
        data = json.loads(capture.last_text)
        assert data["config"]["code"] == "def rossum_hook(...):"
        assert "/hooks/5" in m.call_args[0][0].full_url

    def test_create_hook_function(self, capture):
        _set_connected()
        created = {"id": 99, "name": "Test", "type": "function", "active": True}
        with _mock_urlopen(created) as m:
            server.handle_create_hook("req-1", {
                "name": "Test",
                "type": "function",
                "events": ["annotation_content.initialize"],
                "config": {"runtime": "python3.12", "code": "def rossum_hook_request_handler(payload): return payload"},
            })
        body = json.loads(m.call_args[0][0].data)
        assert body["name"] == "Test"
        assert body["type"] == "function"
        assert body["events"] == ["annotation_content.initialize"]
        assert body["active"] is True
        assert body["queues"] == []
        assert "/hooks" in m.call_args[0][0].full_url
        assert m.call_args[0][0].method == "POST"

    def test_create_hook_webhook_with_queues(self, capture):
        _set_connected()
        created = {"id": 100, "name": "Export WH", "type": "webhook"}
        with _mock_urlopen(created) as m:
            server.handle_create_hook("req-1", {
                "name": "Export WH",
                "type": "webhook",
                "events": ["annotation_content.export"],
                "config": {"url": "https://example.com/hook"},
                "queue_ids": [10, 20],
                "run_after": [5],
                "token_owner": 42,
                "active": False,
            })
        body = json.loads(m.call_args[0][0].data)
        assert body["type"] == "webhook"
        assert body["active"] is False
        assert body["queues"] == [
            "https://example.rossum.ai/api/v1/queues/10",
            "https://example.rossum.ai/api/v1/queues/20",
        ]
        assert body["run_after"] == ["https://example.rossum.ai/api/v1/hooks/5"]
        assert body["token_owner"] == "https://example.rossum.ai/api/v1/users/42"

    def test_create_hook_with_sideload(self, capture):
        _set_connected()
        with _mock_urlopen({"id": 101}) as m:
            server.handle_create_hook("req-1", {
                "name": "With sideload",
                "type": "function",
                "events": ["annotation_content.updated"],
                "config": {"runtime": "python3.12", "code": "pass"},
                "sideload": ["schemas"],
            })
        body = json.loads(m.call_args[0][0].data)
        assert body["sideload"] == ["schemas"]

    def test_delete_hook(self, capture):
        _set_connected()
        resp = mock.MagicMock()
        resp.status = 204
        resp.__enter__ = mock.MagicMock(return_value=resp)
        resp.__exit__ = mock.MagicMock(return_value=False)
        with mock.patch("urllib.request.urlopen", return_value=resp) as m:
            server.handle_delete_hook("req-1", {"hook_id": 42})
        assert not capture.last_is_error
        assert "Deleted" in capture.last_text
        assert "/hooks/42" in m.call_args[0][0].full_url
        assert m.call_args[0][0].method == "DELETE"

    def test_delete_hook_not_found(self, capture):
        _set_connected()
        error = urllib.error.HTTPError(
            "https://example.com", 404, "Not Found", {}, io.BytesIO(b'{"detail":"Not found."}')
        )
        with mock.patch("urllib.request.urlopen", side_effect=error):
            server.handle_delete_hook("req-1", {"hook_id": 999})
        assert capture.last_is_error
        assert "404" in capture.last_text

    def test_get_schema(self, capture):
        _set_connected()
        with _mock_urlopen({"id": 5, "content": [{"category": "section"}]}):
            server.handle_get_schema("req-1", {"schema_id": 5})
        data = json.loads(capture.last_text)
        assert data["id"] == 5

    def test_list_schemas(self, capture):
        _set_connected()
        schemas = [{"id": 5, "name": "Tax invoices", "queues": ["https://api/queues/10"], "extra": "ignored"}]
        with self._mock_list_response(schemas):
            server.handle_list_schemas("req-1", {})
        data = json.loads(capture.last_text)
        assert data["results"][0]["name"] == "Tax invoices"
        assert "extra" not in data["results"][0]

    def test_list_workspaces(self, capture):
        _set_connected()
        workspaces = [{"id": 1, "name": "Production", "organization": "https://api/orgs/1",
                       "queues": ["https://api/queues/10"], "autopilot": False, "extra": "ignored"}]
        with self._mock_list_response(workspaces):
            server.handle_list_workspaces("req-1", {})
        data = json.loads(capture.last_text)
        assert data["results"][0]["name"] == "Production"
        assert "extra" not in data["results"][0]

    def test_get_workspace(self, capture):
        _set_connected()
        with _mock_urlopen({"id": 1, "name": "Production", "queues": []}) as m:
            server.handle_get_workspace("req-1", {"workspace_id": 1})
        data = json.loads(capture.last_text)
        assert data["name"] == "Production"
        assert "/workspaces/1" in m.call_args[0][0].full_url

    def test_get_organization(self, capture):
        _set_connected()
        with _mock_urlopen({"id": 42, "name": "Acme Corp", "is_trial": False}) as m:
            server.handle_get_organization("req-1", {"organization_id": 42})
        data = json.loads(capture.last_text)
        assert data["name"] == "Acme Corp"
        assert "/organizations/42" in m.call_args[0][0].full_url

    def test_get_document(self, capture):
        _set_connected()
        with _mock_urlopen({"id": 99, "original_file_name": "invoice.pdf", "mime_type": "application/pdf"}) as m:
            server.handle_get_document("req-1", {"document_id": 99})
        data = json.loads(capture.last_text)
        assert data["original_file_name"] == "invoice.pdf"
        assert "/documents/99" in m.call_args[0][0].full_url

    def test_get_annotation(self, capture):
        _set_connected()
        ann_data = {"id": 100, "status": "exported", "messages": [], "metadata": {"export_id": "abc"}}
        with _mock_urlopen(ann_data) as m:
            server.handle_get_annotation("req-1", {"annotation_id": 100})
        data = json.loads(capture.last_text)
        assert data["status"] == "exported"
        assert data["metadata"]["export_id"] == "abc"
        assert "/annotations/100" in m.call_args[0][0].full_url

    def test_get_inbox(self, capture):
        _set_connected()
        inbox_data = {"id": 50, "email": "invoices-xyz@elis.rossum.ai", "queues": ["https://api/queues/10"]}
        with _mock_urlopen(inbox_data) as m:
            server.handle_get_inbox("req-1", {"inbox_id": 50})
        data = json.loads(capture.last_text)
        assert data["email"] == "invoices-xyz@elis.rossum.ai"
        assert "/inboxes/50" in m.call_args[0][0].full_url

    def test_list_connectors(self, capture):
        _set_connected()
        connectors = [{"id": 3, "name": "SAP Export", "queues": ["https://api/queues/10"],
                       "service_url": "https://example.com/export", "authorization_type": "token",
                       "asynchronous": False, "extra": "ignored"}]
        with self._mock_list_response(connectors):
            server.handle_list_connectors("req-1", {})
        data = json.loads(capture.last_text)
        assert data["results"][0]["name"] == "SAP Export"
        assert "extra" not in data["results"][0]

    def test_list_connectors_filter(self, capture):
        _set_connected()
        with self._mock_list_response([]) as m:
            server.handle_list_connectors("req-1", {"queue": 10})
        call_url = m.call_args[0][0].full_url
        assert "queue=10" in call_url

    def test_get_connector(self, capture):
        _set_connected()
        connector_data = {"id": 3, "name": "SAP Export", "service_url": "https://example.com/export"}
        with _mock_urlopen(connector_data) as m:
            server.handle_get_connector("req-1", {"connector_id": 3})
        data = json.loads(capture.last_text)
        assert data["name"] == "SAP Export"
        assert "/connectors/3" in m.call_args[0][0].full_url

    def test_tools_require_connection(self, capture):
        """All authenticated tools should fail gracefully when not connected."""
        authenticated_handlers = [
            (server.handle_whoami, {}),
            (server.handle_list_collections, {}),
            (server.handle_aggregate, {"collectionName": "c", "pipeline": []}),
            (server.handle_find, {"collectionName": "c"}),
            (server.handle_list_indexes, {"collectionName": "c"}),
            (server.handle_list_search_indexes, {"collectionName": "c"}),
            (server.handle_create_index, {"collectionName": "c", "indexName": "x", "keys": {"f": 1}}),
            (server.handle_create_search_index, {"collectionName": "c", "mappings": {}}),
            (server.handle_drop_index, {"collectionName": "c", "indexName": "x"}),
            (server.handle_drop_search_index, {"collectionName": "c", "indexName": "x"}),
            (server.handle_list_users, {}),
            (server.handle_list_audit_logs, {"object_type": "user"}),
            (server.handle_get_hook_secret_keys, {"hook_id": 1}),
            (server.handle_list_annotations, {"queue": 1}),
            (server.handle_get_annotation, {"annotation_id": 1}),
            (server.handle_get_annotation_content, {"annotation_id": 1}),
            (server.handle_list_queues, {}),
            (server.handle_get_queue, {"queue_id": 1}),
            (server.handle_list_hooks, {}),
            (server.handle_get_hook, {"hook_id": 1}),
            (server.handle_create_hook, {"name": "t", "type": "function", "events": [], "config": {}}),
            (server.handle_delete_hook, {"hook_id": 1}),
            (server.handle_get_schema, {"schema_id": 1}),
            (server.handle_list_schemas, {}),
            (server.handle_list_workspaces, {}),
            (server.handle_get_workspace, {"workspace_id": 1}),
            (server.handle_get_organization, {"organization_id": 1}),
            (server.handle_get_document, {"document_id": 1}),
            (server.handle_get_inbox, {"inbox_id": 1}),
            (server.handle_list_connectors, {}),
            (server.handle_get_connector, {"connector_id": 1}),
        ]
        for handler, args in authenticated_handlers:
            capture.messages.clear()
            handler(f"req-{handler.__name__}", args)
            assert capture.last_is_error, f"{handler.__name__} should fail when not connected"


# --- Main loop integration ---


class TestMainLoop:
    def _run_messages(self, messages, monkeypatch):
        """Feed JSON-RPC messages through the main loop and capture responses."""
        input_lines = "".join(json.dumps(m) + "\n" for m in messages)
        monkeypatch.setattr("sys.stdin", io.StringIO(input_lines))
        output = io.StringIO()
        monkeypatch.setattr("sys.stdout", output)
        server.main()
        return [json.loads(line) for line in output.getvalue().strip().split("\n") if line]

    def test_initialize_and_ping(self, monkeypatch):
        responses = self._run_messages([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "ping"},
        ], monkeypatch)
        assert responses[0]["result"]["serverInfo"]["name"] == "rossum-api"
        assert responses[1]["result"] == {}

    def test_tools_list(self, monkeypatch):
        responses = self._run_messages([
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        ], monkeypatch)
        tool_names = {t["name"] for t in responses[0]["result"]["tools"]}
        assert "rossum_set_token" in tool_names
        assert "data_storage_create_index" in tool_names
        assert len(tool_names) == len(server.TOOLS)

    def test_tools_list_annotations_survive_protocol(self, monkeypatch):
        """Write and destructive annotations must be present in the tools/list response."""
        responses = self._run_messages([
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        ], monkeypatch)
        tools_by_name = {t["name"]: t for t in responses[0]["result"]["tools"]}

        # Write (non-destructive)
        for name in ("data_storage_create_index", "data_storage_create_search_index", "rossum_create_hook"):
            ann = tools_by_name[name]["annotations"]
            assert ann["readOnlyHint"] is False, f"{name} readOnlyHint"
            assert ann["destructiveHint"] is False, f"{name} destructiveHint"

        # Destructive
        for name in ("data_storage_drop_index", "data_storage_drop_search_index", "rossum_delete_hook"):
            ann = tools_by_name[name]["annotations"]
            assert ann["readOnlyHint"] is False, f"{name} readOnlyHint"
            assert ann["destructiveHint"] is True, f"{name} destructiveHint"

        # Read-only (spot check)
        assert tools_by_name["rossum_whoami"]["annotations"]["readOnlyHint"] is True
        assert tools_by_name["data_storage_find"]["annotations"]["readOnlyHint"] is True

    def test_call_unknown_tool(self, monkeypatch):
        responses = self._run_messages([
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "nope"}},
        ], monkeypatch)
        assert responses[0]["result"]["isError"] is True

    def test_unknown_method(self, monkeypatch):
        responses = self._run_messages([
            {"jsonrpc": "2.0", "id": 1, "method": "nonexistent"},
        ], monkeypatch)
        assert responses[0]["error"]["code"] == -32601
