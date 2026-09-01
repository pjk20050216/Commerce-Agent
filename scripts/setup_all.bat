@echo off
chcp 65001 >nul
echo ============================================
echo  多智能体跨境电商助手 - 一键初始化脚本
echo ============================================
echo.

cd /d "%~dp0\.."

echo [1/6] 初始化数据库表...
call conda run -n cbcf python -c "import asyncio; from src.db.postgres import init_db; asyncio.run(init_db()); print('数据库初始化完成')" 2>&1
if errorlevel 1 (
    echo [WARN] 数据库初始化可能已经完成（如表已存在则正常）
)

echo.
echo [2/6] 创建开发用户 (admin / admin123)...
call conda run -n cbcf python scripts/migrate_users.py 2>&1
if errorlevel 1 (
    echo [WARN] 用户创建失败（可能已存在）
)

echo.
echo [3/6] Seed 模型厂商预置数据...
call conda run -n cbcf python -c "import asyncio; from src.db.postgres import get_db_session; from src.db.model_provider_seeder import seed_model_providers; async def s(): async with get_db_session() as s2: await seed_model_providers(s2, 'system'); await s2.commit(); print('模型厂商数据完成'); asyncio.run(s())" 2>&1
if errorlevel 1 (
    echo [WARN] 厂商数据可能已存在
)

echo.
echo [4/6] 同步商品到 Redis...
call conda run -n cbcf python scripts/sync_redis.py 2>&1
if errorlevel 1 (
    echo [WARN] Redis 同步失败
)

echo.
echo [5/6] 同步任务到 Redis...
call conda run -n cbcf python scripts/sync_tasks_standalone.py 2>&1
if errorlevel 1 (
    echo [WARN] 任务同步失败，请确保 conda 环境 cbcf 已安装 psycopg 和 redis 包
)

echo.
echo [6/6] 填充知识库（30+ 文档）...
call conda run -n cbcf python scripts/seed_knowledge_base.py 2>&1
if errorlevel 1 (
    echo [WARN] 知识库填充失败
)

echo.
echo ============================================
echo  初始化完成！请执行以下步骤：
echo ============================================
echo.
echo  启动后端: conda run -n cbcf python scripts/start_backend.py
echo  启动前端: cd frontend ^&^& npm run dev
echo.
echo  后端 API:  http://localhost:8002/api/v1/
echo  API 文档:  http://localhost:8002/docs
echo  前端界面:  http://localhost:5173/
echo.
echo  默认账号: admin / admin123
echo  新用户注册: http://localhost:5173/register
echo.
echo  生成演示视频: conda run -n cbcf python scripts/generate_demo_video.py
echo.

pause
