@echo off
title 多智能体跨境电商助手 - 一键启动器
echo ======================================================================
echo           多智能体跨境电商助手 (MAA Platform) - 一键启动
echo ======================================================================
echo.

cd /d "%~dp0"

REM 1. 检查 8002 和 5173 端口是否已有服务在运行
set PORT_8002_BUSY=0
set PORT_5173_BUSY=0

powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8002 -ErrorAction SilentlyContinue) { exit 10 } else { exit 0 }"
if %errorlevel% equ 10 (
    set PORT_8002_BUSY=1
)

powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue) { exit 10 } else { exit 0 }"
if %errorlevel% equ 10 (
    set PORT_5173_BUSY=1
)

if %PORT_8002_BUSY% equ 1 goto :PORT_IN_USE
if %PORT_5173_BUSY% equ 1 goto :PORT_IN_USE

goto :START_SERVICES

:PORT_IN_USE
echo ======================================================================
echo  [提示] 检测到平台服务已经在运行中：
if %PORT_8002_BUSY% equ 1 (
    echo    - 后端服务 (端口 8002): [已在运行]
) else (
    echo    - 后端服务 (端口 8002): [未启动]
)
if %PORT_5173_BUSY% equ 1 (
    echo    - 前端界面 (端口 5173): [已在运行]
) else (
    echo    - 前端界面 (端口 5173): [未启动]
)
echo ======================================================================
echo.
echo  请选择操作：
echo    [1] 自动重启：先释放旧进程，然后全新启动（推荐）
echo    [2] 直接在浏览器中打开页面 (http://localhost:5173)
echo    [3] 取消退出
echo.
set /p USER_CHOICE="请输入选项 (1/2/3，默认回车为 1): "

if "%USER_CHOICE%"=="2" (
    echo 正在为您打开浏览器...
    start http://localhost:5173/
    exit /b 0
)

if "%USER_CHOICE%"=="3" (
    echo 已取消启动。
    exit /b 0
)

echo.
echo 正在停止旧服务进程以释放端口...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8002, 5173 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
timeout /t 1 /nobreak >nul
echo 旧服务已释放，开始重新启动...
echo.

:START_SERVICES

REM 2. 检查 .env 配置文件
if not exist ".env" (
    echo [1/3] 未检测到 .env 配置文件，正在从 .env.example 自动创建...
    copy ".env.example" ".env" >nul
    echo       [OK] .env 配置文件已就绪。
) else (
    echo [1/3] [OK] .env 配置文件已就绪。
)

REM 3. 检查前端依赖
echo [2/3] 检查前端依赖...
if not exist "frontend\node_modules" (
    echo       [提示] 首次启动检测到前端未安装依赖，正在自动执行 npm install...
    cd frontend
    call npm install --registry=https://registry.npmmirror.com
    cd ..
    echo       [OK] 前端依赖安装完成。
) else (
    echo       [OK] 前端依赖已就绪。
)

REM 4. 启动前后端服务
echo [3/3] 正在启动前后端服务...
echo.
echo       >> 正在启动后端服务 (FastAPI / 端口 8002)...
start "CBCF 后端服务 - 端口 8002" cmd /k "cd /d %~dp0 && echo 正在启动后端... && conda run --no-capture-output -n cbcf python main.py"

timeout /t 2 /nobreak >nul

echo       >> 正在启动前端服务 (Vue 3 / 端口 5173)...
start "CBCF 前端服务 - 端口 5173" cmd /k "cd /d %~dp0frontend && echo 正在启动前端... && npm run dev"

timeout /t 3 /nobreak >nul
echo.
echo ======================================================================
echo  [OK] 启动指令已发送！正在自动打开浏览器...
echo.
echo  前端界面:  http://localhost:5173/
echo  后端文档:  http://localhost:8002/docs
echo  健康检查:  http://localhost:8002/api/v1/health
echo.
echo  提示: 
echo  - 如需停止服务，请双击运行【一键停止.bat】。
echo  - 即使未填 API Key，系统也会自动启用 Mock 降级体验。
echo ======================================================================
echo.

start http://localhost:5173/

echo 按任意键可关闭此引导窗口（不会关闭已启动的前后端服务）...
pause >nul
