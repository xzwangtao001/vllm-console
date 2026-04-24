"""实例管理服务"""

import os
import json
import subprocess
import signal
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.tables import ModelInstance, Model, Task


class InstanceService:
    """实例管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        # venv python path for vLLM
        self._venv_python = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "venv", "bin", "python"
        )

    async def list_instances(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        model_id: Optional[int] = None,
        keyword: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = select(ModelInstance)

        if status:
            query = query.where(ModelInstance.status == status)
        if model_id:
            query = query.where(ModelInstance.model_id == model_id)
        if keyword:
            query = query.where(
                (ModelInstance.name.contains(keyword)) |
                (ModelInstance.served_model_name.contains(keyword))
            )

        from sqlalchemy import func
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        offset = (page - 1) * page_size
        query = query.order_by(ModelInstance.created_at.desc()).offset(offset).limit(page_size)

        result = await self.db.execute(query)
        instances = result.scalars().all()

        items = []
        for inst in instances:
            model_result = await self.db.execute(
                select(Model.name).where(Model.id == inst.model_id)
            )
            model_name = model_result.scalar_one_or_none()

            items.append({
                "id": inst.id, "name": inst.name, "model_id": inst.model_id,
                "model_name": model_name, "host": inst.host, "port": inst.port,
                "served_model_name": inst.served_model_name, "dtype": inst.dtype,
                "tensor_parallel_size": inst.tensor_parallel_size,
                "gpu_memory_utilization": inst.gpu_memory_utilization,
                "max_model_len": inst.max_model_len, "max_num_seqs": inst.max_num_seqs,
                "trust_remote_code": bool(inst.trust_remote_code),
                "quantization": inst.quantization, "api_key": inst.api_key,
                "pid": inst.pid, "status": inst.status,
                "health_status": inst.health_status,
                "started_at": inst.started_at.isoformat() if inst.started_at else None,
                "stopped_at": inst.stopped_at.isoformat() if inst.stopped_at else None,
                "last_health_check_at": inst.last_health_check_at.isoformat() if inst.last_health_check_at else None,
                "created_at": inst.created_at.isoformat(),
                "updated_at": inst.updated_at.isoformat(),
            })

        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_instance(self, instance_id: int) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            select(ModelInstance).where(ModelInstance.id == instance_id)
        )
        inst = result.scalar_one_or_none()
        if not inst:
            return None

        model_result = await self.db.execute(
            select(Model.name).where(Model.id == inst.model_id)
        )
        model_name = model_result.scalar_one_or_none()

        return {
            "id": inst.id, "name": inst.name, "model_id": inst.model_id,
            "model_name": model_name, "host": inst.host, "port": inst.port,
            "served_model_name": inst.served_model_name, "dtype": inst.dtype,
            "tensor_parallel_size": inst.tensor_parallel_size,
            "gpu_memory_utilization": inst.gpu_memory_utilization,
            "max_model_len": inst.max_model_len, "max_num_seqs": inst.max_num_seqs,
            "trust_remote_code": bool(inst.trust_remote_code),
            "quantization": inst.quantization, "api_key": inst.api_key,
            "extra_args_json": json.loads(inst.extra_args_json) if inst.extra_args_json else {},
            "launch_command": inst.launch_command, "pid": inst.pid,
            "status": inst.status, "health_status": inst.health_status,
            "last_error": inst.last_error,
            "started_at": inst.started_at.isoformat() if inst.started_at else None,
            "stopped_at": inst.stopped_at.isoformat() if inst.stopped_at else None,
            "last_health_check_at": inst.last_health_check_at.isoformat() if inst.last_health_check_at else None,
            "created_at": inst.created_at.isoformat(),
            "updated_at": inst.updated_at.isoformat(),
        }

    async def create_instance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        model_result = await self.db.execute(
            select(Model).where(Model.id == data["model_id"])
        )
        model = model_result.scalar_one_or_none()
        if not model:
            raise ValueError("Model not found")
        if model.status != "downloaded":
            raise ValueError("Model not downloaded yet")

        port_result = await self.db.execute(
            select(ModelInstance).where(
                ModelInstance.host == data.get("host", "0.0.0.0"),
                ModelInstance.port == data["port"]
            )
        )
        if port_result.first():
            raise ValueError("Port already in use")

        inst = ModelInstance(
            name=data["name"], model_id=data["model_id"],
            host=data.get("host", "0.0.0.0"), port=data["port"],
            served_model_name=data.get("served_model_name"),
            dtype=data.get("dtype", "auto"),
            tensor_parallel_size=data.get("tensor_parallel_size", 1),
            gpu_memory_utilization=data.get("gpu_memory_utilization", 0.9),
            max_model_len=data.get("max_model_len"),
            max_num_seqs=data.get("max_num_seqs"),
            trust_remote_code=1 if data.get("trust_remote_code") else 0,
            quantization=data.get("quantization"),
            api_key=data.get("api_key"),
            extra_args_json=json.dumps(data.get("extra_args_json", {})),
            status="created",
        )

        self.db.add(inst)
        await self.db.commit()
        await self.db.refresh(inst)
        return {"id": inst.id}

    async def update_instance(self, instance_id: int, data: Dict[str, Any]) -> bool:
        result = await self.db.execute(
            select(ModelInstance).where(ModelInstance.id == instance_id)
        )
        inst = result.scalar_one_or_none()
        if not inst:
            return False

        if inst.status == "running":
            raise ValueError("Cannot update running instance")

        update_data = {k: v for k, v in data.items() if v is not None}
        for key, value in update_data.items():
            if key == "extra_args_json":
                setattr(inst, key, json.dumps(value))
            elif key == "trust_remote_code":
                setattr(inst, key, 1 if value else 0)
            else:
                setattr(inst, key, value)

        await self.db.commit()
        return True

    async def delete_instance(self, instance_id: int) -> bool:
        result = await self.db.execute(
            select(ModelInstance).where(ModelInstance.id == instance_id)
        )
        inst = result.scalar_one_or_none()
        if not inst:
            return False
        if inst.status == "running":
            raise ValueError("Cannot delete running instance")

        await self.db.delete(inst)
        await self.db.commit()
        return True

    def _build_launch_command(self, inst: ModelInstance, model: Model) -> str:
        """构建 vLLM 启动命令（使用 venv 中的 python）"""
        cmd = [
            self._venv_python, "-m", "vllm.entrypoints.openai.api_server",
            "--model", model.local_path,
            "--host", inst.host,
            "--port", str(inst.port),
        ]

        if inst.served_model_name:
            cmd.extend(["--served-model-name", inst.served_model_name])

        cmd.extend(["--dtype", inst.dtype])
        cmd.extend(["--tensor-parallel-size", str(inst.tensor_parallel_size)])
        cmd.extend(["--gpu-memory-utilization", str(inst.gpu_memory_utilization)])

        if inst.max_model_len:
            cmd.extend(["--max-model-len", str(inst.max_model_len)])

        if inst.max_num_seqs:
            cmd.extend(["--max-num-seqs", str(inst.max_num_seqs)])

        if inst.trust_remote_code:
            cmd.append("--trust-remote-code")

        if inst.quantization:
            cmd.extend(["--quantization", inst.quantization])

        if inst.extra_args_json:
            extra_args = json.loads(inst.extra_args_json)
            for key, value in extra_args.items():
                cmd.extend([f"--{key}", str(value)])

        return " ".join(cmd)

    async def start_instance(self, instance_id: int) -> Dict[str, Any]:
        result = await self.db.execute(
            select(ModelInstance).where(ModelInstance.id == instance_id)
        )
        inst = result.scalar_one_or_none()
        if not inst:
            raise ValueError("Instance not found")
        if inst.status == "running":
            raise ValueError("Instance already running")

        model_result = await self.db.execute(
            select(Model).where(Model.id == inst.model_id)
        )
        model = model_result.scalar_one_or_none()
        if not model or model.status != "downloaded":
            raise ValueError("Model not downloaded")

        inst.status = "starting"
        await self.db.commit()

        task = Task(
            task_type="instance_start",
            target_type="instance",
            target_id=instance_id,
            status="running",
            message=f"Starting instance: {inst.name}",
        )
        self.db.add(task)
        await self.db.commit()

        launch_cmd = self._build_launch_command(inst, model)
        inst.launch_command = launch_cmd

        log_dir = os.path.join(os.path.dirname(__file__), "../../data/logs/instances")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"instance_{instance_id}.log")

        try:
            log_file = open(log_path, "w")
            proc = subprocess.Popen(
                launch_cmd, shell=True,
                stdout=log_file, stderr=subprocess.STDOUT,
                preexec_fn=os.setsid,
            )

            inst.pid = proc.pid
            inst.status = "running"
            inst.started_at = datetime.now()
            inst.health_status = "healthy"

            task.status = "success"
            task.progress = 100
            task.message = "Instance started"
            task.finished_at = datetime.now()

            await self.db.commit()

            return {"task_id": task.id, "pid": proc.pid, "status": "running"}

        except Exception as e:
            inst.status = "error"
            inst.last_error = str(e)
            task.status = "failed"
            task.message = str(e)
            task.finished_at = datetime.now()
            await self.db.commit()
            raise

    async def stop_instance(self, instance_id: int, force: bool = False) -> Dict[str, Any]:
        result = await self.db.execute(
            select(ModelInstance).where(ModelInstance.id == instance_id)
        )
        inst = result.scalar_one_or_none()
        if not inst:
            raise ValueError("Instance not found")
        if inst.status not in ["running", "starting"]:
            raise ValueError("Instance not running")

        inst.status = "stopping"
        await self.db.commit()

        task = Task(
            task_type="instance_stop",
            target_type="instance",
            target_id=instance_id,
            status="running",
            message=f"Stopping instance: {inst.name}",
        )
        self.db.add(task)
        await self.db.commit()

        try:
            if inst.pid:
                if force:
                    os.killpg(os.getpgid(inst.pid), signal.SIGKILL)
                else:
                    os.killpg(os.getpgid(inst.pid), signal.SIGTERM)

            inst.status = "stopped"
            inst.stopped_at = datetime.now()
            inst.health_status = "stopped"
            inst.pid = None

            task.status = "success"
            task.progress = 100
            task.message = "Instance stopped"
            task.finished_at = datetime.now()

            await self.db.commit()

            return {"task_id": task.id, "status": "stopped"}

        except Exception as e:
            inst.status = "error"
            inst.last_error = str(e)
            task.status = "failed"
            task.message = str(e)
            task.finished_at = datetime.now()
            await self.db.commit()
            raise

    async def restart_instance(self, instance_id: int, force: bool = False) -> Dict[str, Any]:
        if await self.stop_instance(instance_id, force):
            return await self.start_instance(instance_id)
        else:
            raise ValueError("Failed to restart instance")

    async def get_instance_status(self, instance_id: int) -> Dict[str, Any]:
        result = await self.db.execute(
            select(ModelInstance).where(ModelInstance.id == instance_id)
        )
        inst = result.scalar_one_or_none()
        if not inst:
            raise ValueError("Instance not found")

        pid_alive = False
        if inst.pid:
            try:
                os.kill(inst.pid, 0)
                pid_alive = True
            except OSError:
                pid_alive = False

        if inst.status == "running" and pid_alive:
            inst.health_status = "healthy"
            inst.last_health_check_at = datetime.now()
            await self.db.commit()
        elif inst.status == "running" and not pid_alive:
            inst.status = "error"
            inst.health_status = "unhealthy"
            inst.last_error = "Process died unexpectedly"
            await self.db.commit()

        return {
            "id": inst.id, "status": inst.status,
            "health_status": inst.health_status, "pid": inst.pid,
            "pid_alive": pid_alive,
            "last_health_check_at": inst.last_health_check_at.isoformat() if inst.last_health_check_at else None,
        }

    async def get_instance_logs(self, instance_id: int, lines: int = 200, offset: int = 0) -> Dict[str, Any]:
        log_dir = os.path.join(os.path.dirname(__file__), "../../data/logs/instances")
        log_path = os.path.join(log_dir, f"instance_{instance_id}.log")

        if not os.path.exists(log_path):
            return {"log_path": log_path, "content": "", "offset": offset, "lines": 0, "has_more": False, "error": "Log file not found"}

        try:
            with open(log_path, "r") as f:
                all_lines = f.readlines()

            total_lines = len(all_lines)
            start = max(0, total_lines - offset - lines)
            end = total_lines - offset

            content = "".join(all_lines[start:end])

            return {
                "log_path": log_path, "content": content,
                "offset": offset, "lines": end - start,
                "has_more": start > 0,
            }
        except Exception as e:
            return {"log_path": log_path, "content": "", "offset": offset, "lines": 0, "has_more": False, "error": str(e)}
