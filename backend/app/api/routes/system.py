"""系统信息路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.response import APIResponse, ErrorCode
from ...services.system_service import SystemService

router = APIRouter()


@router.get("/summary")
async def get_system_summary(db: AsyncSession = Depends(get_db)):
    """获取系统摘要"""
    service = SystemService(db)
    
    try:
        result = await service.get_summary()
        return APIResponse(data=result)
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.get("/gpu")
async def get_gpu_info(db: AsyncSession = Depends(get_db)):
    """获取 GPU 信息"""
    service = SystemService(db)
    
    try:
        result = await service.get_gpu_info()
        return APIResponse(data=result)
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.get("/processes")
async def get_processes(db: AsyncSession = Depends(get_db)):
    """获取进程信息"""
    service = SystemService(db)
    
    try:
        result = await service.get_processes()
        return APIResponse(data=result)
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.get("/storage")
async def get_storage_info(db: AsyncSession = Depends(get_db)):
    """获取存储信息"""
    service = SystemService(db)
    
    try:
        result = await service.get_storage_info()
        return APIResponse(data=result)
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )
