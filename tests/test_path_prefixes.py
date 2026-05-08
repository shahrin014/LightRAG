"""
Integration tests for API and WebUI path prefix support via root_path.

With the root_path approach, routes always stay at their natural paths
(/docs, /health, /query, /documents/...). The api_path is passed to
FastAPI's root_path parameter, which controls the servers URL in the
OpenAPI spec for correct reverse proxy operation.
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


class TestRootPathConfiguration:
    """Test that root_path is set correctly on the FastAPI app."""

    def test_root_path_set_when_path_provided(self, mock_args_api_path):
        """Test app.root_path reflects api_path."""
        with patch('lightrag.api.lightrag_server.LightRAG') as mock_rag:
            mock_rag.return_value = MagicMock()
            from lightrag.api.lightrag_server import create_app
            app = create_app(mock_args_api_path)
            assert app.root_path == "/test-api"

    def test_root_path_none_when_no_prefix(self, mock_args_no_prefix):
        """Test app.root_path is None when no path is configured."""
        with patch('lightrag.api.lightrag_server.LightRAG') as mock_rag:
            mock_rag.return_value = MagicMock()
            from lightrag.api.lightrag_server import create_app
            app = create_app(mock_args_no_prefix)
            assert not app.root_path


class TestRoutesAtNaturalPaths:
    """Test that routes stay at their natural paths regardless of root_path."""

    def test_routes_accessible_at_both_paths_with_prefix(self, mock_args_api_path):
        """With root_path, routes work at both prefixed and natural paths.

        Root_path is set on the app. When a request comes in with the prefix,
        FastAPI injects root_path into the ASGI scope, and Starlette strips
        it from the path before matching. So /test-api/docs and /docs both work.
        """
        with patch('lightrag.api.lightrag_server.LightRAG') as mock_rag:
            mock_rag.return_value = MagicMock()
            from lightrag.api.lightrag_server import create_app
            app = create_app(mock_args_api_path)
            client = TestClient(app)

            # Natural path works
            response = client.get('/docs')
            assert response.status_code == 200

            response = client.get('/openapi.json')
            assert response.status_code == 200

            # Prefixed path also works (FastAPI strips root_path from scope)
            response = client.get('/test-api/docs')
            assert response.status_code == 200

            response = client.get('/test-api/openapi.json')
            assert response.status_code == 200

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

            response = client.get('/test-api/docs')
            assert response.status_code == 404


class TestOpenAPISpecIntegration:
    """Test that OpenAPI spec uses root_path for servers URL."""

    def test_openapi_spec_has_servers_url_with_prefix(self, mock_args_api_path):
        """Test OpenAPI spec servers URL includes the prefix via root_path."""
        with patch('lightrag.api.lightrag_server.LightRAG') as mock_rag:
            mock_rag.return_value = MagicMock()
            from lightrag.api.lightrag_server import create_app
            app = create_app(mock_args_api_path)
            client = TestClient(app)

            response = client.get('/openapi.json')
            assert response.status_code == 200
            spec = response.json()

            servers = spec.get("servers", [])
            assert len(servers) > 0
            assert "/test-api" in servers[0].get("url", "")

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
                assert not path.startswith("/test-api/")


class TestWebUIPrefixIntegration:
    """Test that WebUI is served at the correct path."""

    def test_webui_at_prefixed_path(self, mock_args_api_path):
        """Test WebUI assets at configured path with api_path."""
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
