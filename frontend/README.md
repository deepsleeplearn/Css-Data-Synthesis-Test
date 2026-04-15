# 交互测试前端

这个前端现在只保留一种模式：`interactive-test` 对应的 CLI 手工输入对话模式。

## 当前能力

- 选择场景后启动一轮手工测试会话
- 首轮由用户先输入，行为与 CLI 手工测试一致
- 支持 `/help`、`/slots`、`/state`、`/quit`
- 支持可选“已知地址”和“自动生成隐藏设定”配置
- 右侧实时展示已收集槽位和运行时状态

## 运行方式

1. 安装依赖
   ```bash
   pip install -r frontend/requirements.txt
   ```

2. 启动服务
   ```bash
   python -m frontend.server
   ```

3. 打开浏览器
   访问 [http://localhost:8000](http://localhost:8000)

## 账号登录

服务现在默认要求先登录，只有备案账号才能进入测试台。

1. 在本地创建账号文件
   ```bash
   cp frontend/registered_accounts.example.json frontend/registered_accounts.local.json
   ```

2. 按 `username` 和 `password` 维护备案账号
   ```json
   {
     "accounts": [
       {
         "username": "qa-admin",
         "display_name": "测试管理员",
         "password": "ChangeMe123!",
         "enabled": true
       }
     ]
   }
   ```

3. 启动服务后访问页面
   输入 URL 会先看到登录界面，只有账号命中备案名单才能进入测试页面。

如需改账号文件位置，可设置环境变量 `FRONTEND_REGISTERED_ACCOUNTS_FILE`。

## Docker 运行

仓库根目录已经提供：

- `Dockerfile`
- `docker-compose.yml`

直接在仓库根目录执行：

```bash
docker compose up -d --build
```

默认访问地址：

- 本机：`http://localhost:8527`
- 公司内网其他机器：`http://<部署机器内网IP>:8527`

## 说明

- 前端适配的是 `multi_agent_data_synthesis.cli interactive-test` 的会话语义，而不是批量生成模式。
- 默认不写输出文件，也不会持久化隐藏设定历史。
