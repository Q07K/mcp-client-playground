"""OpenAI MCP Client 테스트 모듈."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mcps.clients.openai import OpenAIMCPClient

from .conftest import MockTool, MockToolResult


class TestOpenAIMCPClient:
    """OpenAI MCP Client 테스트"""

    @pytest.fixture
    def mock_openai_client(self):
        """OpenAI 클라이언트 Mock"""
        with patch("src.mcps.clients.openai.OpenAI") as mock:
            client = OpenAIMCPClient(api_key="test-api-key")
            yield client

    @pytest.mark.asyncio
    async def test_execute_tool_call_success(self, mock_openai_client):
        """툴 호출 성공 테스트"""
        # Arrange
        mock_openai_client.call_tool = AsyncMock(
            return_value=MockToolResult(content="45")
        )
        mock_openai_client.tool_to_server = {"multiply": "math_server"}
        mock_openai_client.sessions = {"math_server": MagicMock()}

        # Act
        result = await mock_openai_client._execute_tool_call(
            call_count=1, tool_name="multiply", tool_args={"a": 15, "b": 3}
        )

        # Assert
        assert result.content == "45"
        mock_openai_client.call_tool.assert_called_once_with(
            "multiply", {"a": 15, "b": 3}
        )

    @pytest.mark.asyncio
    async def test_execute_tool_call_not_found(self, mock_openai_client):
        """존재하지 않는 툴 호출 테스트"""

        # Arrange
        async def raise_value_error(name, args):
            raise ValueError(
                f"Tool '{name}' not found in any connected server."
            )

        mock_openai_client.call_tool = raise_value_error
        mock_openai_client.tool_to_server = {}

        # Act & Assert
        with pytest.raises(ValueError, match="not found"):
            await mock_openai_client._execute_tool_call(
                call_count=1, tool_name="unknown_tool", tool_args={}
            )

    @pytest.mark.asyncio
    async def test_get_all_tools(self, mock_openai_client):
        """모든 도구 목록 가져오기 테스트"""
        # Arrange
        mock_tools = [
            MockTool(
                name="add",
                description="Add two numbers",
                inputSchema={
                    "type": "object",
                    "properties": {"a": {"type": "number"}},
                },
            ),
            MockTool(
                name="multiply",
                description="Multiply two numbers",
                inputSchema={
                    "type": "object",
                    "properties": {"a": {"type": "number"}},
                },
            ),
        ]
        mock_openai_client.get_all_tools = AsyncMock(return_value=mock_tools)

        # Act
        tools = await mock_openai_client.get_all_tools()

        # Assert
        assert len(tools) == 2
        assert tools[0].name == "add"
        assert tools[1].name == "multiply"
