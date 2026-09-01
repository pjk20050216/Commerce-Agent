@echo off
title 多智能体跨境电商助手 - 一键环境初始化向导
echo ======================================================================
echo           多智能体跨境电商助手 - 一键环境初始化向导
echo ======================================================================
echo.
echo 本脚本将自动为您的电脑配置 Python (Conda) 与前端依赖。
echo.

cd /d "%~dp0"

REM 1. 检查 Conda
echo [1/4] 检查 Conda...
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到 conda 命令！请先安装 Miniconda 或 Anaconda。
    echo 下载地址: https://docs.conda.io/en/latest/miniconda.html
    echo.
    pause
    exit /b 1
)
echo       [OK] Conda 已安装。

REM 2. 创建或更新 conda cbcf 环境
echo.
echo [2/4] 配置 Python 虚拟环境 (cbcf, Python 3.13)...
call conda create -n cbcf python=3.13 -y
echo       [OK] 虚拟环境创建完成，开始安装 Python 依赖...
call conda run -n cbcf pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
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
