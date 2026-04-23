"""系统设置路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.response import APIResponse, ErrorCode
from ...services.settings_service import SettingsService

router = APIRouter()


@router.get("")
async def get_settings(db: AsyncSession = Depends(get_db)):
    """获取系统设置"""
    service = SettingsService(db)
    
    try:
        settings = await service.get_all()
        return APIResponse(data=settings)
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )


@router.put("")
async def update_settings(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """更新系统设置"""
    service = SettingsService(db)
    
    try:
        await service.update(data)
        return APIResponse(data={"updated": True})
    except Exception as e:
        return APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )
