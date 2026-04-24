"""Pydantic Schema 定义"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime


# ============ Engine 相关 Schema ============

class EngineStatusResponse(BaseModel):
    """引擎状态响应"""
    model_config = ConfigDict(protected_namespaces=())
    python_path: Optional[str] = None
    python_version: Optional[str] = None
    pip_version: Optional[str] = None
    venv_path: Optional[str] = None
    gpu_type: str = "unknown"
    cuda_version: Optional[str] = None
    rocm_version: Optional[str] = None
    gpu_info: Optional[Any] = None
    nvidia_smi_available: bool = False
    rocm_smi_available: bool = False
    torch_version: Optional[str] = None
    transformers_version: Optional[str] = None
    vllm_version: Optional[str] = None
    status: str = "not_installed"
    message: Optional[str] = None
    last_checked_at: Optional[datetime] = None


class EngineInstallRequest(BaseModel):
    """安装引擎请求"""
    python_path: Optional[str] = None
    venv_path: Optional[str] = None
    install_args: str = ""


# ============ Model 相关 Schema ============

class ModelCreate(BaseModel):
    """创建模型请求"""
    name: str = Field(..., min_length=1)
    source_type: str = Field(..., pattern="^(huggingface|modelscope|local)$")
    source_repo: str = Field(..., min_length=1)
    source_revision: str = "main"
    local_path: str = Field(..., min_length=1)
    remark: str = ""


class ModelUpdate(BaseModel):
    """更新模型请求"""
    name: Optional[str] = None
    source_repo: Optional[str] = None
    source_revision: Optional[str] = None
    local_path: Optional[str] = None
    remark: Optional[str] = None


class ModelResponse(BaseModel):
    """模型响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    source_type: str
    source_repo: str
    source_revision: str
    local_path: str
    local_size_bytes: int = 0
    status: str
    meta_json: Optional[Dict[str, Any]] = None
    remark: Optional[str] = None
    last_analyzed_at: Optional[datetime] = None
    last_downloaded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ModelListResponse(BaseModel):
    """模型列表响应"""
    items: list[ModelResponse]
    total: int
    page: int
    page_size: int


# ============ Instance 相关 Schema ============

class InstanceCreate(BaseModel):
    """创建实例请求"""
    name: str = Field(..., min_length=1)
    model_id: int
    host: str = "0.0.0.0"
    port: int = Field(..., ge=1, le=65535)
    served_model_name: Optional[str] = None
    dtype: str = "auto"
    tensor_parallel_size: int = Field(default=1, ge=1)
    gpu_memory_utilization: float = Field(default=0.9, gt=0, le=1)
    max_model_len: Optional[int] = None
    max_num_seqs: Optional[int] = None
    trust_remote_code: bool = False
    quantization: Optional[str] = None
    api_key: Optional[str] = None
    extra_args_json: Dict[str, Any] = Field(default_factory=dict)


class InstanceUpdate(BaseModel):
    """更新实例请求"""
    name: Optional[str] = None
    served_model_name: Optional[str] = None
    dtype: Optional[str] = None
    tensor_parallel_size: Optional[int] = None
    gpu_memory_utilization: Optional[float] = None
    max_model_len: Optional[int] = None
    max_num_seqs: Optional[int] = None
    trust_remote_code: Optional[bool] = None
    quantization: Optional[str] = None
    api_key: Optional[str] = None
    extra_args_json: Optional[Dict[str, Any]] = None


class InstanceResponse(BaseModel):
    """实例响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    model_id: int
    model_name: Optional[str] = None
    host: str
    port: int
    served_model_name: Optional[str] = None
    dtype: str
    tensor_parallel_size: int
    gpu_memory_utilization: float
    max_model_len: Optional[int] = None
    max_num_seqs: Optional[int] = None
    trust_remote_code: bool
    quantization: Optional[str] = None
    api_key: Optional[str] = None
    pid: Optional[int] = None
    status: str
    health_status: str = "unknown"
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    last_health_check_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class InstanceListResponse(BaseModel):
    """实例列表响应"""
    items: list[InstanceResponse]
    total: int
    page: int
    page_size: int


# ============ Task 相关 Schema ============

class TaskResponse(BaseModel):
    """任务响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_type: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    status: str
    progress: int
    message: Optional[str] = None
    log_path: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    """任务列表响应"""
    items: list[TaskResponse]
    total: int
    page: int
    page_size: int


# ============ Setting 相关 Schema ============

class SettingsResponse(BaseModel):
    """设置响应"""
    default_model_dir: str
    default_log_dir: str
    huggingface_token: str = ""
    modelscope_token: str = ""
    http_proxy: str = ""
    https_proxy: str = ""
    default_host: str = "0.0.0.0"
    default_port_start: int = 8000
    default_instance_template: Dict[str, Any] = Field(default_factory=dict)


class SettingsUpdate(BaseModel):
    """更新设置请求"""
    default_model_dir: Optional[str] = None
    default_log_dir: Optional[str] = None
    huggingface_token: Optional[str] = None
    modelscope_token: Optional[str] = None
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    default_host: Optional[str] = None
    default_port_start: Optional[int] = None
    default_instance_template: Optional[Dict[str, Any]] = None


# ============ System 相关 Schema ============

class SystemSummaryResponse(BaseModel):
    """系统摘要响应"""
    model_config = ConfigDict(protected_namespaces=())
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    gpu_count: int
    running_instance_count: int
    model_count: int
    downloaded_model_count: int


class GPUInfo(BaseModel):
    """GPU 信息"""
    index: int
    name: str
    memory_total_mb: int
    memory_used_mb: int
    memory_free_mb: int
    utilization_gpu: int
    temperature: int


class SystemGPUResponse(BaseModel):
    """系统 GPU 响应"""
    gpu_type: str
    gpus: list[GPUInfo]
