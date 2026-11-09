@echo off
title 多智能体跨境电商助手 - 一键环境初始化向导
echo ======================================================================
echo           多智能体跨境电商助手 - 一键环境初始化向导
echo ======================================================================
echo.
echo 本脚本将自动配置 uv 虚拟环境 (.venv) 与前端依赖。
echo.

cd /d "%~dp0"

REM 1. 检查 uv
echo [1/4] 检查 uv 包管理器...
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到 uv 命令！请先安装 uv。
    echo 安装方式一: 打开 https://docs.astral.sh/uv/ 按官方指引安装
    echo 安装方式二: 已在 Python 环境时执行 pip install uv
    echo.
    pause
    exit /b 1
)
echo       [OK] uv 已安装。

REM 2. 同步 Python 依赖到 .venv
echo.
echo [2/4] 同步 Python 依赖到 .venv，含 RAG 扩展，首次约 1GB，请耐心等待...
set UV_HTTP_TIMEOUT=600
uv sync --extra rag
if %errorlevel% neq 0 (
    echo.
    echo [错误] Python 依赖安装失败，请检查网络后重试。
    echo 若只是网络超时，可多次执行本脚本，uv 会断点续传。
    pause
    exit /b 1
)
echo       [OK] Python 依赖安装完成。

REM 3. 安装前端依赖
echo.
echo [3/4] 配置前端 Node.js 依赖...
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [警告] 未检测到 npm 命令！请确认是否安装 Node.js。
    echo 下载地址: https://nodejs.org/
) else (
    cd frontend
    call npm install --registry=https://registry.npmmirror.com
    cd ..
    echo       [OK] 前端依赖安装完成。
)

REM 4. 准备配置文件
echo.
echo [4/4] 准备环境变量配置文件 .env...
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo       [OK] 已从 .env.example 生成 .env。
    echo       提示: .env 中的数据库端口需与 docker-compose 的映射一致。
) else (
    echo       [OK] .env 配置文件已存在。
)

echo.
echo ======================================================================
echo  环境初始化完成！
echo  现在您可以直接双击运行根目录下的【一键启动.bat】来启动平台！
echo ======================================================================
echo.
pause
