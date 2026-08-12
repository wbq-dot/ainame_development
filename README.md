# 知名台 AI 起名项目

知名台是一个前后端一体的 AI 起名服务。后端使用 FastAPI，前端使用 Vue 3 + UniApp，当前包含用户认证、AI 起名、专属知识库、Logo 生成、套餐与次数、支付宝支付退款、账户安全、专家起名服务和管理后台。

## 主要功能

- 邮箱验证码注册、JWT 登录与令牌刷新
- 人名、企业名、宠物名等 AI 起名及结果反馈
- PDF、TXT 专属知识库与本地向量检索
- 通义万相 Logo 生成
- 平台套餐、使用次数、订单、支付宝支付和退款
- 修改密码、换绑邮箱、注销账户及延迟数据清理
- 专家入驻、套餐审核、专家订单、交付、评价、争议和结算
- 用户、套餐、退款及专家业务管理后台

## 技术组成

- 后端：FastAPI、SQLAlchemy、Alembic、Pydantic
- 前端：Vue 3、UniApp、HBuilderX
- 业务数据库：MySQL（异步 SQLAlchemy）
- 工作流记忆：PostgreSQL、LangGraph Checkpoint
- 缓存与验证码：Redis
- 异步任务：RabbitMQ
- 本地知识库：Chroma、Ollama
- 模型服务：DeepSeek、阿里云百炼/通义万相
- 支付：支付宝开放平台

## 目录说明

```text
ainame_development/
├─ projectback/
│  └─ wbq_ainame/                    # FastAPI 后端应用
│     ├─ main.py                    # 应用入口、中间件、路由和后台任务
│     ├─ settings/                  # 环境变量读取与全局配置
│     ├─ dependencies.py            # 数据库会话等 FastAPI 依赖
│     ├─ routers/                   # 认证、账户、起名、Logo、支付、专家等 API
│     ├─ schemas/                   # Pydantic 请求与响应模型
│     ├─ models/                    # SQLAlchemy 数据库模型
│     ├─ repository/                # 数据访问层
│     ├─ core/                      # 起名、Logo、RAG、支付和账户等核心业务
│     ├─ alembictable/              # 业务数据库 Alembic 迁移
│     ├─ scripts/                   # 管理员、数据清理和数据库检查工具
│     ├─ tests/                     # unittest 测试，也可通过 pytest 运行
│     ├─ docs/                      # 后端专项说明
│     ├─ backups/                   # 运维清理记录和清单
│     ├─ static/logos/              # 运行时生成的 Logo 静态文件
│     ├─ private_storage/expert/    # 专家资质和交付文件的私有存储
│     ├─ rag_worker.py              # 知识库 RabbitMQ 消费进程
│     ├─ init_pg_memory.py          # LangGraph PostgreSQL 检查点表初始化
│     ├─ backfill_total_recharge.py # 历史充值数据回填工具
│     ├─ manage_expert_demo_users.py # 专家演示账号管理工具
│     ├─ alembic.ini                # Alembic 配置
│     ├─ .env.example              # 可提交的后端配置模板
│     └─ .env                       # 后端本地配置，不提交
├─ projectfront/                         # Vue 3 + UniApp 前端
│  ├─ pages/                        # 业务页面和管理端页面
│  ├─ components/                   # 可复用 Vue 组件
│  ├─ api/                          # 后端 API 封装
│  ├─ utils/                        # 请求、认证、配置和本地数据工具
│  ├─ scripts/                      # 前端源码检查脚本
│  ├─ App.vue / main.js             # 根组件与应用入口
│  ├─ pages.json                    # 页面路由和底部导航
│  ├─ manifest.json                 # UniApp 应用配置
│  ├─ package.json                  # 前端项目元数据
│  └─ unpackage/                    # HBuilderX 构建缓存和输出，不要手动编辑
├─ requirements.txt                      # pip 依赖清单
├─ environment.yml                       # Conda 环境清单
├─ todo_list.txt                         # 项目待办记录
└─ README.md                             # 项目说明
```

`.env`、上传文件、Chroma 本地数据、专家私有文件和前端构建结果不应作为日常源码修改。

## 运行前准备

建议准备：

- Git
- Python 3.13
- pip
- Conda（可选，仓库已提供 `environment.yml`）
- HBuilderX（运行 UniApp 前端）
- Node.js（仅运行前端源码检查脚本时需要）
- MySQL 业务数据库
- PostgreSQL、Redis 和 RabbitMQ
- Ollama（使用专属知识库时需要）

### 功能与外部服务

| 功能 | 需要的服务或配置 |
| --- | --- |
| FastAPI 启动与基础业务 | MySQL `DB_URI`、PostgreSQL `POST_GRESQL_DB` |
| 注册验证码、换绑邮箱 | Redis、SMTP 邮件配置 |
| AI 起名 | DeepSeek API、PostgreSQL 工作流记忆 |
| 知识库上传和处理 | MySQL、RabbitMQ、`rag_worker.py`、Ollama、Chroma |
| Logo 生成 | 阿里云百炼 API |
| 支付和退款 | 支付宝配置；不使用时设置 `PAYMENT_ENABLED=false` |

## 获取代码

```bash
git clone <仓库地址>
cd ainame_development
git switch main
```

## 安装 Python 环境

以下两种方式任选一种。

### 方式一：Conda

在仓库根目录执行：

```bash
conda env create -f environment.yml
conda activate fastapi-env
python --version
python -m pip --version
```

更新已有环境：

```bash
conda env update -n fastapi-env -f environment.yml --prune
```

`environment.yml` 已包含 pip 依赖，不需要再重复安装 `requirements.txt`。

### 方式二：venv

Windows PowerShell：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows CMD：

```bat
py -3.13 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

macOS / Linux：

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

安装完成后可执行：

```bash
python -m pip check
python -m pip show fastapi uvicorn sqlalchemy
```

## 配置后端 `.env`

先将 `projectback/wbq_ainame/.env.example` 复制为 `projectback/wbq_ainame/.env`，再填写当前环境的真实值。

Windows PowerShell：

```powershell
Copy-Item projectback/wbq_ainame/.env.example projectback/wbq_ainame/.env
```

macOS / Linux：

```bash
cp projectback/wbq_ainame/.env.example projectback/wbq_ainame/.env
```

下面列出代码支持的配置项；带默认值的调优项通常无需修改。

> `.env` 已被 `.gitignore` 排除。不要将真实密码、JWT 密钥、支付私钥或 API Key 写入 README、提交记录或聊天消息。

### 基础配置

```dotenv
# MySQL 业务数据库
DB_URI=mysql+aiomysql://USER:PASSWORD@127.0.0.1:3306/DB_NAME

# LangGraph 检查点 PostgreSQL
POST_GRESQL_DB=postgresql://USER:PASSWORD@127.0.0.1:5432/DB_NAME

# 生产环境必须替换为足够长的随机值
JWT_SECRET_KEY=REPLACE_WITH_A_LONG_RANDOM_SECRET

# 首任管理员网页初始化密钥，至少 32 个字符；不需要时留空
ADMIN_BOOTSTRAP_SECRET=

REDIS_URL=redis://127.0.0.1:6379/0
APP_BASE_URL=http://127.0.0.1:8000

# 是否在终端输出执行的 SQL 语句(适合本地排查数据库问题)
SQL_ECHO=false

# 知识库上传的 PDF、TXT 文件大小，单位: 字节
MAX_UPLOAD_SIZE=20971520
```

`CORS_ORIGINS` 默认包含本机 `5173` 和 `8080` 端口，`CORS_ORIGIN_REGEX` 默认额外允许本机及常见局域网地址。部署到其他域名时可覆盖：

```dotenv
CORS_ORIGINS=https://your-frontend.example.com
# CORS_ORIGIN_REGEX=^自定义正则表达式$
```

### 邮件服务

注册验证码和换绑邮箱时需要：

```dotenv
MAIL_USERNAME=********
MAIL_PASSWORD=********
MAIL_FROM=********
MAIL_PORT=********
MAIL_SERVER=********
MAIL_FROM_NAME=知名台
MAIL_STARTTLS=true
MAIL_SSL_TLS=false
USE_CREDENTIALS=true
VALIDATE_CERTS=true
```

### 模型服务

```dotenv
# AI 起名
DEEP_SEEKER_API_KEY=********

# Logo 生成
DASHSCOPE_API_KEY=********
DASHSCOPE_BASE_URL=********
WANXIANG_MODEL=wan2.6-t2i
```

### 知识库

```dotenv
RABBITMQ_URL=amqp://USER:PASSWORD@127.0.0.1:5672/

# 以下是可选覆盖；相对路径会以后端目录为基准
# CHROMDB_PATH=chroma_rag_db
# UPLOAD_FOLDER=D:/data/ainame/uploads

OLLAMA_EMBEDDING_MODEL=qwen3-embedding:4b
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_REQUEST_TIMEOUT=180
RAG_EMBED_BATCH_SIZE=8
RAG_EMBED_MAX_ATTEMPTS=4
RAG_EMBED_RETRY_DELAY=3
RAG_TOP_K=3

# 默认不使用固定分数门槛；仅在已按当前向量模型校准后设置
# RAG_PRIMARY_MIN_SCORE=0.65
# RAG_FALLBACK_MIN_SCORE=0.55
```

### 支付与退款

不测试支付时至少明确设置 `PAYMENT_ENABLED=false`。启用后需要填写同一套沙箱或生产环境参数，不要混用。

```dotenv
PAYMENT_ENABLED=false
ALIPAY_ENVIRONMENT=sandbox
ALIPAY_APP_ID=********
ALIPAY_SELLER_ID=********
ALIPAY_GATEWAY=
ALIPAY_NOTIFY_URL=https://your-backend.example.com/pay/paySuccess
ALIPAY_RETURN_URL=https://your-backend.example.com/pay/success
ALIPAY_APP_PRIVATE_KEY=********
ALIPAY_PUBLIC_KEY=********

PAYMENT_FRONTEND_RESULT_URL=http://127.0.0.1:8080/#/pages/payment/result
PAYMENT_ORDER_TIMEOUT_MINUTES=60
PAYMENT_RECONCILE_INTERVAL_SECONDS=30
PAYMENT_RECONCILE_BATCH_SIZE=50
REFUND_WINDOW_HOURS=24

# 可选；不填时会根据普通支付回调地址推导
EXPERT_ALIPAY_NOTIFY_URL=
EXPERT_ALIPAY_RETURN_URL=
```

支付宝异步通知 `/pay/paySuccess` 是普通订单入账依据；`/pay/success` 只验签并跳转前端结果页。生产环境建议使用可公网访问的 HTTPS 地址。

### 后台任务与私有存储

以下配置都有默认值，仅在需要调整运维节奏或存储位置时设置：

```dotenv
ACCOUNT_CLEANUP_INTERVAL_SECONDS=60
ACCOUNT_CLEANUP_BATCH_SIZE=10
ORDER_CLEANUP_INTERVAL_SECONDS=300

# 留空不要显式写入；默认为 projectback/wbq_ainame/private_storage/expert
# EXPERT_PRIVATE_STORAGE_DIR=D:/data/ainame/expert-private
```

## 初始化数据库

先确认 `.env` 中的 `DB_URI` 和 `POST_GRESQL_DB` 均可用，再进入后端目录：

```bash
cd projectback/wbq_ainame
```

### 1. 迁移 MySQL 业务表

```bash
python -m alembic upgrade head
```

### 2. 初始化 LangGraph PostgreSQL 检查点表

```bash
python init_pg_memory.py
```

`init_pg_memory.py` 会调用 LangGraph Checkpoint 的 `setup()` 创建所需表。

## 启动项目

### 启动后端

在 `projectback/wbq_ainame` 目录执行：

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

启动后访问：

- 连通性检查：`http://127.0.0.1:8000/`
- Swagger 接口文档：`http://127.0.0.1:8000/docs`
- ReDoc 接口文档：`http://127.0.0.1:8000/redoc`

如果需要手机真机访问，将 `--host 127.0.0.1` 改为 `--host 0.0.0.0`，并在前端填写电脑的局域网 IP。

### 启动知识库 Worker

保持后端运行，再打开一个已激活同一 Python 环境的终端：

```bash
cd projectback/wbq_ainame
python rag_worker.py
```

只测试非知识库功能时可以不启动 Worker。没有 Worker 时上传任务可以进入 RabbitMQ，但不会被消费和向量化。

### 启动前端

`projectfront/package.json` 当前没有 npm 启动脚本，请使用 HBuilderX：

1. 选择“文件 → 导入 → 从本地目录导入”。
2. 选择仓库中的 `projectfront` 目录。
3. 选择“运行 → 运行到浏览器 → Chrome”。
4. 本机联调使用 `http://127.0.0.1:8000`；真机联调在“我的”页面改为电脑局域网地址。

更详细的前端说明见 [projectfront/README.md](projectfront/README.md)。

## 测试与检查

### 后端方案一：unittest

项目测试用例基于 Python 标准库 `unittest`，无需额外安装测试框架：

```bash
cd projectback/wbq_ainame
python -m unittest discover -s tests -p "test_*.py" -v
```

### 后端方案二：pytest

Pytest 可以直接收集并运行现有 `unittest` 用例。`pytest` 当前不在项目依赖清单中，首次使用时单独安装：

```bash
python -m pip install pytest
cd projectback/wbq_ainame
python -m pytest tests -q
```

### 前端源码检查

前端检查脚本会验证 `pages.json` 路由、Vue 页面存在性、模板标签和 JavaScript 语法：

```bash
cd projectfront
node --experimental-vm-modules scripts/check_sfc.mjs
```

## 后端运维工具

在 `projectback/wbq_ainame` 目录中运行：

```bash
python -m scripts.manage_admin --help
python -m scripts.cleanup_expert_data --help
python -m scripts.check_db
```

专家服务的迁移、支付回调、私有存储和清理流程见 [专家服务运维](projectback/wbq_ainame/docs/expert_service.md)。

## 常见问题

### 后端启动失败

依次检查：

1. 当前终端是否位于 `projectback/wbq_ainame`。
2. `.env` 是否存在，`DB_URI`、`POST_GRESQL_DB` 和 `JWT_SECRET_KEY` 是否正确。
3. MySQL 和 PostgreSQL 是否已启动，两组表是否已初始化。
4. 如果仅特定接口失败，再按“功能与外部服务”检查 Redis、RabbitMQ、Ollama、邮件或模型服务。

### 前端显示“服务未连接”

1. 确认 `http://127.0.0.1:8000/` 可以访问。
2. 真机调试时不要使用手机自身的 `127.0.0.1`，应改为电脑局域网 IP。
3. 确认 Uvicorn 监听 `0.0.0.0`，并检查防火墙和 CORS 配置。

### 提交前检查敏感信息

```bash
git status --short
git check-ignore -v projectback/wbq_ainame/.env
```

第二条命令应显示 `.env` 被 `.gitignore` 排除。提交前请再次确认变更中没有密码、令牌、私钥、客户资料或专家私有文件。
