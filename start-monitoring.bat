@echo off
REM Shadow Writing 监控服务启动脚本 (Windows)
REM 使用方法: .\start-monitoring.bat

echo 启动 Shadow Writing 监控服务...

REM 检查 Docker 是否运行
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Docker 未运行，请先启动 Docker
    pause
    exit /b 1
)

REM 创建必要的目录
if not exist monitoring mkdir monitoring
if not exist monitoring\prometheus mkdir monitoring\prometheus
if not exist monitoring\grafana mkdir monitoring\grafana
if not exist monitoring\grafana\provisioning mkdir monitoring\grafana\provisioning
if not exist monitoring\grafana\provisioning\datasources mkdir monitoring\grafana\provisioning\datasources
if not exist monitoring\grafana\provisioning\dashboards mkdir monitoring\grafana\provisioning\dashboards

REM 检查 docker-compose 是否可用
docker-compose version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo docker-compose 未安装或不在 PATH 中
    echo 请确保 Docker Desktop 已安装并包含 docker-compose
    pause
    exit /b 1
)

REM 启动监控服务
echo 启动 Prometheus 和 Grafana...
docker-compose --profile monitoring up -d

REM 等待服务启动
echo 等待服务启动...
timeout /t 10 /nobreak >nul

REM 检查服务状态
echo 检查服务状态...
docker-compose --profile monitoring ps | findstr "Up" >nul
if %ERRORLEVEL% equ 0 (
    echo 监控服务启动成功！
    echo.
    echo 服务访问地址:
    echo   - Grafana:  http://localhost:3001 (用户名: admin, 密码: admin)
    echo   - Prometheus: http://localhost:9090
    echo.
    echo 仪表板: http://localhost:3001/d/shadow-writing-dashboard
    echo.
    echo 请确保你的 FastAPI 应用正在运行，以便 Prometheus 能够收集指标
    echo FastAPI 指标端点: http://localhost:8000/metrics
) else (
    echo 服务启动失败，请检查日志:
    docker-compose --profile monitoring logs
)

pause
