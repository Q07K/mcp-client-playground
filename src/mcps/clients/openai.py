import json

from mcp.types import Tool
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
)
from openai.types.chat.chat_completion import ChatCompletion

from src.core.logger import log_execution_time, mcp_logger

from .base import BaseMCPClient


class OpenAIMCPClient(BaseMCPClient):
    """OpenAI API를 사용하는 MCP 클라이언트."""

    DEFAULT_MODEL = "gpt-4o"

    def __init__(self, api_key: str) -> None:
        super().__init__()
        self.model_client = OpenAI(api_key=api_key)

    @staticmethod
    def _convert_tools(tools: list[Tool]) -> list[ChatCompletionToolParam]:
        """MCP 도구를 OpenAI 형식으로 변환."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                },
            }
            for tool in tools
        ]

    def _create_completion(
        self,
        model: str,
        messages: list[ChatCompletionMessageParam],
        tools: list[ChatCompletionToolParam] | None,
    ) -> ChatCompletion:
        """OpenAI API 호출."""
        return self.model_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools or None,
        )

    @log_execution_time(logger=mcp_logger)
    async def chat(self, user_input: str, model: str | None = None) -> str:
        """OpenAI와 대화하며 필요시 도구 호출."""
        model = model or self.DEFAULT_MODEL
        tools = await self.get_all_tools()
        openai_tools = self._convert_tools(tools) if tools else None

        messages: list[ChatCompletionMessageParam] = [
            {"role": "user", "content": user_input}
        ]
        response = self._create_completion(
            model=model, messages=messages, tools=openai_tools
        )

        # 도구 호출 루프
        call_count = 0
        while tool_calls := response.choices[0].message.tool_calls:
            messages.append(response.choices[0].message)  # type: ignore

            for tool_call in tool_calls:
                call_count += 1
                args = json.loads(tool_call.function.arguments)
                result = await self.execute_tool(
                    call_count, tool_call.function.name, args
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result.content),
                    }
                )

            response = self._create_completion(
                model=model, messages=messages, tools=openai_tools
            )

        return response.choices[0].message.content or ""


if __name__ == "__main__":
    import asyncio

    async def main() -> None:
        async with OpenAIMCPClient(api_key="sk-proj-YOUR_API_KEY") as client:
            await client.load_servers_from_config(
                '{"mcpServers": {"math_server": {"url": "http://localhost:8000/sse"}}}'
            )
            response = await client.chat(
                "What is 15 multiplied by 3, then divided by 5?"
            )
            mcp_logger.info("Final response: %s", response)

    asyncio.run(main())
