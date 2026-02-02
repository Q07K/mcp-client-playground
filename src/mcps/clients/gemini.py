from google import genai
from google.genai import types
from mcp.types import Tool

from src.core.logger import log_execution_time, mcp_logger

from .base import BaseMCPClient


class GeminiMCPClient(BaseMCPClient):
    """Gemini API를 사용하는 MCP 클라이언트."""

    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: str) -> None:
        super().__init__()
        self.model_client = genai.Client(api_key=api_key)

    @staticmethod
    def _convert_tools(tools: list[Tool]) -> list[types.Tool]:
        """MCP 도구를 Gemini 형식으로 변환."""
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name=tool.name,
                        description=tool.description,
                        parameters=tool.inputSchema,
                    )
                    for tool in tools
                ]
            )
        ]

    @log_execution_time(logger=mcp_logger)
    async def chat(self, user_input: str, model: str | None = None) -> str:
        """Gemini와 대화하며 필요시 도구 호출."""
        model = model or self.DEFAULT_MODEL
        tools = await self.get_all_tools()
        gemini_tools = self._convert_tools(tools)

        chat = self.model_client.chats.create(
            model=model, config={"tools": gemini_tools}
        )
        response = chat.send_message(message=user_input)

        # 도구 호출 루프
        call_count = 0
        while fc := response.candidates[0].content.parts[0].function_call:
            call_count += 1
            result = await self.execute_tool(
                call_count, fc.name, dict(fc.args)
            )
            response = chat.send_message(
                message=types.Part.from_function_response(
                    name=fc.name, response={"result": result.content}
                )
            )

        return response.text


if __name__ == "__main__":
    import asyncio

    async def main() -> None:
        async with GeminiMCPClient(api_key="YOUR_GEMINI_API_KEY") as client:
            await client.load_servers_from_config(
                '{"mcpServers": {"math_server": {"url": "http://localhost:8000/sse"}}}'
            )
            response = await client.chat(
                "What is 15 multiplied by 3, then divided by 5?"
            )
            mcp_logger.info("Final response: %s", response)

    asyncio.run(main())
