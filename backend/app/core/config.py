import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    app_name: str = "vLLM Console"
    app_version: str = "0.1.0"
    debug: bool = True
    
    # 后端服务配置
    host: str = "0.0.0.0"
    port: int = 3000
    
    # 数据库配置
    database_url: str = "sqlite+aiosqlite:///./data/db/vllm_console.db"
    
    # 目录配置
    default_model_dir: str = "./data/models"  # 统一模型存储根目录
    default_log_dir: str = "./data/logs"
    
    # Token 配置（可选）
    huggingface_token: Optional[str] = None
    modelscope_token: Optional[str] = None
    
    # 代理配置（可选）
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    
    # 默认实例参数
    default_host: str = "0.0.0.0"
    default_port_start: int = 8000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
