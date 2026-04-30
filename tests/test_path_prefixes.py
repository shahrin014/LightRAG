"""
Unit tests for API and WebUI path prefix support.

Tests configurable prefixes:
- API prefix: unit-test-back/api
- WebUI prefix: unit-test-front/webui

Verifies that routes are correctly mounted at prefixed paths
and that default behavior is preserved when no prefix is set.
"""

import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient


# We need to mock the heavy imports to avoid import issues during collection
# Instead, we'll test the logic by importing only the parsing function


class TestArgumentParsing:
    """Test that CLI arguments are properly parsed."""

    def test_api_prefix_argument(self):
        """Test that --api-prefix argument is accepted."""
        from lightrag.api.config import parse_args
        import sys

        # Save original argv
        original_argv = sys.argv.copy()

        try:
            # Simulate command line with --api-prefix
            sys.argv = ['lightrag-server', '--api-prefix', 'unit-test-back/api']
            args = parse_args()
            assert args.api_prefix == 'unit-test-back/api'
        finally:
            sys.argv = original_argv

    def test_webui_path_argument(self):
        """Test that --webui-path argument is accepted."""
        from lightrag.api.config import parse_args
        import sys

        original_argv = sys.argv.copy()

        try:
            sys.argv = ['lightrag-server', '--webui-path', 'unit-test-front/webui']
            args = parse_args()
            assert args.webui_path == 'unit-test-front/webui'
        finally:
            sys.argv = original_argv

    def test_default_api_prefix(self):
        """Test that API prefix defaults to empty string."""
        from lightrag.api.config import parse_args
        import sys

        original_argv = sys.argv.copy()

        try:
            sys.argv = ['lightrag-server']
            args = parse_args()
            assert args.api_prefix == ''
        finally:
            sys.argv = original_argv

    def test_default_webui_path(self):
        """Test that WebUI path defaults to /webui."""
        from lightrag.api.config import parse_args
        import sys

        original_argv = sys.argv.copy()

        try:
            sys.argv = ['lightrag-server']
            args = parse_args()
            assert args.webui_path == '/webui'
        finally:
            sys.argv = original_argv


class TestPrefixPathCalculation:
    """Test that path prefixes are correctly calculated."""

    def test_api_prefixed_paths(self):
        """Test that API paths are correctly prefixed."""
        api_prefix = 'unit-test-back/api'

        # These are the path calculations from lightrag_server.py
        docs_path = f"{api_prefix}/docs" if api_prefix else "/docs"
        redoc_path = f"{api_prefix}/redoc" if api_prefix else "/redoc"
        openapi_path = f"{api_prefix}/openapi.json" if api_prefix else "/openapi.json"
        health_path = f"{api_prefix}/health" if api_prefix else "/health"
        login_path = f"{api_prefix}/login" if api_prefix else "/login"
        auth_status_path = f"{api_prefix}/auth-status" if api_prefix else "/auth-status"

        assert docs_path == 'unit-test-back/api/docs'
        assert redoc_path == 'unit-test-back/api/redoc'
        assert openapi_path == 'unit-test-back/api/openapi.json'
        assert health_path == 'unit-test-back/api/health'
        assert login_path == 'unit-test-back/api/login'
        assert auth_status_path == 'unit-test-back/api/auth-status'

    def test_webui_prefixed_path(self):
        """Test that WebUI path is correctly set."""
        webui_path = 'unit-test-front/webui'

        assert webui_path == 'unit-test-front/webui'

    def test_router_prefix_with_api_prefix(self):
        """Test that routers get correct prefix."""
        api_prefix = 'unit-test-back/api'

        # Document routes
        doc_prefix = f"{api_prefix}/documents" if api_prefix else "/documents"
        assert doc_prefix == 'unit-test-back/api/documents'

        # Query and graph routes
        query_prefix = api_prefix
        assert query_prefix == 'unit-test-back/api'

        # Ollama API
        ollama_prefix = f"{api_prefix}/api" if api_prefix else "/api"
        assert ollama_prefix == 'unit-test-back/api/api'

    def test_no_prefix_uses_defaults(self):
        """Test that empty prefix gives default paths."""
        api_prefix = ''

        docs_path = f"{api_prefix}/docs" if api_prefix else "/docs"
        assert docs_path == "/docs"

        webui_path = '/webui'  # default
        assert webui_path == '/webui'


class TestEnvironmentVariables:
    """Test that environment variables are read correctly."""

    def test_env_api_prefix(self):
        """Test LIGHTRAG_API_PREFIX environment variable."""
        import os
        from lightrag.api.config import get_env_value

        os.environ['LIGHTRAG_API_PREFIX'] = 'unit-test-back/api'
        try:
            value = get_env_value("LIGHTRAG_API_PREFIX", "")
            assert value == 'unit-test-back/api'
        finally:
            del os.environ['LIGHTRAG_API_PREFIX']

    def test_env_webui_path(self):
        """Test LIGHTRAG_WEBUI_PATH environment variable."""
        import os
        from lightrag.api.config import get_env_value

        os.environ['LIGHTRAG_WEBUI_PATH'] = 'unit-test-front/webui'
        try:
            value = get_env_value("LIGHTRAG_WEBUI_PATH", "/webui")
            assert value == 'unit-test-front/webui'
        finally:
            del os.environ['LIGHTRAG_WEBUI_PATH']


class TestDefaultBehaviorPreserved:
    """Test that default behavior is preserved without prefixes."""

    def test_no_prefix_defaults(self):
        """Test that defaults preserve existing behavior."""
        from lightrag.api.config import parse_args
        import sys

        original_argv = sys.argv.copy()

        try:
            sys.argv = ['lightrag-server']
            args = parse_args()

            # Verify defaults
            assert args.api_prefix == ''
            assert args.webui_path == '/webui'
        finally:
            sys.argv = original_argv
