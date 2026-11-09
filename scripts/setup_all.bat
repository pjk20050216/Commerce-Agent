@echo off
chcp 65001 >nul
echo ============================================
echo  多智能体跨境电商助手 - 一键初始化脚本
echo ============================================
echo.

cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未检测到 .venv 虚拟环境！
    echo         请先双击运行根目录下的【一键初始化环境.bat】。
    echo.
    pause
    exit /b 1
)

echo [1/6] 初始化数据库表...
uv run python -c "import asyncio; from src.db.postgres import init_db; asyncio.run(init_db()); print('数据库初始化完成')" 2>&1
if errorlevel 1 (
    echo [WARN] 数据库初始化可能已经完成（如表已存在则正常）
)

echo.
echo [2/6] 创建开发用户 (admin / admin123)...
uv run python scripts/migrate_users.py 2>&1
if errorlevel 1 (
    echo [WARN] 用户创建失败（可能已存在）
)

echo.
echo [3/6] Seed 模型厂商预置数据...
uv run python scripts/seed_model_providers.py 2>&1
if errorlevel 1 (
    echo [WARN] 厂商数据可能已存在
)

echo.
echo [4/6] 同步商品到 Redis...
uv run python scripts/sync_redis.py 2>&1
if errorlevel 1 (
    echo [WARN] Redis 同步失败
)

echo.
echo [5/6] 同步任务到 Redis...
uv run python scripts/sync_tasks_standalone.py 2>&1
if errorlevel 1 (
    echo [WARN] 任务同步失败，请确认 .venv 已安装 psycopg 与 redis 依赖
)

echo.
echo [6/6] 填充知识库（30+ 文档）...
uv run python scripts/seed_knowledge_base.py 2>&1
if errorlevel 1 (
    echo [WARN] 知识库填充失败
)

echo.
echo ============================================
echo  初始化完成！请执行以下步骤：
echo ============================================
echo.
echo  启动后端: uv run python scripts/start_backend.py
echo  启动前端: cd frontend ^&^& npm run dev
echo.
echo  后端 API:  http://localhost:8002/api/v1/
echo  API 文档:  http://localhost:8002/docs
echo  前端界面:  http://localhost:5173/
echo.
echo  默认账号: admin / admin123
echo  新用户注册: http://localhost:5173/register
echo.
echo  生成演示视频: uv run python scripts/generate_demo_video.py
echo.

pause
