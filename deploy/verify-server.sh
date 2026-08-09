#!/usr/bin/env bash
set -euo pipefail

echo "1/4 检查容器状态"
docker compose ps

echo
echo "2/4 检查健康接口"
curl --fail --silent --show-error \
  http://127.0.0.1:8000/api/v1/health
echo

echo
echo "3/4 检查持久卷"
docker volume inspect stock_ai_data \
  --format '数据卷：{{.Name}}，位置：{{.Mountpoint}}'

echo
echo "4/4 显示最近日志"
docker compose logs --tail=30 api
