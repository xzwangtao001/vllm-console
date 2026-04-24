"""模型管理服务"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..models.tables import Model, Task
from ..schemas.schemas import ModelCreate, ModelUpdate
from ..core.config import settings


def get_model_local_path(model_name: str, source_type: str) -> str:
    """根据模型名称和来源类型生成统一的本地路径
    
    路径格式: {default_model_dir}/{source_type}/{model_name}
    例如: ./data/models/huggingface/Qwen-Qwen3-8B
    """
    # 将模型名称中的斜杠替换为下划线，避免路径冲突
    safe_name = model_name.replace("/", "-")
    return os.path.join(settings.default_model_dir, source_type, safe_name)


class ModelService:
    """模型管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def list_models(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        source_type: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取模型列表"""
        # 构建查询
        query = select(Model)
        
        # 过滤条件
        if status:
            query = query.where(Model.status == status)
        if source_type:
            query = query.where(Model.source_type == source_type)
        if keyword:
            query = query.where(
                (Model.name.contains(keyword)) | (Model.source_repo.contains(keyword))
            )
        
        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 分页
        offset = (page - 1) * page_size
        query = query.order_by(Model.created_at.desc()).offset(offset).limit(page_size)
        
        result = await self.db.execute(query)
        models = result.scalars().all()
        
        items = []
        for m in models:
            items.append({
                "id": m.id,
                "name": m.name,
                "source_type": m.source_type,
                "source_repo": m.source_repo,
                "source_revision": m.source_revision,
                "local_path": m.local_path,
                "local_size_bytes": m.local_size_bytes,
                "status": m.status,
                "meta_json": json.loads(m.meta_json) if m.meta_json else None,
                "remark": m.remark,
                "last_analyzed_at": m.last_analyzed_at.isoformat() if m.last_analyzed_at else None,
                "last_downloaded_at": m.last_downloaded_at.isoformat() if m.last_downloaded_at else None,
                "created_at": m.created_at.isoformat(),
                "updated_at": m.updated_at.isoformat(),
            })
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    
    async def get_model(self, model_id: int) -> Optional[Dict[str, Any]]:
        """获取模型详情"""
        result = await self.db.execute(
            select(Model).where(Model.id == model_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        return {
            "id": model.id,
            "name": model.name,
            "source_type": model.source_type,
            "source_repo": model.source_repo,
            "source_revision": model.source_revision,
            "local_path": model.local_path,
            "local_size_bytes": model.local_size_bytes,
            "status": model.status,
            "meta_json": json.loads(model.meta_json) if model.meta_json else None,
            "remark": model.remark,
            "last_analyzed_at": model.last_analyzed_at.isoformat() if model.last_analyzed_at else None,
            "last_downloaded_at": model.last_downloaded_at.isoformat() if model.last_downloaded_at else None,
            "created_at": model.created_at.isoformat(),
            "updated_at": model.updated_at.isoformat(),
        }
    
    async def create_model(self, data: ModelCreate) -> Dict[str, Any]:
        """创建模型"""
        # 自动生成统一的本地路径
        local_path = get_model_local_path(data.name, data.source_type)
        
        model = Model(
            name=data.name,
            source_type=data.source_type,
            source_repo=data.source_repo,
            source_revision=data.source_revision,
            local_path=local_path,
            remark=data.remark,
            status="new",
        )
        
        self.db.add(model)
        await self.db.commit()
        await self.db.refresh(model)
        
        return {"id": model.id}
    
    async def update_model(self, model_id: int, data: ModelUpdate) -> bool:
        """更新模型"""
        result = await self.db.execute(
            select(Model).where(Model.id == model_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            return False
        
        # 下载中的模型不允许修改关键字段
        if model.status == "downloading":
            raise ValueError("Cannot update model while downloading")
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(model, key, value)
        
        # 如果名称或来源类型改变，重新生成本地路径
        if data.name is not None or data.source_type is not None:
            new_name = data.name or model.name
            new_source_type = data.source_type or model.source_type
            model.local_path = get_model_local_path(new_name, new_source_type)
        
        await self.db.commit()
        return True
    
    async def delete_model(self, model_id: int, remove_local_files: bool = False) -> bool:
        """删除模型"""
        result = await self.db.execute(
            select(Model).where(Model.id == model_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            return False
        
        # 检查是否有运行中的实例
        from ..models.tables import ModelInstance
        instance_result = await self.db.execute(
            select(ModelInstance).where(ModelInstance.model_id == model_id)
        )
        instances = instance_result.scalars().all()
        
        running_instances = [i for i in instances if i.status == "running"]
        if running_instances:
            raise ValueError("Cannot delete model with running instances")
        
        # 删除本地文件（可选）
        if remove_local_files and model.local_path:
            try:
                import shutil
                if os.path.exists(model.local_path):
                    shutil.rmtree(model.local_path)
            except Exception as e:
                print(f"Failed to delete local files: {e}")
        
        # 删除数据库记录
        await self.db.delete(model)
        await self.db.commit()
        
        return True
    
    async def analyze_model(self, model_id: int) -> Dict[str, Any]:
        """分析模型源"""
        result = await self.db.execute(
            select(Model).where(Model.id == model_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            raise ValueError("Model not found")
        
        # 更新状态为分析中
        model.status = "analyzing"
        await self.db.commit()
        
        # 创建分析任务
        task = Task(
            task_type="model_analyze",
            target_type="model",
            target_id=model_id,
            status="running",
            message=f"Analyzing model: {model.name}",
        )
        self.db.add(task)
        await self.db.commit()
        
        # 执行分析（这里先简化，实际应该异步）
        try:
            meta_info = await self._fetch_model_meta(model)
            
            model.status = "ready_to_download"
            model.meta_json = json.dumps(meta_info)
            model.last_analyzed_at = datetime.now()
            
            task.status = "success"
            task.progress = 100
            task.message = "Analysis completed"
            task.finished_at = datetime.now()
            
            await self.db.commit()
            
            return {"task_id": task.id, "meta": meta_info}
            
        except Exception as e:
            model.status = "invalid"
            task.status = "failed"
            task.message = str(e)
            task.finished_at = datetime.now()
            await self.db.commit()
            
            raise
    
    async def _fetch_model_meta(self, model: Model) -> Dict[str, Any]:
        """获取模型元信息"""
        if model.source_type == "huggingface":
            return await self._fetch_hf_meta(model.source_repo, model.source_revision)
        elif model.source_type == "modelscope":
            return await self._fetch_ms_meta(model.source_repo, model.source_revision)
        elif model.source_type == "local":
            return {"source": "local", "path": model.local_path}
        else:
            raise ValueError(f"Unknown source type: {model.source_type}")
    
    async def _fetch_hf_meta(self, repo: str, revision: str = "main") -> Dict[str, Any]:
        """获取 HuggingFace 模型元信息"""
        try:
            from huggingface_hub import HfApi
            api = HfApi()
            
            # 获取模型信息
            model_info = api.model_info(repo, revision=revision)
            
            return {
                "source": "huggingface",
                "repo": repo,
                "revision": revision,
                "pipeline_tag": model_info.pipeline_tag,
                "library_name": model_info.library_name,
                "tags": model_info.tags,
                "downloads": model_info.downloads,
                "likes": model_info.likes,
                "card_data": model_info.card_data.to_dict() if model_info.card_data else None,
            }
        except Exception as e:
            raise ValueError(f"Failed to fetch HuggingFace info: {e}")
    
    async def _fetch_ms_meta(self, repo: str, revision: str = "main") -> Dict[str, Any]:
        """获取 ModelScope 模型元信息"""
        try:
            from modelscope.hub.api import HubApi
            api = HubApi()
            
            # 获取模型信息
            model_info = api.get_model_info(repo, revision=revision)
            
            return {
                "source": "modelscope",
                "repo": repo,
                "revision": revision,
                "tasks": model_info.get("tasks", []),
                "framework": model_info.get("framework", []),
                "license": model_info.get("license", ""),
            }
        except Exception as e:
            raise ValueError(f"Failed to fetch ModelScope info: {e}")
    
    async def download_model(self, model_id: int, force: bool = False) -> Dict[str, Any]:
        """下载模型"""
        result = await self.db.execute(
            select(Model).where(Model.id == model_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            raise ValueError("Model not found")
        
        # 检查状态
        if model.status == "downloaded" and not force:
            raise ValueError("Model already downloaded, use force=true to re-download")
        
        if model.status not in ["ready_to_download", "downloaded", "error"]:
            raise ValueError(f"Model not ready for download, current status: {model.status}")
        
        # 更新状态
        model.status = "downloading"
        await self.db.commit()
        
        # 创建下载任务
        task = Task(
            task_type="model_download",
            target_type="model",
            target_id=model_id,
            status="running",
            message=f"Downloading model: {model.name}",
        )
        self.db.add(task)
        await self.db.commit()
        
        # 执行下载（这里先简化，实际应该异步）
        try:
            await self._execute_download(model, task)
            
            model.status = "downloaded"
            model.last_downloaded_at = datetime.now()
            
            task.status = "success"
            task.progress = 100
            task.message = "Download completed"
            task.finished_at = datetime.now()
            
            await self.db.commit()
            
            return {"task_id": task.id}
            
        except Exception as e:
            model.status = "error"
            task.status = "failed"
            task.message = str(e)
            task.finished_at = datetime.now()
            await self.db.commit()
            
            raise
    
    async def _execute_download(self, model: Model, task: Task):
        """执行模型下载"""
        # 创建目录
        os.makedirs(model.local_path, exist_ok=True)
        
        if model.source_type == "huggingface":
            await self._download_hf(model, task)
        elif model.source_type == "modelscope":
            await self._download_ms(model, task)
        elif model.source_type == "local":
            # 本地模型不需要下载
            task.message = "Local model, no download needed"
            return
        else:
            raise ValueError(f"Unknown source type: {model.source_type}")
    
    async def _download_hf(self, model: Model, task: Task):
        """从 HuggingFace 下载"""
        from huggingface_hub import snapshot_download
        
        def download_callback(progress):
            """更新进度"""
            task.progress = int(progress * 100)
        
        snapshot_download(
            repo_id=model.source_repo,
            revision=model.source_revision,
            local_dir=model.local_path,
            local_dir_use_symlinks=False,
        )
        
        # 计算大小
        total_size = 0
        for root, dirs, files in os.walk(model.local_path):
            for f in files:
                total_size += os.path.getsize(os.path.join(root, f))
        
        model.local_size_bytes = total_size
    
    async def _download_ms(self, model: Model, task: Task):
        """从 ModelScope 下载"""
        from modelscope.hub.snapshot_download import snapshot_download
        
        snapshot_download(
            model_id=model.source_repo,
            revision=model.source_revision,
            cache_dir=model.local_path,
        )
        
        # 计算大小
        total_size = 0
        for root, dirs, files in os.walk(model.local_path):
            for f in files:
                total_size += os.path.getsize(os.path.join(root, f))
        
        model.local_size_bytes = total_size
