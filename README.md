# Analysis Agent System

## 环境配置

### 1. 安装依赖

```bash
pip install python-dotenv
```

### 2. 配置环境变量

项目使用 `.env` 文件管理敏感配置（数据库密码、API密钥等）。

#### 首次设置步骤：

1. **复制模板文件**
   ```bash
   cp .env.example .env
   ```

2. **编辑 `.env` 文件**
   
   打开 `.env` 文件，修改以下配置项为你的实际值：
   
   ```env
   # Database Configuration
   DB_HOST=your-database-host
   DB_PORT=3306
   DB_NAME=analysis
   DB_USER=your-username
   DB_PASSWORD=your-password
   
   # LLM Configuration
   VLLM_API_BASE=http://your-llm-server:8080/v1
   MODEL_NAME=qwen3-vl-8b-instruct
   ```

3. **⚠️ 重要安全提示**
   - `.env` 文件已添加到 `.gitignore`，**不会**被提交到 Git
   - **永远不要**将 `.env` 文件分享给他人或上传到公共仓库
   - 使用 `.env.example` 作为配置模板与他人共享

### 3. 配置文件说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `APP_HOST` | 服务器监听地址 | `0.0.0.0` |
| `APP_PORT` | 服务器端口 | `8000` |
| `APP_DEBUG` | 调试模式 | `true` |
| `UPLOAD_DIR` | 文件上传目录 | `./uploads` |
| `EXPORT_DIR` | 文件导出目录 | `./exports` |
| `AUTH_SECRET_KEY` | 认证密钥 | `change-me-in-production` |
| `VLLM_API_BASE` | LLM API 地址 | `http://localhost:8080/v1` |
| `VLLM_API_KEY` | LLM API 密钥 | `EMPTY` |
| `MODEL_NAME` | 模型名称 | `qwen3-vl-8b-instruct` |
| `DB_HOST` | 数据库主机 | `localhost` |
| `DB_PORT` | 数据库端口 | `3306` |
| `DB_NAME` | 数据库名称 | `analysis` |
| `DB_USER` | 数据库用户 | `root` |
| `DB_PASSWORD` | 数据库密码 | （必须设置） |

### 4. 启动应用

```bash
python run_server.py
```

应用会自动从 `.env` 文件加载配置。

---

## 项目结构

```
analysis_agent_system/
├── .env                  # 环境变量配置（不提交到Git）
├── .env.example          # 配置模板（可提交）
├── .gitignore            # Git忽略规则
├── analysis_agent_system/
│   └── app/
│       ├── config.py     # 配置加载模块
│       └── ...
├── exports/              # 导出文件目录
├── uploads/              # 上传文件目录
└── run_server.py         # 启动脚本
```

---

## 安全最佳实践

1. ✅ 使用 `.env` 文件存储敏感信息
2. ✅ 将 `.env` 添加到 `.gitignore`
3. ✅ 提供 `.env.example` 作为模板
4. ❌ 不要硬编码密码或密钥
5. ❌ 不要在代码中明文存储敏感信息
6. ❌ 不要将 `.env` 文件上传到版本控制系统
