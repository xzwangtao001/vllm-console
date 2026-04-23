"""系统信息服务"""

import os
import psutil
import subprocess
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..models.tables import Model, ModelInstance


class SystemService:
    """系统信息服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_summary(self) -> Dict[str, Any]:
        """获取系统摘要信息"""
        # CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # 内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # 磁盘使用率
        disk = psutil.disk_usage("/")
        disk_percent = disk.percent
        
        # GPU 数量
        gpu_count = await self._get_gpu_count()
        
        # 运行中实例数
        result = await self.db.execute(
            select(func.count()).where(ModelInstance.status == "running")
        )
        running_instance_count = result.scalar() or 0
        
        # 模型总数
        result = await self.db.execute(select(func.count()).select_from(Model))
        model_count = result.scalar() or 0
        
        # 已下载模型数
        result = await self.db.execute(
            select(func.count()).where(Model.status == "downloaded")
        )
        downloaded_model_count = result.scalar() or 0
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "disk_percent": disk_percent,
            "gpu_count": gpu_count,
            "running_instance_count": running_instance_count,
            "model_count": model_count,
            "downloaded_model_count": downloaded_model_count,
        }
    
    async def _get_gpu_count(self) -> int:
        """获取 GPU 数量"""
        try:
            # 检测 NVIDIA
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=count", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
        except Exception:
            pass
        
        try:
            # 检测 AMD
            result = subprocess.run(
                ["rocm-smi", "--showallinfo"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                # 简单计算 GPU 数量
                return result.stdout.count("GPU[")
        except Exception:
            pass
        
        return 0
    
    async def get_gpu_info(self) -> Dict[str, Any]:
        """获取 GPU 详细信息"""
        # 检测 NVIDIA
        try:
            result = subprocess.run(
                ["nvidia-smi", 
                 "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                gpus = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 7:
                            gpus.append({
                                "index": int(parts[0]),
                                "name": parts[1],
                                "memory_total_mb": int(parts[2]),
                                "memory_used_mb": int(parts[3]),
                                "memory_free_mb": int(parts[4]),
                                "utilization_gpu": int(parts[5]),
                                "temperature": int(parts[6]),
                            })
                
                return {
                    "gpu_type": "nvidia",
                    "gpus": gpus,
                }
        except Exception as e:
            print(f"NVIDIA detection error: {e}")
        
        # 检测 AMD
        try:
            result = subprocess.run(
                ["rocm-smi", "--showallinfo"],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                gpus = []
                # 简化解析
                for i, line in enumerate(result.stdout.split('\n')):
                    if 'GPU[' in line or 'Card' in line:
                        gpus.append({
                            "index": len(gpus),
                            "name": "AMD GPU",
                            "memory_total_mb": 0,
                            "memory_used_mb": 0,
                            "memory_free_mb": 0,
                            "utilization_gpu": 0,
                            "temperature": 0,
                        })
                
                return {
                    "gpu_type": "amd",
                    "gpus": gpus,
                }
        except Exception as e:
            print(f"AMD detection error: {e}")
        
        return {
            "gpu_type": "none",
            "gpus": [],
        }
    
    async def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        # 模型目录
        model_dir = os.path.join(os.path.dirname(__file__), "../../data/models")
        log_dir = os.path.join(os.path.dirname(__file__), "../../data/logs")
        
        # 计算目录大小
        model_dir_size = self._get_dir_size(model_dir)
        log_dir_size = self._get_dir_size(log_dir)
        
        # 磁盘信息
        disk = psutil.disk_usage("/")
        
        return {
            "model_dir": os.path.abspath(model_dir),
            "model_dir_size_bytes": model_dir_size,
            "log_dir": os.path.abspath(log_dir),
            "log_dir_size_bytes": log_dir_size,
            "disk_total_bytes": disk.total,
            "disk_used_bytes": disk.used,
            "disk_free_bytes": disk.free,
        }
    
    def _get_dir_size(self, path: str) -> int:
        """计算目录大小"""
        total_size = 0
        if not os.path.exists(path):
            return 0
        
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.isfile(fp):
                    total_size += os.path.getsize(fp)
        
        return total_size
    
    async def get_processes(self) -> List[Dict[str, Any]]:
        """获取受管进程信息"""
        result = await self.db.execute(
            select(ModelInstance).where(ModelInstance.status == "running")
        )
        instances = result.scalars().all()
        
        processes = []
        for inst in instances:
            if inst.pid:
                try:
                    proc = psutil.Process(inst.pid)
                    processes.append({
                        "instance_id": inst.id,
                        "name": inst.name,
                        "pid": inst.pid,
                        "status": "running",
                        "cpu_percent": proc.cpu_percent(interval=0.1),
                        "memory_mb": proc.memory_info().rss / 1024 / 1024,
                        "uptime_seconds": (psutil.boot_time() - proc.create_time()) if proc.create_time() else 0,
                    })
                except psutil.NoSuchProcess:
                    pass
        
        return processes
