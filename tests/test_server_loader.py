"""서버 로드 테스트 모듈."""

from unittest.mock import AsyncMock, patch

import pytest

from src.core.config import TransportType
from src.mcps.clients.openai import OpenAIMCPClient


class TestLoadServersFromConfig:
    """load_servers_from_config 메서드 테스트"""

    @pytest.fixture
    def mock_openai_client(self):
        """OpenAI 클라이언트 Mock"""
        with patch("src.mcps.clients.openai.OpenAI"):
            client = OpenAIMCPClient(api_key="test-api-key")
            yield client

    @pytest.mark.asyncio
    async def test_load_from_dict(self, mock_openai_client):
        """딕셔너리에서 서버 로드 테스트"""
        # Arrange
        mock_openai_client.add_server = AsyncMock()
        config_dict = {
            "mcpServers": {
                "server1": {"url": "http://localhost:8000/sse"},
                "server2": {"url": "http://localhost:8001/sse"},
            }
        }

        # Act
        await mock_openai_client.load_servers_from_config(config_dict)

        # Assert
        assert mock_openai_client.add_server.call_count == 2

    @pytest.mark.asyncio
    async def test_load_from_json_string(self, mock_openai_client):
        """JSON 문자열에서 서버 로드 테스트"""
        # Arrange
        mock_openai_client.add_server = AsyncMock()
        json_str = """
        {
          "mcpServers": {
            "json_server": { "url": "http://localhost:9000/sse" }
          }
        }
        """

        # Act
        await mock_openai_client.load_servers_from_config(json_str)

        # Assert
        mock_openai_client.add_server.assert_called_once_with(
            name="json_server",
            url="http://localhost:9000/sse",
            transport=TransportType.SSE,
            headers={},
        )

    @pytest.mark.asyncio
    async def test_load_from_file(self, mock_openai_client, tmp_path):
        """파일에서 서버 로드 테스트"""
        # Arrange
        mock_openai_client.add_server = AsyncMock()
        config_file = tmp_path / "test_config.json"
        config_file.write_text(
            """
        {
          "mcpServers": {
            "file_server": { "url": "http://localhost:7000/sse" }
          }
        }
        """,
            encoding="utf-8",
        )

        # Act
        await mock_openai_client.load_servers_from_config(str(config_file))

        # Assert
        mock_openai_client.add_server.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_with_headers(self, mock_openai_client):
        """헤더가 포함된 설정 로드 테스트"""
        # Arrange
        mock_openai_client.add_server = AsyncMock()
        config_dict = {
            "mcpServers": {
                "auth_server": {
                    "url": "http://localhost:8000/sse",
                    "headers": {"Authorization": "Bearer test_token"},
                }
            }
        }

        # Act
        await mock_openai_client.load_servers_from_config(config_dict)

        # Assert
        mock_openai_client.add_server.assert_called_once_with(
            name="auth_server",
            url="http://localhost:8000/sse",
            transport=TransportType.SSE,
            headers={"Authorization": "Bearer test_token"},
        )

    @pytest.mark.asyncio
    async def test_load_http_transport(self, mock_openai_client):
        """HTTP transport 설정 로드 테스트"""
        # Arrange
        mock_openai_client.add_server = AsyncMock()
        config_dict = {
            "mcpServers": {
                "http_server": {
                    "url": "http://localhost:8000/mcp",
                    "transport": "http",
                }
            }
        }

        # Act
        await mock_openai_client.load_servers_from_config(config_dict)

        # Assert
        mock_openai_client.add_server.assert_called_once_with(
            name="http_server",
            url="http://localhost:8000/mcp",
            transport=TransportType.HTTP,
            headers={},
        )

    @pytest.mark.asyncio
    async def test_load_mixed_transports(self, mock_openai_client):
        """SSE와 HTTP 혼합 설정 로드 테스트"""
        # Arrange
        mock_openai_client.add_server = AsyncMock()
        config_dict = {
            "mcpServers": {
                "sse_server": {
                    "url": "http://localhost:8000/sse",
                    "transport": "sse",
                },
                "http_server": {
                    "url": "http://localhost:8001/mcp",
                    "transport": "http",
                },
            }
        }

        # Act
        await mock_openai_client.load_servers_from_config(config_dict)

        # Assert
        assert mock_openai_client.add_server.call_count == 2
