"""实例管理路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ...core.database import get_db
from ...core.response import APIResponse, ErrorCode
from ...services.instance_service import InstanceService
from ...services.task_scheduler import get_scheduler

router = APIRouter()


@router.get("")
async def list_instances(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    model_id: Optional[int] = None,
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """获取实例列表"""
    service = InstanceService(db)
    
    try:
        result = await service.list_instances(
            page=page,
            page_size=page_size,
            status=status,
            model_id=model_id,
            keyword=keyword,
        )
        return APIResponse(data=result)
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.post("")
async def create_instance(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """创建实例"""
    service = InstanceService(db)
    
    try:
        result = await service.create_instance(data)
        return APIResponse(data=result)
    except ValueError as e:
        return APIResponse(
            code=ErrorCode.STATE_ERROR,
            message=str(e),
        )
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.get("/{instance_id}")
async def get_instance(
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取实例详情"""
    service = InstanceService(db)
    
    try:
        result = await service.get_instance(instance_id)
        if not result:
            return APIResponse(
                code=ErrorCode.NOT_FOUND,
                message="Instance not found",
            )
        return APIResponse(data=result)
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.put("/{instance_id}")
async def update_instance(
    instance_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """更新实例"""
    service = InstanceService(db)
    
    try:
        success = await service.update_instance(instance_id, data)
        if not success:
            return APIResponse(
                code=ErrorCode.NOT_FOUND,
                message="Instance not found",
            )
        return APIResponse(data={"updated": True})
    except ValueError as e:
        return APIResponse(
            code=ErrorCode.STATE_ERROR,
            message=str(e),
        )
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.delete("/{instance_id}")
async def delete_instance(
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除实例"""
    service = InstanceService(db)
    
    try:
        success = await service.delete_instance(instance_id)
        if not success:
            return APIResponse(
                code=ErrorCode.NOT_FOUND,
                message="Instance not found",
            )
        return APIResponse(data={"deleted": True})
    except ValueError as e:
        return APIResponse(
            code=ErrorCode.STATE_ERROR,
            message=str(e),
        )
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.post("/{instance_id}/start")
async def start_instance(
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    """启动实例"""
    scheduler = get_scheduler()
    
    if not scheduler:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="Task scheduler not initialized",
        )
    
    try:
        task_id = await scheduler.create_task(
            task_type="instance_start",
            target_type="instance",
            target_id=instance_id,
        )
        return APIResponse(data={
            "task_id": task_id,
            "task_type": "instance_start",
            "status": "pending",
        })
    except ValueError as e:
        return APIResponse(
            code=ErrorCode.STATE_ERROR,
            message=str(e),
        )
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.post("/{instance_id}/stop")
async def stop_instance(
    instance_id: int,
    force: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """停止实例"""
    scheduler = get_scheduler()
    
    if not scheduler:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="Task scheduler not initialized",
        )
    
    try:
        task_id = await scheduler.create_task(
            task_type="instance_stop",
            target_type="instance",
            target_id=instance_id,
            payload={"force": force},
        )
        return APIResponse(data={
            "task_id": task_id,
            "task_type": "instance_stop",
            "status": "pending",
        })
    except ValueError as e:
        return APIResponse(
            code=ErrorCode.STATE_ERROR,
            message=str(e),
        )
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.post("/{instance_id}/restart")
async def restart_instance(
    instance_id: int,
    force: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """重启实例"""
    scheduler = get_scheduler()
    
    if not scheduler:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="Task scheduler not initialized",
        )
    
    try:
        task_id = await scheduler.create_task(
            task_type="instance_restart",
            target_type="instance",
            target_id=instance_id,
            payload={"force": force},
        )
        return APIResponse(data={
            "task_id": task_id,
            "task_type": "instance_restart",
            "status": "pending",
        })
    except ValueError as e:
        return APIResponse(
            code=ErrorCode.STATE_ERROR,
            message=str(e),
        )
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.get("/{instance_id}/status")
async def get_instance_status(
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取实例状态"""
    service = InstanceService(db)
    
    try:
        result = await service.get_instance_status(instance_id)
        return APIResponse(data=result)
    except ValueError as e:
        return APIResponse(
            code=ErrorCode.NOT_FOUND,
            message=str(e),
        )
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.get("/{instance_id}/logs")
async def get_instance_logs(
    instance_id: int,
    lines: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """获取实例日志"""
    service = InstanceService(db)
    
    try:
        result = await service.get_instance_logs(instance_id, lines, offset)
        return APIResponse(data=result)
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )
