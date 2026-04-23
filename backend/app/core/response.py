from typing import Any, Optional, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""
    code: int = 0
    message: str = "ok"
    data: Optional[T] = None


class APIError(BaseModel):
    """API 错误响应"""
    code: int
    message: str
    data: None = None


# 错误码定义
class ErrorCode:
    SUCCESS = 0
    GENERAL_ERROR = 40000
    NOT_FOUND = 40001
    VALIDATION_ERROR = 40002
    STATE_ERROR = 40003
    PORT_OCCUPIED = 40004
    MODEL_NOT_DOWNLOADED = 40005
    ENV_NOT_READY = 40006
    TASK_RUNNING = 40007
    INTERNAL_ERROR = 50000
    SUBPROCESS_ERROR = 50001
    DOWNLOAD_ERROR = 50002
    HEALTH_CHECK_ERROR = 50003
