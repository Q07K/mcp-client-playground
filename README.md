# MCP Client Playground

MCP(Model Context Protocol) 서버와 통신하는 Python 클라이언트 라이브러리입니다. Gemini와 OpenAI API를 지원하며, SSE 및 HTTP 전송 방식을 통해 MCP 서버의 도구들을 호출할 수 있습니다.

## 주요 기능

- **다중 MCP 서버 연결** - 여러 MCP 서버를 동시에 연결하고 관리
- **다양한 LLM 지원** - Gemini, OpenAI API 통합
- **전송 방식 선택** - SSE(Server-Sent Events) 및 HTTP 지원
- **자동 도구 매핑** - 연결된 서버의 도구를 자동으로 검색 및 매핑

## 프로젝트 구조

```
├── src/
│   ├── core/
│   │   ├── config.py      # MCP 서버 설정 스키마
│   │   └── logger.py      # 로깅 유틸리티
│   └── mcps/
│       ├── clients/
│       │   ├── base.py    # MCP 클라이언트 기본 클래스
│       │   ├── gemini.py  # Gemini API 클라이언트
│       │   └── openai.py  # OpenAI API 클라이언트
│       └── servers/
│           └── example.py # 예제 MCP 서버 (산술 연산)
├── tests/                 # 테스트 코드
├── mcp_config.example.json # 설정 파일 예시
└── main.py
```

## 설치

```bash
# 의존성 설치
pip install -e .

# 또는 uv 사용
uv sync
```

## 설정

### 설정 파일 생성

`mcp_config.json` 파일을 생성하여 MCP 서버를 설정합니다:

```json
{
  "mcpServers": {
    "math_server": {
      "url": "http://localhost:8000/sse",
      "transport": "sse",
      "headers": {},
      "timeout": 30
    },
    "weather_server": {
      "url": "http://localhost:8001/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      },
      "timeout": 60
    },
    "http_api_server": {
      "url": "http://localhost:8002/mcp",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      },
      "timeout": 30
    }
  }
}
```

### 환경 변수 설정

`.env` 파일에 API 키를 설정합니다:

```env
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
```

## 활용 예시

### 1. 예제 MCP 서버 실행

```bash
python -m src.mcps.servers.example
```

### 2. Gemini 클라이언트 사용

```python
import asyncio
from src.mcps.clients import GeminiMCPClient

async def main():
    async with GeminiMCPClient(api_key="YOUR_GEMINI_API_KEY") as client:
        # 설정 파일에서 서버 로드
        await client.load_servers_from_config("mcp_config.json")
        
        # 대화 및 도구 호출
        response = await client.chat(
            "15에 3을 곱한 후 5로 나눈 값은?"
        )
        print(response)

asyncio.run(main())
```

### 3. OpenAI 클라이언트 사용

```python
import asyncio
from src.mcps.clients import OpenAIMCPClient

async def main():
    async with OpenAIMCPClient(api_key="YOUR_OPENAI_API_KEY") as client:
        # JSON 딕셔너리로 서버 설정
        await client.load_servers_from_config({
            "mcpServers": {
                "math_server": {
                    "url": "http://localhost:8000/sse",
                    "transport": "sse"
                }
            }
        })
        
        # 대화
        response = await client.chat("100을 25로 나눈 값은?")
        print(response)

asyncio.run(main())
```

### 4. 수동 서버 추가

```python
import asyncio
from src.mcps.clients import GeminiMCPClient
from src.core.config import TransportType

async def main():
    async with GeminiMCPClient(api_key="YOUR_API_KEY") as client:
        # 개별 서버 추가
        await client.add_server(
            name="math_server",
            url="http://localhost:8000/sse",
            transport=TransportType.SSE,
            headers={"Authorization": "Bearer token"}
        )
        
        # 등록된 도구 확인
        tools = await client.get_all_tools()
        for tool in tools:
            print(f"- {tool.name}: {tool.description}")
        
        # 도구 직접 호출
        result = await client.call_tool("add", {"a": 10, "b": 20})
        print(f"결과: {result}")

asyncio.run(main())
```

### 5. 설정 로드 방식

`MCPConfig`는 다양한 방식으로 설정을 로드할 수 있습니다:

```python
# 1. 파일 경로에서 로드
await client.load_servers_from_config("mcp_config.json")

# 2. Path 객체에서 로드
from pathlib import Path
await client.load_servers_from_config(Path("mcp_config.json"))

# 3. 딕셔너리에서 로드
await client.load_servers_from_config({
    "mcpServers": {"server1": {"url": "http://localhost:8000/sse"}}
})

# 4. JSON 문자열에서 로드
await client.load_servers_from_config('{"mcpServers": {...}}')

# 5. MCPConfig 객체 직접 사용
from src.core.config import MCPConfig
config = MCPConfig.from_file("mcp_config.json")
await client.load_servers_from_config(config)
```

## 지원 전송 방식

| 전송 방식 | 설명 |
|----------|------|
| `sse` | Server-Sent Events (기본값) |
| `http` | HTTP 스트리밍 |

## 테스트 실행

```bash
pytest tests/ -v
```

## 라이선스

MIT License