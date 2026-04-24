"""引擎管理路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.response import APIResponse, ErrorCode
from ...models.tables import EngineRuntime
from ...services.task_scheduler import get_scheduler

router = APIRouter()


@router.get("/status")
async def get_engine_status(db: AsyncSession = Depends(get_db)):
    """获取引擎状态"""
    import json
    result = await db.execute(
        EngineRuntime.__table__.select().order_by(EngineRuntime.id.desc()).limit(1)
    )
    row = result.first()

    if not row:
        return APIResponse(data={
            "python_path": None, "python_version": None, "pip_version": None,
            "venv_path": None, "gpu_type": "unknown", "cuda_version": None,
            "rocm_version": None, "gpu_info": [], "nvidia_smi_available": False,
            "rocm_smi_available": False, "torch_version": None,
            "transformers_version": None, "vllm_version": None,
            "status": "not_installed", "message": "尚未检测环境",
            "last_checked_at": None,
        })

    gpu_info = json.loads(row.gpu_info_json) if row.gpu_info_json else {"gpus": []}

    return APIResponse(data={
        "python_path": row.python_path, "python_version": row.python_version,
        "pip_version": row.pip_version, "venv_path": row.venv_path,
        "gpu_type": row.gpu_type if hasattr(row, 'gpu_type') else "unknown",
        "cuda_version": row.cuda_version,
        "rocm_version": row.rocm_version if hasattr(row, 'rocm_version') else None,
        "gpu_info": gpu_info.get("gpus", []),
        "nvidia_smi_available": bool(row.nvidia_smi_available),
        "rocm_smi_available": bool(getattr(row, 'rocm_smi_available', False)),
        "torch_version": row.torch_version, "transformers_version": row.transformers_version,
        "vllm_version": row.vllm_version, "status": row.status,
        "message": row.message,
        "last_checked_at": row.last_checked_at.isoformat() if row.last_checked_at else None,
    })


@router.post("/check")
async def check_engine():
    """触发环境检测任务"""
    scheduler = get_scheduler()
    if not scheduler:
        return APIResponse(code=ErrorCode.INTERNAL_ERROR, message="Task scheduler not initialized")
    try:
        task_id = await scheduler.create_task(task_type="engine_check", target_type="engine")
        return APIResponse(data={"task_id": task_id, "task_type": "engine_check", "status": "pending"})
    except Exception as e:
        return APIResponse(code=ErrorCode.INTERNAL_ERROR, message=str(e))
