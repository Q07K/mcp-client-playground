"""
애플리케이션 설정 모듈.
pydantic-settings를 사용하여 환경변수에서 설정을 로드.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MCP 서버 설정 파일 경로
    mcp_servers_path: str = Field(
        default="mcp-servers.json", description="MCP 서버 설정 파일 경로"
    )

    # OpenAI
    openai_api_key: str = Field(default="", description="OpenAI API Key")

    # Gemini
    gemini_api_key: str = Field(
        default="", description="Google Gemini API Key"
    )

    # Anthropic (향후 확장용)
    anthropic_api_key: str = Field(default="", description="Anthropic API Key")


@lru_cache
def get_settings() -> Settings:
    """설정 싱글톤 반환."""
    return Settings()


# 편의를 위한 전역 인스턴스
settings = get_settings()

__all__ = ["Settings", "get_settings", "settings"]
