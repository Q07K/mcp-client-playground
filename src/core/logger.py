import functools
import logging
import time
from typing import Any, Callable

# 기본 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s.%(msecs)03d] %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    """지정된 이름으로 로거를 가져옴"""
    return logging.getLogger(name)


# 툴 호출 전용 로거
tool_logger = get_logger("tool_call")
mcp_logger = get_logger("mcp_client")


def log_execution_time(logger: logging.Logger | None = None):
    """
    함수 실행 시간을 측정하고 로깅하는 데코레이터.
    동기/비동기 함수 모두 지원.
    """

    def decorator(func: Callable) -> Callable:
        _logger = logger or get_logger(func.__module__)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.perf_counter()
            _logger.info("[START] %s", func.__name__)

            try:
                result = await func(*args, **kwargs)
                elapsed = (time.perf_counter() - start_time) * 1000
                _logger.info("[END] %s - %.3fms", func.__name__, elapsed)
                return result
            except Exception as e:
                elapsed = (time.perf_counter() - start_time) * 1000
                _logger.error(
                    "[ERROR] %s - %.3fms - %s: %s",
                    func.__name__,
                    elapsed,
                    type(e).__name__,
                    e,
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.perf_counter()
            _logger.info("[START] %s", func.__name__)

            try:
                result = func(*args, **kwargs)
                elapsed = (time.perf_counter() - start_time) * 1000
                _logger.info("[END] %s - %.3fms", func.__name__, elapsed)
                return result
            except Exception as e:
                elapsed = (time.perf_counter() - start_time) * 1000
                _logger.error(
                    "[ERROR] %s - %.3fms - %s: %s",
                    func.__name__,
                    elapsed,
                    type(e).__name__,
                    e,
                )
                raise

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def log_tool_call(logger: logging.Logger | None = None):
    """
    툴 호출 전용 데코레이터.
    툴 이름, 인자, 결과, 실행 시간을 상세하게 로깅.
    """

    def decorator(func: Callable) -> Callable:
        _logger = logger or tool_logger

        @functools.wraps(func)
        async def wrapper(
            self,
            call_count: int,
            tool_name: str,
            tool_args: dict,
            *args,
            **kwargs,
        ) -> Any:
            start_time = time.perf_counter()
            _logger.info(
                "#%d Tool called: %s(%s)", call_count, tool_name, tool_args
            )

            try:
                result = await func(
                    self, call_count, tool_name, tool_args, *args, **kwargs
                )
                elapsed = (time.perf_counter() - start_time) * 1000

                # result의 content 속성 추출
                content = getattr(result, "content", result)
                _logger.info(
                    "#%d Tool result: %s (%.3fms)",
                    call_count,
                    content,
                    elapsed,
                )
                return result
            except Exception as e:
                elapsed = (time.perf_counter() - start_time) * 1000
                _logger.error(
                    "#%d Tool error: %s - %s: %s (%.3fms)",
                    call_count,
                    tool_name,
                    type(e).__name__,
                    e,
                    elapsed,
                )
                raise

        return wrapper

    return decorator
