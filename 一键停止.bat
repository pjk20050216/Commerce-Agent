@echo off
title 多智能体跨境电商助手 - 一键停止
echo ======================================================================
echo           多智能体跨境电商助手 (MAA Platform) - 一键停止
echo ======================================================================
echo.
echo 正在检查并释放端口 8002 和 5173...

powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8002, 5173 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"

echo.
echo ======================================================================
echo  [OK] 后端 8002 与 前端 5173 端口已成功释放！
echo ======================================================================
echo.
echo  说明: 数据库与 Redis 容器不会被关闭，数据会保留。
echo  如需一并停止，请执行: docker compose stop postgres
echo.
pause
