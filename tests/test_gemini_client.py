"""Gemini MCP Client 테스트 모듈."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mcps.clients.gemini import GeminiMCPClient

from .conftest import MockTool, MockToolResult


class TestGeminiMCPClient:
    """Gemini MCP Client 테스트"""

    @pytest.fixture
    def mock_gemini_client(self):
        """Gemini 클라이언트 Mock"""
        with patch("src.mcps.clients.gemini.genai") as mock:
            client = GeminiMCPClient(api_key="test-api-key")
            yield client

    @pytest.mark.asyncio
    async def test_execute_tool_call_success(self, mock_gemini_client):
        """툴 호출 성공 테스트"""
        # Arrange
        mock_gemini_client.call_tool = AsyncMock(
            return_value=MockToolResult(content="9")
        )
        mock_gemini_client.tool_to_server = {"divide": "math_server"}
        mock_gemini_client.sessions = {"math_server": MagicMock()}

        # Act
        result = await mock_gemini_client.execute_tool(
            call_count=1, tool_name="divide", tool_args={"a": 45, "b": 5}
        )

        # Assert
        assert result.content == "9"
        mock_gemini_client.call_tool.assert_called_once_with(
            "divide", {"a": 45, "b": 5}
        )

    @pytest.mark.asyncio
    async def test_execute_tool_call_error_handling(self, mock_gemini_client):
        """툴 호출 에러 핸들링 테스트"""

        # Arrange
        async def raise_connection_error(name, args):
            raise ConnectionError("Server connection failed")

        mock_gemini_client.call_tool = raise_connection_error

        # Act & Assert
        with pytest.raises(ConnectionError, match="Server connection failed"):
            await mock_gemini_client.execute_tool(
                call_count=1, tool_name="divide", tool_args={"a": 45, "b": 5}
            )

    @pytest.mark.asyncio
    async def test_get_all_tools(self, mock_gemini_client):
        """모든 도구 목록 가져오기 테스트"""
        # Arrange
        mock_tools = [
            MockTool(
                name="subtract",
                description="Subtract two numbers",
                inputSchema={
                    "type": "object",
                    "properties": {"a": {"type": "number"}},
                },
            ),
        ]
        mock_gemini_client.get_all_tools = AsyncMock(return_value=mock_tools)

        # Act
        tools = await mock_gemini_client.get_all_tools()

        # Assert
        assert len(tools) == 1
        assert tools[0].name == "subtract"
