"""任务调度服务 - 异步任务队列"""

import asyncio
import os
import json
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Awaitable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.tables import Task
from ..services.env_service import EnvironmentService
from ..services.model_service import ModelService
from ..services.instance_service import InstanceService


class TaskScheduler:
    """任务调度器 - 管理后台异步任务"""
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.running_tasks: Dict[int, asyncio.Task] = {}
        self.cancel_flags: Dict[int, bool] = {}
        self._running = False
    
    async def start(self):
        """启动任务调度器"""
        self._running = True
        asyncio.create_task(self._process_queue())
        print("Task scheduler started")
    
    async def stop(self):
        """停止任务调度器"""
        self._running = False
        # 取消所有运行中的任务
        for task_id, task in self.running_tasks.items():
            if not task.done():
                task.cancel()
        print("Task scheduler stopped")
    
    async def _process_queue(self):
        """处理任务队列"""
        while self._running:
            try:
                # 从队列获取任务
                task_data = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                
                task_id = task_data["task_id"]
                task_type = task_data["task_type"]
                target_id = task_data.get("target_id")
                
                # 执行任务
                asyncio.create_task(self._execute_task(task_id, task_type, target_id))
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Task queue error: {e}")
    
    async def _execute_task(self, task_id: int, task_type: str, target_id: Optional[int] = None):
        """执行具体任务"""
        async with self.db_session_factory() as db:
            try:
                # 获取任务
                result = await db.execute(
                    select(Task).where(Task.id == task_id)
                )
                task = result.scalar_one_or_none()
                
                if not task:
                    return
                
                # 更新任务状态为运行中
                task.status = "running"
                task.started_at = datetime.now()
                await db.commit()
                
                # 根据任务类型执行
                if task_type == "engine_check":
                    await self._run_engine_check(task, db)
                elif task_type == "engine_install":
                    await self._run_engine_install(task, db)
                elif task_type == "model_analyze":
                    await self._run_model_analyze(task, target_id, db)
                elif task_type == "model_download":
                    await self._run_model_download(task, target_id, db)
                elif task_type == "instance_start":
                    await self._run_instance_start(task, target_id, db)
                elif task_type == "instance_stop":
                    await self._run_instance_stop(task, target_id, db)
                elif task_type == "instance_restart":
                    await self._run_instance_restart(task, target_id, db)
                else:
                    raise ValueError(f"Unknown task type: {task_type}")
                
                # 任务成功
                if task.status != "failed":  # 可能被子任务设置为 failed
                    task.status = "success"
                    task.progress = 100
                    if not task.message:
                        task.message = "Task completed successfully"
                
                task.finished_at = datetime.now()
                await db.commit()
                
            except asyncio.CancelledError:
                # 任务被取消
                task.status = "canceled"
                task.message = "Task was canceled by user"
                task.finished_at = datetime.now()
                await db.commit()
                print(f"Task {task_id} canceled")
                
            except Exception as e:
                # 任务失败
                task.status = "failed"
                task.message = f"{str(e)}\n\n{traceback.format_exc()}"
                task.finished_at = datetime.now()
                await db.commit()
                print(f"Task {task_id} failed: {e}")
            
            finally:
                # 从运行中移除
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]
                if task_id in self.cancel_flags:
                    del self.cancel_flags[task_id]
    
    async def _run_engine_check(self, task: Task, db: AsyncSession):
        """执行环境检测任务"""
        task.message = "Checking Python environment..."
        task.progress = 10
        await db.commit()
        
        env_data = EnvironmentService.check_all()
        
        task.message = f"Environment check completed: {env_data['status']}"
        task.progress = 100
        
        # 更新 engine_runtime
        from ..models.tables import EngineRuntime
        result = await db.execute(
            select(EngineRuntime).limit(1)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            from sqlalchemy import update
            await db.execute(
                update(EngineRuntime)
                .where(EngineRuntime.id == existing.id)
                .values(
                    python_path=env_data["python_path"],
                    python_version=env_data["python_version"],
                    pip_version=env_data["pip_version"],
                    venv_path=env_data["venv_path"],
                    gpu_type=env_data["gpu_type"],
                    cuda_version=env_data["cuda_version"],
                    rocm_version=env_data["rocm_version"],
                    nvidia_smi_available=1 if env_data["nvidia_smi_available"] else 0,
                    rocm_smi_available=1 if env_data["rocm_smi_available"] else 0,
                    gpu_info_json=json.dumps(env_data["gpu_info"]),
                    torch_version=env_data["torch_version"],
                    transformers_version=env_data["transformers_version"],
                    vllm_version=env_data["vllm_version"],
                    status=env_data["status"],
                    message=env_data["message"],
                    last_checked_at=datetime.fromisoformat(env_data["last_checked_at"]),
                )
            )
        else:
            db.add(EngineRuntime(**{
                k: v for k, v in env_data.items()
                if k not in ["gpu_info", "last_checked_at"]
            }, gpu_info_json=json.dumps(env_data["gpu_info"])))
        
        await db.commit()
    
    async def _run_engine_install(self, task: Task, db: AsyncSession):
        """执行 vLLM 安装任务"""
        task.message = "Installing vLLM..."
        task.progress = 20
        await db.commit()
        
        # 实际安装逻辑（简化版）
        log_dir = os.path.join(os.path.dirname(__file__), "../../data/logs/engine")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"install_{task.id}.log")
        task.log_path = log_path
        
        # 执行 pip install
        try:
            proc = await asyncio.create_subprocess_shell(
                "pip install vllm",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            
            with open(log_path, "w") as log_file:
                async for line in proc.stdout:
                    log_file.write(line.decode())
                    log_file.flush()
            
            await proc.wait()
            
            if proc.returncode == 0:
                task.message = "vLLM installed successfully"
                task.progress = 100
            else:
                raise Exception(f"Installation failed with code {proc.returncode}")
                
        except Exception as e:
            task.message = str(e)
            raise
        
        await db.commit()
    
    async def _run_model_analyze(self, task: Task, target_id: int, db: AsyncSession):
        """执行模型分析任务"""
        task.message = "Analyzing model..."
        task.progress = 20
        await db.commit()
        
        service = ModelService(db)
        await service.analyze_model(target_id)
        
        task.message = "Model analysis completed"
        task.progress = 100
        await db.commit()
    
    async def _run_model_download(self, task: Task, target_id: int, db: AsyncSession):
        """执行模型下载任务"""
        task.message = "Starting model download..."
        task.progress = 10
        await db.commit()
        
        service = ModelService(db)
        await service.download_model(target_id)
        
        task.message = "Model download completed"
        task.progress = 100
        await db.commit()
    
    async def _run_instance_start(self, task: Task, target_id: int, db: AsyncSession):
        """执行实例启动任务"""
        task.message = "Starting instance..."
        task.progress = 30
        await db.commit()
        
        service = InstanceService(db)
        await service.start_instance(target_id)
        
        task.message = "Instance started successfully"
        task.progress = 100
        await db.commit()
    
    async def _run_instance_stop(self, task: Task, target_id: int, db: AsyncSession):
        """执行实例停止任务"""
        task.message = "Stopping instance..."
        task.progress = 30
        await db.commit()
        
        service = InstanceService(db)
        await service.stop_instance(target_id)
        
        task.message = "Instance stopped"
        task.progress = 100
        await db.commit()
    
    async def _run_instance_restart(self, task: Task, target_id: int, db: AsyncSession):
        """执行实例重启任务"""
        task.message = "Restarting instance..."
        task.progress = 20
        await db.commit()
        
        service = InstanceService(db)
        await service.restart_instance(target_id)
        
        task.message = "Instance restarted"
        task.progress = 100
        await db.commit()
    
    async def create_task(
        self,
        task_type: str,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> int:
        """创建新任务并加入队列"""
        async with self.db_session_factory() as db:
            task = Task(
                task_type=task_type,
                target_type=target_type,
                target_id=target_id,
                status="pending",
                progress=0,
                message="Task queued",
                payload_json=json.dumps(payload) if payload else None,
            )
            db.add(task)
            await db.commit()
            await db.refresh(task)
            
            # 加入队列
            await self.task_queue.put({
                "task_id": task.id,
                "task_type": task_type,
                "target_id": target_id,
            })
            
            return task.id
    
    async def cancel_task(self, task_id: int) -> bool:
        """取消任务"""
        self.cancel_flags[task_id] = True
        
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            return True
        
        # 如果任务还在 pending 状态，直接更新为 canceled
        async with self.db_session_factory() as db:
            result = await db.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if task and task.status == "pending":
                task.status = "canceled"
                task.finished_at = datetime.now()
                await db.commit()
                return True
        
        return False
    
    async def get_task_status(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        async with self.db_session_factory() as db:
            result = await db.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if not task:
                return None
            
            return {
                "id": task.id,
                "task_type": task.task_type,
                "status": task.status,
                "progress": task.progress,
                "message": task.message,
                "log_path": task.log_path,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "finished_at": task.finished_at.isoformat() if task.finished_at else None,
            }


# 全局任务调度器实例
_scheduler: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """获取全局任务调度器"""
    return _scheduler


def init_scheduler(db_session_factory):
    """初始化任务调度器"""
    global _scheduler
    _scheduler = TaskScheduler(db_session_factory)
    return _scheduler
