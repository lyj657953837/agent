# 环境变量配置指南

## 📋 概述

本项目使用 `.env` 文件管理所有敏感配置，包括数据库连接、API密钥等。这种设计确保：

- ✅ 敏感信息不会泄露到版本控制系统
- ✅ 不同环境（开发/测试/生产）可以使用不同配置
- ✅ 配置集中管理，易于维护

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install python-dotenv
```

或者使用提供的 requirements.txt：

```bash
pip install -r requirements.txt
```

### 2. 创建配置文件

**Windows:**
```bash
copy .env.example .env
```

**Linux/Mac:**
```bash
cp .env.example .env
```

### 3. 编辑配置

打开 `.env` 文件，修改以下关键配置：

```env
# 数据库配置（必须修改）
DB_HOST=your-database-host
DB_NAME=analysis
DB_USER=your-username
DB_PASSWORD=your-secure-password

# LLM API 配置（根据实际部署修改）
VLLM_API_BASE=http://your-llm-server:8080/v1
MODEL_NAME=qwen3-vl-8b-instruct

# 认证密钥（生产环境必须修改）
AUTH_SECRET_KEY=generate-a-random-secret-key-here
```

### 4. 验证配置

```bash
python test_config.py
```

如果看到 "All configuration loaded successfully! ✓"，说明配置正确。

### 5. 启动应用

```bash
python run_server.py
```

---

## ⚙️ 配置项详解

### 应用设置

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `APP_HOST` | 服务器监听地址 | `0.0.0.0` | 否 |
| `APP_PORT` | 服务器端口 | `8000` | 否 |
| `APP_DEBUG` | 调试模式（true/false） | `true` | 否 |

### 文件存储

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `UPLOAD_DIR` | 文件上传目录 | `./uploads` | 否 |
| `EXPORT_DIR` | 文件导出目录 | `./exports` | 否 |
| `MAX_UPLOAD_SIZE_MB` | 最大上传文件大小（MB） | `500` | 否 |

### 认证安全

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `AUTH_SECRET_KEY` | JWT签名密钥 | `change-me-in-production` | **是（生产环境）** |

⚠️ **重要：** 生产环境必须生成强随机密钥：
```python
import secrets
print(secrets.token_urlsafe(32))
```

### LLM (VLLM) 配置

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `VLLM_API_BASE` | VLLM API 基础URL | `http://localhost:8080/v1` | **是** |
| `VLLM_API_KEY` | API 认证密钥 | `EMPTY` | 否 |
| `MODEL_NAME` | 模型名称 | `qwen3-vl-8b-instruct` | **是** |
| `LLM_MAX_TOKENS` | 最大token数 | `4096` | 否 |
| `LLM_TEMPERATURE` | 温度参数（0-1） | `0.7` | 否 |
| `LLM_TIMEOUT` | 请求超时时间（秒） | `120` | 否 |

### 数据库配置

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `DB_HOST` | 数据库主机地址 | `localhost` | **是** |
| `DB_PORT` | 数据库端口 | `3306` | 否 |
| `DB_NAME` | 数据库名称 | `analysis` | **是** |
| `DB_USER` | 数据库用户名 | `root` | **是** |
| `DB_PASSWORD` | 数据库密码 | （空） | **是** |
| `DB_POOL_SIZE` | 连接池大小 | `10` | 否 |
| `DB_MAX_OVERFLOW` | 最大溢出连接数 | `20` | 否 |
| `DB_POOL_RECYCLE` | 连接回收时间（秒） | `3600` | 否 |

---

## 🔒 安全最佳实践

### ✅ 应该做的

1. **使用 `.env` 文件存储敏感信息**
   ```env
   DB_PASSWORD=super-secret-password
   AUTH_SECRET_KEY=random-generated-key
   ```

2. **将 `.env` 添加到 `.gitignore`**
   ```gitignore
   .env
   ```

3. **提供 `.env.example` 作为模板**
   ```env
   DB_PASSWORD=your-password-here
   AUTH_SECRET_KEY=your-secret-key-here
   ```

4. **为不同环境使用不同的 `.env` 文件**
   ```
   .env.development
   .env.staging
   .env.production
   ```

5. **定期轮换密钥和密码**

### ❌ 不应该做的

1. **不要硬编码敏感信息**
   ```python
   # ✗ 错误示例
   DB_PASSWORD = "my-secret-password"
   
   # ✓ 正确示例
   DB_PASSWORD = os.getenv("DB_PASSWORD")
   ```

2. **不要将 `.env` 提交到 Git**
   ```bash
   # ✗ 永远不要这样做
   git add .env
   git commit -m "Add config"
   ```

3. **不要在日志中打印敏感信息**
   ```python
   # ✗ 错误示例
   logger.info(f"DB Password: {settings.DB_PASSWORD}")
   
   # ✓ 正确示例
   logger.info("Database configuration loaded")
   ```

4. **不要共享 `.env` 文件**
   - 不要通过邮件发送
   - 不要上传到云盘
   - 不要在聊天工具中粘贴

---

## 🌍 多环境配置

### 开发环境 (.env.development)

```env
APP_DEBUG=true
DB_HOST=localhost
DB_NAME=analysis_dev
DB_PASSWORD=dev-password
VLLM_API_BASE=http://localhost:8080/v1
```

### 生产环境 (.env.production)

```env
APP_DEBUG=false
DB_HOST=prod-db.example.com
DB_NAME=analysis_prod
DB_PASSWORD=strong-production-password
VLLM_API_BASE=https://llm.example.com/v1
AUTH_SECRET_KEY=production-secret-key
```

### 加载特定环境配置

修改 [config.py](file://d:\liyajun\AI\analysis_agent_system\analysis_agent_system\app\config.py)：

```python
import os

# Load environment-specific .env file
env = os.getenv("APP_ENV", "development")
env_file = Path(__file__).parent.parent.parent / f".env.{env}"

if env_file.exists():
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv()  # Fall back to .env
```

然后设置环境变量：

```bash
# Windows
set APP_ENV=production
python run_server.py

# Linux/Mac
export APP_ENV=production
python run_server.py
```

---

## 🐛 故障排查

### 问题1：配置未加载

**症状：** 应用使用默认值而非 `.env` 中的值

**解决方案：**
1. 检查 `.env` 文件是否在正确位置（项目根目录）
2. 检查文件名是否正确（应该是 `.env` 而不是 `env.txt`）
3. 检查是否有语法错误（每行一个变量，无空格）
4. 运行 `python test_config.py` 验证

### 问题2：python-dotenv 未安装

**症状：** `ModuleNotFoundError: No module named 'dotenv'`

**解决方案：**
```bash
pip install python-dotenv
```

### 问题3：特殊字符导致解析错误

**症状：** 密码包含 `@`、`#` 等特殊字符时出错

**解决方案：**
用引号包裹值：
```env
DB_PASSWORD="p@ssw0rd#123"
AUTH_SECRET_KEY="key-with-special-chars"
```

### 问题4：配置被缓存

**症状：** 修改 `.env` 后配置未更新

**解决方案：**
重启应用服务器，Python 在启动时加载配置。

---

## 📚 相关文档

- [python-dotenv 官方文档](https://github.com/theskumar/python-dotenv)
- [FastAPI 配置最佳实践](https://fastapi.tiangolo.com/advanced/settings/)
- [12-Factor App - Config](https://12factor.net/config)

---

## 🔗 相关文件

- `.env` - 环境变量配置（不提交到Git）
- `.env.example` - 配置模板（可提交）
- `.gitignore` - Git忽略规则
- `analysis_agent_system/app/config.py` - 配置加载模块
- `requirements.txt` - Python依赖列表
- `test_config.py` - 配置验证脚本
