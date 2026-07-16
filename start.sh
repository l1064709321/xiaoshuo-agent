#!/usr/bin/env bash
# Novel Agent 一键启动脚本:自动装依赖 + 后台启动服务
# 用法: bash start.sh
set -e
cd "$(dirname "$0")"

echo "==> 检查依赖..."
python -m pip install -q -r requirements.txt 2>&1 | tail -2 || true

echo "==> 停止旧进程..."
pkill -f "run.py" 2>/dev/null || true
sleep 1

echo "==> 启动服务..."
nohup python run.py > /tmp/novel-agent.log 2>&1 &
echo $! > /tmp/novel-agent.pid

echo "==> 等待就绪..."
for i in $(seq 1 15); do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null || echo 000)
  if [ "$code" = "200" ]; then
    echo "✓ 服务已启动: http://localhost:8000/  (PID $(cat /tmp/novel-agent.pid))"
    exit 0
  fi
  sleep 1
done

echo "✗ 启动失败,日志:"
cat /tmp/novel-agent.log
exit 1
