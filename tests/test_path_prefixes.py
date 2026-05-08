"""
Integration tests for API and WebUI path support.

The API path is set as the servers URL in the OpenAPI spec (via FastAPI's
servers parameter). Routes always stay at their natural paths. The servers
entry tells Swagger UI what prefix to use when making API calls through
a reverse proxy.
"""

import os
import sys
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

import pytest


@pytest.fixture
def mock_args_api_path():
    """Create mock args with API path."""
    from lightrag.api.config import parse_args

    original_argv = sys.argv.copy()
    try:
        sys.argv = ['lightrag-server', '--api-path', '/test-api']
        args = parse_args()
        yield args
    finally:
        sys.argv = original_argv


@pytest.fixture
def mock_args_no_prefix():
    """Create mock args without API path."""
    from lightrag.api.config import parse_args

    original_argv = sys.argv.copy()
    try:
        sys.argv = ['lightrag-server']
        args = parse_args()
        yield args
    finally:
        sys.argv = original_argv


class TestOpenAPIServersConfig:
    """Test that servers is set correctly on the FastAPI app."""

    def test_servers_set_when_path_provided(self, mock_args_api_path):
        """Test app.servers reflects api_path."""
        with patch('lightrag.api.lightrag_server.LightRAG') as mock_rag:
            mock_rag.return_value = MagicMock()
            from lightrag.api.lightrag_server import create_app
            app = create_app(mock_args_api_path)
            assert app.servers == [{"url": "/test-api"}]

    def test_servers_empty_when_no_path(self, mock_args_no_prefix):
        """Test app.servers is empty when no path is configured."""
        with patch('lightrag.api.lightrag_server.LightRAG') as mock_rag:
            mock_rag.return_value = MagicMock()
            from lightrag.api.lightrag_server import create_app
            app = create_app(mock_args_no_prefix)
            assert app.servers == []


class TestOpenAPISpecIntegration:
    """Test that OpenAPI spec uses servers for URL."""

    def test_openapi_spec_has_servers_url_with_path(self, mock_args_api_path):
        """Test OpenAPI spec servers URL includes the api_path."""
        with patch('lightrag.api.lightrag_server.LightRAG') as mock_rag:
            mock_rag.return_value = MagicMock()
            from lightrag.api.lightrag_server import create_app
            app = create_app(mock_args_api_path)
            client = TestClient(app)

            response = client.get('/openapi.json')
            assert response.status_code == 200
            spec = response.json()

            servers = spec.get("servers", [])
            assert len(servers) > 0, "OpenAPI spec should have servers entry when api_path is set"
            assert "/test-api" in servers[0].get("url", ""), (
                f"Expected servers URL to contain /test-api, got: {servers[0].get('url')}"
            )

    def test_openapi_spec_no_servers_without_path(self, mock_args_no_prefix):
        """Test OpenAPI spec has no servers entry when no api_path."""
        with patch('lightrag.api.lightrag_server.LightRAG') as mock_rag:
            mock_rag.return_value = MagicMock()
            from lightrag.api.lightrag_server import create_app
            app = create_app(mock_args_no_prefix)
            client = TestClient(app)

            response = client.get('/openapi.json')
            assert response.status_code == 200
            spec = response.json()

            servers = spec.get("servers", [])
            assert len(servers) == 0

    def test_openapi_spec_paths_at_natural_paths(self, mock_args_api_path):
        """Test OpenAPI spec paths are at natural paths (not prefixed)."""
        with patch('lightrag.api.lightrag_server.LightRAG') as mock_rag:
            mock_rag.return_value = MagicMock()
            from lightrag.api.lightrag_server import create_app
            app = create_app(mock_args_api_path)
            client = TestClient(app)

            response = client.get('/openapi.json')
            assert response.status_code == 200
            spec = response.json()
            paths = spec.get("paths", {})

            for path in paths:
                if path == "/":
                    continue
                assert not path.startswith("/test-api/"), (
                    f"Path {path} should not be prefixed with /test-api/"
                )


class TestRoutesAtNaturalPaths:
    """Test that routes stay at their natural paths."""

    def test_routes_accessible_at_natural_path(self, mock_args_api_path):
        """With servers config, routes work at natural paths only."""
        with patch('lightrag.api.lightrag_server.LightRAG') as mock_rag:
            mock_rag.return_value = MagicMock()
            from lightrag.api.lightrag_server import create_app
            app = create_app(mock_args_api_path)
            client = TestClient(app)

            response = client.get('/docs')
            assert response.status_code == 200

            response = client.get('/openapi.json')
            assert response.status_code == 200

    def test_prefixed_paths_not_accessible_directly(self, mock_args_api_path):
        """Without root_path, prefixed paths are not routed."""
        with patch('lightrag.api.lightrag_server.LightRAG') as mock_rag:
            mock_rag.return_value = MagicMock()
            from lightrag.api.lightrag_server import create_app
            app = create_app(mock_args_api_path)
            client = TestClient(app)

            response = client.get('/test-api/docs')
            assert response.status_code == 404

            response = client.get('/test-api/openapi.json')
            assert response.status_code == 404

    def test_routes_at_root_no_prefix(self, mock_args_no_prefix):
        """Test routes are at root when no path is set (default)."""
        with patch('lightrag.api.lightrag_server.LightRAG') as mock_rag:
            mock_rag.return_value = MagicMock()
            from lightrag.api.lightrag_server import create_app
            app = create_app(mock_args_no_prefix)
            client = TestClient(app)

            response = client.get('/docs')
            assert response.status_code == 200

            response = client.get('/openapi.json')
            assert response.status_code == 200


class TestWebUIPrefixIntegration:
    """Test that WebUI is served at the correct path."""

    def test_webui_at_custom_path(self, mock_args_api_path):
        """Test WebUI assets are at the configured webui path."""
        with patch('lightrag.api.lightrag_server.LightRAG') as mock_rag:
            mock_rag.return_value = MagicMock()
            from lightrag.api.lightrag_server import create_app
            from lightrag.api.config import parse_args

            original_argv = sys.argv.copy()
            try:
                sys.argv = ['lightrag-server', '--api-path', '/test-api', '--webui-path', '/test-webui']
                args = parse_args()
                app = create_app(args)
                client = TestClient(app)

                response = client.get('/test-webui/')
                assert response.status_code in [200, 307]
            finally:
                sys.argv = original_argv

    def test_webui_without_api_path(self):
        """Test WebUI works with custom path when no API path is set."""
        with patch('lightrag.api.lightrag_server.LightRAG') as mock_rag:
            mock_rag.return_value = MagicMock()
            from lightrag.api.lightrag_server import create_app
            from lightrag.api.config import parse_args

            original_argv = sys.argv.copy()
            try:
                sys.argv = ['lightrag-server', '--webui-path', '/test-webui']
                args = parse_args()
                app = create_app(args)
                client = TestClient(app)

                response = client.get('/test-webui/')
                assert response.status_code in [200, 307]
            finally:
                sys.argv = original_argv

    def test_webui_not_at_default_path_with_custom(self, mock_args_api_path):
        """Test /webui returns 404 when custom path is set."""
        with patch('lightrag.api.lightrag_server.LightRAG') as mock_rag:
            mock_rag.return_value = MagicMock()
            from lightrag.api.lightrag_server import create_app
            from lightrag.api.config import parse_args

            original_argv = sys.argv.copy()
            try:
                sys.argv = ['lightrag-server', '--api-path', '/test-api', '--webui-path', '/test-webui']
                args = parse_args()
                app = create_app(args)
                client = TestClient(app)

                response = client.get('/webui/')
                assert response.status_code == 404
            finally:
                sys.argv = original_argv


class TestEnvironmentVariables:
    """Test that environment variables are read correctly."""

    def test_env_api_path(self):
        """Test LIGHTRAG_API_PATH environment variable."""
        from lightrag.api.config import get_env_value

        os.environ['LIGHTRAG_API_PATH'] = 'unit-test-back/api'
        try:
            value = get_env_value("LIGHTRAG_API_PATH", "")
            assert value == 'unit-test-back/api'
        finally:
            del os.environ['LIGHTRAG_API_PATH']

    def test_env_webui_path(self):
        """Test LIGHTRAG_WEBUI_PATH environment variable."""
        from lightrag.api.config import get_env_value

        os.environ['LIGHTRAG_WEBUI_PATH'] = 'unit-test-front/webui'
        try:
            value = get_env_value("LIGHTRAG_WEBUI_PATH", "/webui")
            assert value == 'unit-test-front/webui'
        finally:
            del os.environ['LIGHTRAG_WEBUI_PATH']
