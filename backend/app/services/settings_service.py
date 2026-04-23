"""系统设置服务"""

import json
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.tables import AppSetting


class SettingsService:
    """系统设置服务"""
    
    DEFAULT_SETTINGS = {
        "default_model_dir": "./data/models",
        "default_log_dir": "./data/logs",
        "huggingface_token": "",
        "modelscope_token": "",
        "http_proxy": "",
        "https_proxy": "",
        "default_host": "0.0.0.0",
        "default_port_start": 8000,
        "default_instance_template": {
            "dtype": "auto",
            "tensor_parallel_size": 1,
            "gpu_memory_utilization": 0.9,
        },
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all(self) -> Dict[str, Any]:
        """获取所有设置"""
        result = await self.db.execute(
            select(AppSetting)
        )
        settings = result.scalars().all()
        
        # 构建字典
        data = {}
        for s in settings:
            value = s.value
            if s.value_type == "json":
                value = json.loads(value) if value else {}
            elif s.value_type == "number":
                value = float(value) if value else 0
            elif s.value_type == "boolean":
                value = value == "true"
            data[s.key] = value
        
        # 合并默认值
        return {**self.DEFAULT_SETTINGS, **data}
    
    async def update(self, data: Dict[str, Any]) -> bool:
        """更新设置"""
        for key, value in data.items():
            # 跳过 None 值
            if value is None:
                continue
            
            # 确定值类型
            if isinstance(value, dict):
                value_type = "json"
                value_str = json.dumps(value)
            elif isinstance(value, bool):
                value_type = "boolean"
                value_str = "true" if value else "false"
            elif isinstance(value, (int, float)):
                value_type = "number"
                value_str = str(value)
            else:
                value_type = "string"
                value_str = str(value)
            
            # 更新或创建
            result = await self.db.execute(
                select(AppSetting).where(AppSetting.key == key)
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                setting.value = value_str
                setting.value_type = value_type
            else:
                self.db.add(AppSetting(
                    key=key,
                    value=value_str,
                    value_type=value_type,
                ))
        
        await self.db.commit()
        return True
    
    async def get(self, key: str) -> Optional[Any]:
        """获取单个设置"""
        result = await self.db.execute(
            select(AppSetting).where(AppSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if not setting:
            return self.DEFAULT_SETTINGS.get(key)
        
        if setting.value_type == "json":
            return json.loads(setting.value) if setting.value else {}
        elif setting.value_type == "number":
            return float(setting.value) if setting.value else 0
        elif setting.value_type == "boolean":
            return setting.value == "true"
        return setting.value
    
    async def set(self, key: str, value: Any) -> bool:
        """设置单个值"""
        return await self.update({key: value})
