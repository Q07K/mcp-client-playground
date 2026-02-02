"""로깅 데코레이터 테스트 모듈."""

import asyncio
import logging

import pytest

from .conftest import MockToolResult


class TestToolCallLogging:
    """툴 호출 로깅 테스트"""

    @pytest.mark.asyncio
    async def test_logging_decorator_called(self, caplog):
        """로깅 데코레이터가 올바르게 호출되는지 테스트"""
        from src.core.logger import log_tool_call, tool_logger

        # Arrange
        tool_logger.setLevel(logging.INFO)

        class MockClient:
            @log_tool_call()
            async def _execute_tool_call(
                self, call_count: int, tool_name: str, tool_args: dict
            ):
                return MockToolResult(content="test_result")

        client = MockClient()

        # Act
        with caplog.at_level(logging.INFO, logger="tool_call"):
            result = await client._execute_tool_call(
                call_count=1, tool_name="test_tool", tool_args={"key": "value"}
            )

        # Assert
        assert result.content == "test_result"
        assert "test_tool" in caplog.text
        assert "#1" in caplog.text


class TestExecutionTimeMeasurement:
    """실행 시간 측정 테스트"""

    @pytest.mark.asyncio
    async def test_execution_time_logged(self, caplog):
        """실행 시간이 로그에 기록되는지 테스트"""
        from src.core.logger import get_logger, log_execution_time

        logger = get_logger("test")
        logger.setLevel(logging.INFO)

        @log_execution_time(logger)
        async def slow_function():
            await asyncio.sleep(0.01)  # 10ms
            return "done"

        # Act
        with caplog.at_level(logging.INFO, logger="test"):
            result = await slow_function()

        # Assert
        assert result == "done"
        assert "[START] slow_function" in caplog.text
        assert "[END] slow_function" in caplog.text
        assert "ms" in caplog.text
