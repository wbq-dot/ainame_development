# 知名台 UniApp 前端

这是根据 `projectback/wbq_ainame` 现有接口制作的 Vue 3 UniApp 最小联调版本。

## 在 HBuilderX 中运行

1. 启动后端，并确认 FastAPI 运行在 `http://127.0.0.1:8000`。
2. 启动 RabbitMQ、Redis、业务数据库和 LangGraph 使用的 PostgreSQL；测试知识库时还要运行 `rag_worker.py` 与 Ollama。
3. 打开 HBuilderX，选择“文件 → 导入 → 从本地目录导入”，选择整个 `projectfront` 目录。
4. 选择“运行 → 运行到浏览器 → Chrome”。
5. 首页右上角显示“服务正常”后，即可点击业务页面测试。
6. 首页右上角会自动检查后端状态；显示“服务正常”后即可进入各业务页面测试。

## 服务地址

- 浏览器在同一台电脑测试：使用 `http://127.0.0.1:8000`。
- 手机真机测试：在“我的”页面把服务地址改成电脑局域网地址，例如 `http://192.168.1.20:8000`；后端 Uvicorn 还需监听 `0.0.0.0`。

## 后端新增可选环境变量

```dotenv
# 额外允许的 H5 来源，多个地址用英文逗号分隔
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# 最大上传大小，默认 10MB，单位为字节
MAX_UPLOAD_SIZE=10485760

# 默认关闭；仅本地排错时开启 SQL 输出
SQL_ECHO=false

# 知识库向量模型
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:4b

# Ollama 本地服务地址
OLLAMA_BASE_URL=http://127.0.0.1:11434

# 知识库首次检索和精简词降级检索门槛
RAG_PRIMARY_MIN_SCORE=0.65
RAG_FALLBACK_MIN_SCORE=0.55

# 每次最多取回的知识文本块数量
RAG_TOP_K=3

# 支付可靠性与退款
PAYMENT_ENABLED=true
ALIPAY_ENVIRONMENT=sandbox
ALIPAY_SELLER_ID=沙箱或生产商户PID
PAYMENT_FRONTEND_RESULT_URL=http://127.0.0.1:8080/#/pages/payment/result
PAYMENT_ORDER_TIMEOUT_MINUTES=60
PAYMENT_RECONCILE_INTERVAL_SECONDS=30
PAYMENT_RECONCILE_BATCH_SIZE=50
REFUND_WINDOW_HOURS=24
```

安全提醒：请手动更换后端 `.env` 中的 `JWT_SECRET_KEY`，使旧测试文件中泄露过的令牌立即失效。不要把真实密码、JWT 或 API 密钥再次写入 `.http` 文件。
