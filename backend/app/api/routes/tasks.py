"""任务管理路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ...core.database import get_db
from ...core.response import APIResponse, ErrorCode
from ...services.task_scheduler import get_scheduler

router = APIRouter()


@router.get("")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """获取任务列表"""
    from sqlalchemy import select, func
    from ...models.tables import Task
    
    query = select(Task)
    
    if status:
        query = query.where(Task.status == status)
    if task_type:
        query = query.where(Task.task_type == task_type)
    if target_type:
        query = query.where(Task.target_type == target_type)
    if target_id:
        query = query.where(Task.target_id == target_id)
    
    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页
    offset = (page - 1) * page_size
    query = query.order_by(Task.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    items = []
    for t in tasks:
        items.append({
            "id": t.id,
            "task_type": t.task_type,
            "target_type": t.target_type,
            "target_id": t.target_id,
            "status": t.status,
            "progress": t.progress,
            "message": t.message,
            "log_path": t.log_path,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "finished_at": t.finished_at.isoformat() if t.finished_at else None,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat(),
        })
    
    return APIResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取任务详情"""
    from sqlalchemy import select
    from ...models.tables import Task
    
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        return APIResponse(
            code=ErrorCode.NOT_FOUND,
            message="Task not found",
        )
    
    return APIResponse(data={
        "id": task.id,
        "task_type": task.task_type,
        "target_type": task.target_type,
        "target_id": task.target_id,
        "status": task.status,
        "progress": task.progress,
        "message": task.message,
        "log_path": task.log_path,
        "payload_json": task.payload_json,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    })


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: int):
    """取消任务"""
    scheduler = get_scheduler()
    
    if not scheduler:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="Task scheduler not initialized",
        )
    
    try:
        success = await scheduler.cancel_task(task_id)
        if success:
            return APIResponse(data={"canceled": True})
        else:
            return APIResponse(
                code=ErrorCode.STATE_ERROR,
                message="Task cannot be canceled (already completed or not found)",
            )
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.post("/{task_id}/retry")
async def retry_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """重试失败的任务"""
    from sqlalchemy import select
    from ...models.tables import Task
    
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        return APIResponse(
            code=ErrorCode.NOT_FOUND,
            message="Task not found",
        )
    
    if task.status != "failed":
        return APIResponse(
            code=ErrorCode.STATE_ERROR,
            message="Only failed tasks can be retried",
        )
    
    # 创建新任务
    scheduler = get_scheduler()
    if not scheduler:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="Task scheduler not initialized",
        )
    
    try:
        import json
        payload = json.loads(task.payload_json) if task.payload_json else None
        
        new_task_id = await scheduler.create_task(
            task_type=task.task_type,
            target_type=task.target_type,
            target_id=task.target_id,
            payload=payload,
        )
        
        return APIResponse(data={
            "task_id": new_task_id,
            "status": "pending",
        })
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )
