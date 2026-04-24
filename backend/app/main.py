"""FastAPI 应用主入口"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os

from .core.config import settings
from .core.database import engine as db_engine, Base, async_session_maker
from .core.response import APIResponse, ErrorCode
from .api.routes import engine, models, instances, tasks, system, settings as settings_router
from .services.task_scheduler import init_scheduler, get_scheduler


# 创建数据库表
async def init_db():
    """初始化数据库"""
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# 创建 FastAPI 应用
def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )
    
    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(engine.router, prefix="/api/engine", tags=["引擎管理"])
    app.include_router(models.router, prefix="/api/models", tags=["模型管理"])
    app.include_router(instances.router, prefix="/api/instances", tags=["实例管理"])
    app.include_router(tasks.router, prefix="/api/tasks", tags=["任务管理"])
    app.include_router(system.router, prefix="/api/system", tags=["系统信息"])
    app.include_router(settings_router.router, prefix="/api/settings", tags=["系统设置"])
    
    # 挂载前端静态文件（前端构建产物）
    frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend", "dist")
    frontend_dist = os.path.normpath(frontend_dist)
    if os.path.isdir(frontend_dist):
        app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    # 健康检查
    @app.get("/health")
    async def health_check():
        return {"status": "ok"}
    
    # 根路径 — 优先返回前端页面
    @app.get("/")
    async def root():
        if os.path.isdir(frontend_dist) and os.path.isfile(os.path.join(frontend_dist, "index.html")):
            return FileResponse(os.path.join(frontend_dist, "index.html"))
        return APIResponse(data={
            "app": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs"
        })
    
    # SPA fallback — 所有非 /api 路径返回 index.html
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if os.path.isdir(frontend_dist):
            file_path = os.path.join(frontend_dist, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(os.path.join(frontend_dist, "index.html"))
        return {"error": "frontend not built"}
    
    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content=APIResponse(
                code=ErrorCode.INTERNAL_ERROR,
                message=str(exc),
                data=None
            ).model_dump()
        )
    
    # 启动事件
    @app.on_event("startup")
    async def startup_event():
        await init_db()
        # 初始化并启动任务调度器
        scheduler = init_scheduler(async_session_maker)
        await scheduler.start()
    
    # 关闭事件
    @app.on_event("shutdown")
    async def shutdown_event():
        scheduler = get_scheduler()
        if scheduler:
            await scheduler.stop()
    
    return app


app = create_app()
