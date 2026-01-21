#!/bin/bash

# Shadow Writing 监控服务启动脚本
# 使用方法: ./start-monitoring.sh

echo "启动 Shadow Writing 监控服务..."

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "Docker 未运行，请先启动 Docker"
    exit 1
fi

# 创建必要的目录
mkdir -p monitoring/prometheus
mkdir -p monitoring/grafana/provisioning/datasources
mkdir -p monitoring/grafana/provisioning/dashboards

# 启动监控服务
echo "启动 Prometheus 和 Grafana..."
docker-compose --profile monitoring up -d

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo "检查服务状态..."
if docker-compose --profile monitoring ps | grep -q "Up"; then
    echo "监控服务启动成功！"
    echo ""
    echo "服务访问地址:"
    echo "  - Grafana:  http://localhost:3001 (用户名: admin, 密码: admin)"
    echo "  - Prometheus: http://localhost:9090"
    echo ""
    echo "仪表板: http://localhost:3001/d/shadow-writing-dashboard"
    echo ""
    echo "请确保你的 FastAPI 应用正在运行，以便 Prometheus 能够收集指标"
    echo "FastAPI 指标端点: http://localhost:8000/metrics"
else
    echo "服务启动失败，请检查日志:"
    docker-compose --profile monitoring logs
    exit 1
fi
