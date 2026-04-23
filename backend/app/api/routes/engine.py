"""引擎管理路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.response import APIResponse, ErrorCode
from ...schemas.schemas import EngineStatusResponse, EngineInstallRequest
from ...models.tables import EngineRuntime
from ...services.task_scheduler import get_scheduler
from datetime import datetime
import json

router = APIRouter()


@router.get("/status")
async def get_engine_status(db: AsyncSession = Depends(get_db)):
    """获取引擎状态"""
    result = await db.execute(
        EngineRuntime.__table__.select().order_by(EngineRuntime.id.desc()).limit(1)
    )
    row = result.first()
    
    if not row:
        return APIResponse(data=EngineStatusResponse().model_dump())
    
    gpu_info = json.loads(row.gpu_info_json) if row.gpu_info_json else {"gpus": []}
    
    response = EngineStatusResponse(
        python_path=row.python_path,
        python_version=row.python_version,
        pip_version=row.pip_version,
        venv_path=row.venv_path,
        gpu_type=row.gpu_type,
        cuda_version=row.cuda_version,
        rocm_version=row.rocm_version,
        gpu_info=gpu_info.get("gpus", []),
        nvidia_smi_available=bool(row.nvidia_smi_available),
        rocm_smi_available=bool(row.rocm_smi_available),
        torch_version=row.torch_version,
        transformers_version=row.transformers_version,
        vllm_version=row.vllm_version,
        status=row.status,
        message=row.message,
        last_checked_at=row.last_checked_at.isoformat() if row.last_checked_at else None,
    )
    
    return APIResponse(data=response.model_dump())


@router.post("/check")
async def check_engine():
    """触发环境检测任务"""
    scheduler = get_scheduler()
    
    if not scheduler:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="Task scheduler not initialized",
        )
    
    try:
        task_id = await scheduler.create_task(
            task_type="engine_check",
            target_type="engine",
        )
        
        return APIResponse(data={
            "task_id": task_id,
            "task_type": "engine_check",
            "status": "pending",
        })
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.post("/install")
async def install_engine(request: EngineInstallRequest):
    """安装 vLLM"""
    scheduler = get_scheduler()
    
    if not scheduler:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="Task scheduler not initialized",
        )
    
    try:
        task_id = await scheduler.create_task(
            task_type="engine_install",
            target_type="engine",
            payload=request.model_dump(),
        )
        
        return APIResponse(data={
            "task_id": task_id,
            "task_type": "engine_install",
            "status": "pending",
        })
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.post("/upgrade")
async def upgrade_engine():
    """升级 vLLM"""
    scheduler = get_scheduler()
    
    if not scheduler:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="Task scheduler not initialized",
        )
    
    try:
        task_id = await scheduler.create_task(
            task_type="engine_upgrade",
            target_type="engine",
        )
        
        return APIResponse(data={
            "task_id": task_id,
            "task_type": "engine_upgrade",
            "status": "pending",
        })
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.get("/logs")
async def get_engine_logs(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """获取引擎相关日志"""
    from sqlalchemy import select, func
    from ...models.tables import Task
    
    offset = (page - 1) * page_size
    
    result = await db.execute(
        select(Task)
        .where(Task.task_type.in_(["engine_check", "engine_install", "engine_upgrade"]))
        .order_by(Task.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    
    tasks = []
    for row in result.scalars():
        tasks.append({
            "task_id": row.id,
            "task_type": row.task_type,
            "status": row.status,
            "log_path": row.log_path,
            "created_at": row.created_at.isoformat(),
        })
    
    count_result = await db.execute(
        select(func.count())
        .select_from(Task.__table__)
        .where(Task.task_type.in_(["engine_check", "engine_install", "engine_upgrade"]))
    )
    total = count_result.scalar()
    
    return APIResponse(data={
        "items": tasks,
        "total": total,
        "page": page,
        "page_size": page_size,
    })
