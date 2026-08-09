#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "请使用 root 用户运行，或在命令前加 sudo。"
  exit 1
fi

apt-get update
apt-get install -y ca-certificates curl
curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
sh /tmp/get-docker.sh
rm -f /tmp/get-docker.sh

systemctl enable --now docker

echo
echo "Docker 安装完成："
docker --version
docker compose version
