# 股票 AI 后端：腾讯云轻量服务器部署

本指南用于 Ubuntu 轻量应用服务器。部署方式为：

- Docker 运行 FastAPI。
- Uvicorn 只启动一个进程，适合 2 核 2GB 和当前 SQLite 架构。
- `stock_ai_data` Docker 数据卷保存缓存、数据库和报告文件。
- DeepSeek 密钥只写入服务器的 `.env.server`，不进入镜像和小程序。

## 一、腾讯云控制台配置

1. 打开轻量应用服务器控制台，确认实例状态为“运行中”。
2. 记录公网 IP。
3. 在“防火墙”中添加 TCP 端口 `8000`。
4. 端口 `22` 用于 SSH；如果使用腾讯云网页终端，也可以先不调整它。
5. 点击服务器页面的“登录”，进入网页终端。

初次测试需要开放 `8000`。接入 AnyService 并验证成功后，可以再收紧公网访问。

## 二、安装 Docker

将整个 `stock-ai-server` 部署包上传到服务器并解压后，进入目录：

```bash
cd ~/stock-ai-server
```

安装 Docker：

```bash
sudo bash deploy/bootstrap-ubuntu.sh
```

## 三、配置 DeepSeek

复制环境变量模板：

```bash
cp deploy/server.env.example .env.server
nano .env.server
```

在编辑器中将 `DEEPSEEK_API_KEY` 后面的占位文字替换成真实密钥。
然后在另一个终端执行：

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

复制输出的随机字符，将 `.env.server` 中
`STOCK_AI_API_TOKEN` 后面的占位文字替换掉。这个令牌用于防止公网
用户直接创建任务并消耗你的 DeepSeek 额度。

按 `Ctrl+O` 保存，按回车确认，再按 `Ctrl+X` 退出。

保护密钥文件：

```bash
chmod 600 .env.server
```

不要把 `.env.server` 的内容截图或发给其他人。

## 四、构建并启动

```bash
sudo docker compose up -d --build
```

第一次构建需要下载 Python 镜像和安装 AKShare、BaoStock 等依赖，通常需要几分钟。

查看容器状态：

```bash
sudo docker compose ps
```

查看实时日志：

```bash
sudo docker compose logs -f api
```

退出实时日志使用 `Ctrl+C`，不会停止服务器。

## 五、验证

在服务器终端执行：

```bash
curl http://127.0.0.1:8000/api/v1/health
```

正常结果应包含：

```json
{"status":"ok","database":"ok","deepseek_configured":true}
```

然后在自己电脑的浏览器访问：

```text
http://你的公网IP:8000/docs
```

如果打不开，检查腾讯云轻量服务器防火墙是否已开放 TCP 8000。

健康接口不需要令牌。其他接口已经受到 `X-API-Key` 请求头保护。
例如在服务器内查询报告列表时，需要执行：

```bash
set -a
source .env.server
set +a
curl -H "X-API-Key: ${STOCK_AI_API_TOKEN}" \
  http://127.0.0.1:8000/api/v1/stocks/600519/reports
```

也可以运行完整检查：

```bash
sudo bash deploy/verify-server.sh
```

## 六、常用维护命令

重启：

```bash
sudo docker compose restart api
```

更新代码后重新构建：

```bash
sudo docker compose up -d --build
```

停止服务但保留数据：

```bash
sudo docker compose down
```

查看日志：

```bash
sudo docker compose logs --tail=100 api
```

不要执行下面的命令：

```text
docker compose down -v
docker volume rm stock_ai_data
```

它们会删除持久化数据库和报告。

## 七、下一步：接入微信小程序

服务器接口正常后，再进行以下操作：

1. 创建腾讯云 CloudBase 环境并绑定当前小程序 AppID。
2. 在 AnyService 中接入这台轻量服务器的 `8000` 端口。
3. 将小程序的请求模块由本地 `wx.request` 切换为
   `wx.cloud.callContainer`，并在请求头中携带 `X-API-Key`。
4. 上传小程序体验版并在手机微信中测试。

完成服务器验证前，不要修改小程序接口地址。
