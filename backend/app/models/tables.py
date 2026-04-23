"""数据库模型定义"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from ..core.database import Base


class EngineRuntime(Base):
    """系统运行时环境检测记录"""
    
    __tablename__ = "engine_runtime"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    python_path = Column(Text, nullable=True)
    python_version = Column(Text, nullable=True)
    pip_version = Column(Text, nullable=True)
    venv_path = Column(Text, nullable=True)
    
    # GPU 类型：'nvidia' / 'amd' / 'none' / 'unknown'
    gpu_type = Column(String(20), nullable=False, default='unknown')
    
    # NVIDIA 相关
    cuda_version = Column(Text, nullable=True)
    nvidia_smi_available = Column(Integer, nullable=False, default=0)
    
    # AMD 相关
    rocm_version = Column(Text, nullable=True)
    rocm_smi_available = Column(Integer, nullable=False, default=0)
    
    # GPU 信息 JSON
    gpu_info_json = Column(Text, nullable=True)
    
    # 版本信息
    torch_version = Column(Text, nullable=True)
    transformers_version = Column(Text, nullable=True)
    vllm_version = Column(Text, nullable=True)
    
    # 状态：'ready' / 'partial' / 'not_installed' / 'error'
    status = Column(String(20), nullable=False, default='not_installed')
    message = Column(Text, nullable=True)
    
    last_checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class Model(Base):
    """模型资源定义"""
    
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    
    # 来源：'huggingface' / 'modelscope' / 'local'
    source_type = Column(String(20), nullable=False)
    source_repo = Column(Text, nullable=False)
    source_revision = Column(Text, default='main')
    
    local_path = Column(Text, nullable=False)
    local_size_bytes = Column(Integer, default=0)
    
    # 状态：'new' / 'analyzing' / 'ready_to_download' / 'downloading' / 'downloaded' / 'invalid' / 'error'
    status = Column(String(20), nullable=False, default='new')
    
    meta_json = Column(Text, nullable=True)
    remark = Column(Text, nullable=True)
    
    last_analyzed_at = Column(DateTime, nullable=True)
    last_downloaded_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 唯一索引：避免重复添加同一模型
    __table_args__ = (
        Index('idx_models_unique_source', 'source_type', 'source_repo', 'source_revision', unique=True),
        Index('idx_models_status', 'status'),
    )


class ModelInstance(Base):
    """vLLM 服务实例"""
    
    __tablename__ = "model_instances"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    
    host = Column(Text, nullable=False, default='0.0.0.0')
    port = Column(Integer, nullable=False, default=8000)
    served_model_name = Column(Text, nullable=True)
    
    # 启动参数
    dtype = Column(Text, default='auto')
    tensor_parallel_size = Column(Integer, default=1)
    gpu_memory_utilization = Column(Float, default=0.9)
    max_model_len = Column(Integer, nullable=True)
    max_num_seqs = Column(Integer, nullable=True)
    trust_remote_code = Column(Integer, default=0)
    quantization = Column(Text, nullable=True)
    api_key = Column(Text, nullable=True)
    extra_args_json = Column(Text, nullable=True)
    
    # 运行状态
    launch_command = Column(Text, nullable=True)
    pid = Column(Integer, nullable=True)
    
    # 状态：'created' / 'starting' / 'running' / 'stopping' / 'stopped' / 'error'
    status = Column(String(20), nullable=False, default='created')
    
    # 健康状态：'unknown' / 'healthy' / 'unhealthy' / 'starting' / 'stopped'
    health_status = Column(String(20), default='unknown')
    
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    last_health_check_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_instances_host_port', 'host', 'port', unique=True),
        Index('idx_instances_model_id', 'model_id'),
        Index('idx_instances_status', 'status'),
    )


class Task(Base):
    """后台任务记录"""
    
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type = Column(String(50), nullable=False)
    
    # 目标对象：'engine' / 'model' / 'instance' / 'system'
    target_type = Column(String(20), nullable=True)
    target_id = Column(Integer, nullable=True)
    
    # 状态：'pending' / 'running' / 'success' / 'failed' / 'canceled'
    status = Column(String(20), nullable=False, default='pending')
    progress = Column(Integer, default=0)
    message = Column(Text, nullable=True)
    log_path = Column(Text, nullable=True)
    payload_json = Column(Text, nullable=True)
    
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_tasks_task_type', 'task_type'),
        Index('idx_tasks_status', 'status'),
        Index('idx_tasks_target', 'target_type', 'target_id'),
    )


class AppSetting(Base):
    """系统配置项"""
    
    __tablename__ = "app_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), nullable=False, unique=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(20), nullable=False, default='string')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
