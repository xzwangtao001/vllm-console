"""后台任务调度器"""

import asyncio
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..models.tables import Task
from ..services.environment import EnvironmentService
from ..services.model_service import ModelService
from ..services.instance_service import InstanceService


class TaskScheduler:
    """任务调度器"""

    def __init__(self, session_maker: async_sessionmaker):
        self.session_maker = session_maker
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        print("Task scheduler started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("Task scheduler stopped")

    async def create_task(self, task_type: str, target_type: Optional[str] = None,
                          target_id: Optional[int] = None, payload: Optional[Dict[str, Any]] = None) -> int:
        """创建任务到数据库"""
        async with self.session_maker() as db:
            new_task = Task(
                task_type=task_type,
                target_type=target_type,
                target_id=target_id,
                status="pending",
                progress=0,
                payload_json=json.dumps(payload) if payload else None,
            )
            db.add(new_task)
            await db.commit()
            await db.refresh(new_task)
            return new_task.id

    async def _run_loop(self):
        while self._running:
            try:
                async with self.session_maker() as db:
                    from sqlalchemy import select
                    result = await db.execute(
                        select(Task)
                        .where(Task.status == "pending")
                        .order_by(Task.created_at)
                        .limit(1)
                    )
                    task = result.scalar_one_or_none()

                    if task:
                        task.status = "running"
                        task.started_at = datetime.now()
                        await db.commit()

                        try:
                            await self._execute_task(task, db)
                        except asyncio.CancelledError:
                            task.status = "canceled"
                            task.message = "Task was canceled by user"
                            task.finished_at = datetime.now()
                            await db.commit()
                        except Exception as e:
                            task.status = "failed"
                            task.message = str(e)
                            task.finished_at = datetime.now()
                            await db.commit()
                            print(f"Task {task.id} failed: {e}")
                    else:
                        await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Scheduler error: {e}")
                await asyncio.sleep(1)

    async def _execute_task(self, task: Task, db):
        task_type = task.task_type
        target_id = task.target_id

        if task_type == "engine_check":
            await self._run_engine_check(task, db)
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

        if task.status != "failed":
            task.status = "success"
            task.progress = 100
            if not task.message:
                task.message = "Task completed successfully"

        task.finished_at = datetime.now()
        await db.commit()

    async def _run_engine_check(self, task: Task, db):
        task.message = "Checking environment..."
        task.progress = 10
        await db.commit()

        env = EnvironmentService()
        env_data = env.get_full_status()

        from ..models.tables import EngineRuntime
        from sqlalchemy import select
        result = await db.execute(select(EngineRuntime))
        record = result.scalar_one_or_none()

        if not record:
            record = EngineRuntime()
            db.add(record)

        record.python_path = env_data.get("python_path")
        record.python_version = env_data.get("python_version")
        record.pip_version = env_data.get("pip_version")
        record.venv_path = env_data.get("venv_path")
        record.cuda_version = env_data.get("cuda_version")
        record.rocm_version = env_data.get("rocm_version")
        record.gpu_info_json = json.dumps(env_data.get("gpu_info", {}))
        record.nvidia_smi_available = env_data.get("nvidia_smi_available", False)
        record.rocm_smi_available = env_data.get("rocm_smi_available", False)
        record.torch_version = env_data.get("torch_version")
        record.transformers_version = env_data.get("transformers_version")
        record.vllm_version = env_data.get("vllm_version")
        record.status = env_data.get("status", "not_installed")
        record.message = env_data.get("message")
        record.last_checked_at = datetime.now()

        await db.commit()
        task.message = f"Environment check completed: {env_data.get('status', 'unknown')}"
        task.progress = 100

    async def _run_model_analyze(self, task: Task, target_id: int, db):
        task.message = "Analyzing model..."
        task.progress = 20
        await db.commit()
        service = ModelService(db)
        await service.analyze_model(target_id)
        task.message = "Model analysis completed"
        task.progress = 100

    async def _run_model_download(self, task: Task, target_id: int, db):
        task.message = "Downloading model..."
        task.progress = 20
        await db.commit()
        service = ModelService(db)
        await service.download_model(target_id)
        task.message = "Model download completed"
        task.progress = 100

    async def _run_instance_start(self, task: Task, target_id: int, db):
        task.message = "Starting instance..."
        task.progress = 20
        await db.commit()
        service = InstanceService(db)
        await service.start_instance(target_id)
        task.message = "Instance started"
        task.progress = 100

    async def _run_instance_stop(self, task: Task, target_id: int, db):
        task.message = "Stopping instance..."
        task.progress = 20
        await db.commit()
        service = InstanceService(db)
        await service.stop_instance(target_id)
        task.message = "Instance stopped"
        task.progress = 100

    async def _run_instance_restart(self, task: Task, target_id: int, db):
        task.message = "Restarting instance..."
        task.progress = 20
        await db.commit()
        service = InstanceService(db)
        await service.stop_instance(target_id)
        await service.start_instance(target_id)
        task.message = "Instance restarted"
        task.progress = 100


_scheduler: Optional[TaskScheduler] = None


def init_scheduler(session_maker: async_sessionmaker) -> TaskScheduler:
    global _scheduler
    _scheduler = TaskScheduler(session_maker)
    return _scheduler


def get_scheduler() -> Optional[TaskScheduler]:
    return _scheduler
