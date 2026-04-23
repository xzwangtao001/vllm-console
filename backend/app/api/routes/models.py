"""模型管理路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ...core.database import get_db
from ...core.response import APIResponse, ErrorCode
from ...schemas.schemas import ModelCreate, ModelUpdate
from ...services.model_service import ModelService
from ...services.task_scheduler import get_scheduler

router = APIRouter()


@router.get("")
async def list_models(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    source_type: Optional[str] = None,
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """获取模型列表"""
    service = ModelService(db)
    
    try:
        result = await service.list_models(
            page=page,
            page_size=page_size,
            status=status,
            source_type=source_type,
            keyword=keyword,
        )
        return APIResponse(data=result)
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.post("")
async def create_model(
    data: ModelCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建模型"""
    service = ModelService(db)
    
    try:
        result = await service.create_model(data)
        return APIResponse(data=result)
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.get("/{model_id}")
async def get_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取模型详情"""
    service = ModelService(db)
    
    try:
        result = await service.get_model(model_id)
        if not result:
            return APIResponse(
                code=ErrorCode.NOT_FOUND,
                message="Model not found",
            )
        return APIResponse(data=result)
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.put("/{model_id}")
async def update_model(
    model_id: int,
    data: ModelUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新模型"""
    service = ModelService(db)
    
    try:
        success = await service.update_model(model_id, data)
        if not success:
            return APIResponse(
                code=ErrorCode.NOT_FOUND,
                message="Model not found",
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


@router.delete("/{model_id}")
async def delete_model(
    model_id: int,
    remove_local_files: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """删除模型"""
    service = ModelService(db)
    
    try:
        success = await service.delete_model(model_id, remove_local_files)
        if not success:
            return APIResponse(
                code=ErrorCode.NOT_FOUND,
                message="Model not found",
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


@router.post("/{model_id}/analyze")
async def analyze_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
):
    """分析模型"""
    scheduler = get_scheduler()
    
    if not scheduler:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="Task scheduler not initialized",
        )
    
    try:
        task_id = await scheduler.create_task(
            task_type="model_analyze",
            target_type="model",
            target_id=model_id,
        )
        return APIResponse(data={
            "task_id": task_id,
            "task_type": "model_analyze",
            "status": "pending",
        })
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.post("/{model_id}/download")
async def download_model(
    model_id: int,
    force: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """下载模型"""
    service = ModelService(db)
    scheduler = get_scheduler()
    
    if not scheduler:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="Task scheduler not initialized",
        )
    
    try:
        # 先验证模型状态
        model_data = await service.get_model(model_id)
        if not model_data:
            return APIResponse(
                code=ErrorCode.NOT_FOUND,
                message="Model not found",
            )
        
        if model_data["status"] == "downloaded" and not force:
            return APIResponse(
                code=ErrorCode.STATE_ERROR,
                message="Model already downloaded, use force=true to re-download",
            )
        
        # 创建下载任务
        task_id = await scheduler.create_task(
            task_type="model_download",
            target_type="model",
            target_id=model_id,
            payload={"force": force},
        )
        
        return APIResponse(data={
            "task_id": task_id,
            "task_type": "model_download",
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
