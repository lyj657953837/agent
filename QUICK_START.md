# 配置快速参考

## 🚀 快速开始

```bash
# 1. 复制模板
cp .env.example .env

# 2. 编辑配置（至少修改以下项）
# DB_PASSWORD=your-password
# VLLM_API_BASE=http://your-llm-server:8080/v1

# 3. 验证配置
python test_config.py

# 4. 启动应用
python run_server.py
```

---

## 🔑 必填配置项

| 变量 | 说明 | 示例 |
|------|------|------|
| `DB_PASSWORD` | 数据库密码 | `DB_PASSWORD=my-secret-pass` |
| `VLLM_API_BASE` | LLM API 地址 | `VLLM_API_BASE=http://server:8080/v1` |
| `MODEL_NAME` | 模型名称 | `MODEL_NAME=qwen3-vl-8b-instruct` |

---

## ⚙️ 常用配置

### 开发环境
```env
APP_DEBUG=true
DB_HOST=localhost
VLLM_API_BASE=http://localhost:8080/v1
```

### 生产环境
```env
APP_DEBUG=false
DB_HOST=prod-db.example.com
AUTH_SECRET_KEY=<strong-random-key>
VLLM_API_BASE=https://llm.example.com/v1
```

---

## 🛠️ 故障排查

```bash
# 检查配置加载
python test_config.py

# 查看当前环境变量
python -c "import os; print(os.getenv('DB_PASSWORD', 'NOT SET'))"

# 测试数据库连接
python -c "from analysis_agent_system.app.config import settings; print(settings.DATABASE_URL)"
```

---

## 📖 详细文档

- [完整配置指南](./docs/ENVIRONMENT_CONFIG.md)
- [迁移说明](./docs/CONFIG_MIGRATION.md)
- [配置模板](./.env.example)
