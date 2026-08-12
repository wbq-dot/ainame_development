# ainame_development

AI 起名项目，包含 FastAPI 后端和 UniApp 前端。

## 目录说明

```text
ainame_development/
├─ projectback/wbq_ainame/   # FastAPI 后端
├─ projectfront/             # UniApp 前端
├─ requirements.txt          # pip 依赖清单
└─ environment.yml           # Conda 环境清单
```

## 运行前准备

建议准备以下软件和服务：

- Git
- Python 3.13（`environment.yml` 当前使用 Python 3.13）
- pip（Python 的软件包安装工具）
- Conda，可选；用于按 `environment.yml` 创建独立环境
- HBuilderX；用于运行 UniApp 前端
- 业务数据库、PostgreSQL、Redis、RabbitMQ
- Ollama；使用本地知识库功能时需要

请先确认外部服务已启动，并准备好对应的连接地址和账号。支付、邮件和模型接口只在使用相关功能时需要配置。

## 获取代码

```bash
git clone <仓库地址>
cd ainame_development
git switch main
```

## 安装 Python 环境

以下两种方式任选一种。推荐使用 Conda，因为仓库已提供完整的 `environment.yml`。

### 方式一：使用 Conda（推荐）

在仓库根目录执行：

```bash
conda env create -f environment.yml
conda activate fastapi-env
python --version
python -m pip --version
```

`environment.yml` 已包含 pip 依赖。以后配置文件发生变化时，可更新现有环境：

```bash
conda env update -n fastapi-env -f environment.yml --prune
```

### 方式二：使用 Python venv

venv 是 Python 自带的轻量级独立环境。

Windows PowerShell：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

Windows CMD：

```bat
py -3.13 -m venv .venv
.venv\Scripts\activate.bat
python --version
```

macOS / Linux：

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python --version
```

## 安装 pip 和项目依赖

先检查 pip：

```bash
python -m pip --version
```

如果提示没有 pip，可使用 Python 自带模块安装：

```bash
python -m ensurepip --upgrade
```

升级 pip，并安装仓库锁定的依赖版本：

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

推荐始终使用 `python -m pip`，这样可以确保依赖被安装到当前已激活的 Python 环境中。

安装完成后可检查关键依赖：

```bash
python -m pip show fastapi uvicorn sqlalchemy
python -m pip check
```

## 配置 `.env`

后端会从 `projectback/wbq_ainame/.env` 读取配置。下面复制了当前 `.env` 的全部配置项，但所有值都已用 `********` 遮盖，没有包含真实密码、密钥或连接地址。

> 安全提示：仓库已通过 `.gitignore` 排除 `.env`。不要把真实的数据库密码、邮箱密码、JWT 密钥、支付密钥或模型 API Key 写进 README、提交记录或聊天消息。

在 `projectback/wbq_ainame/.env` 中填写真实值：

```dotenv
DB_URI=********

MAIL_USERNAME=********
MAIL_PASSWORD=********
MAIL_FROM=********
MAIL_PORT=********
MAIL_SERVER=********
MAIL_FROM_NAME=********
MAIL_STARTTLS=********
MAIL_SSL_TLS=********
USE_CREDENTIALS=********
VALIDATE_CERTS=********

REDIS_URL=********

JWT_SECRET_KEY=********
ADMIN_BOOTSTRAP_SECRET=********
DEEP_SEEKER_API_KEY=********

PAYMENT_ENABLED=********
ALIPAY_ENVIRONMENT=********
ALIPAY_APP_ID=********
ALIPAY_SELLER_ID=********
ALIPAY_GATEWAY=********
ALIPAY_NOTIFY_URL=********
ALIPAY_RETURN_URL=********
ALIPAY_APP_PRIVATE_KEY=********
ALIPAY_PUBLIC_KEY=********
PAYMENT_FRONTEND_RESULT_URL=********
PAYMENT_ORDER_TIMEOUT_MINUTES=********
PAYMENT_RECONCILE_INTERVAL_SECONDS=********
PAYMENT_RECONCILE_BATCH_SIZE=********
REFUND_WINDOW_HOURS=********
EXPERT_ALIPAY_NOTIFY_URL=********
EXPERT_ALIPAY_RETURN_URL=********

CHROMDB_PATH=********
UPLOAD_FOLDER=********
EXPERT_PRIVATE_STORAGE_DIR=********

POST_GRESQL_DB=********
RABBITMQ_URL=********

DASHSCOPE_API_KEY=********
DASHSCOPE_BASE_URL=********
WANXIANG_MODEL=********

APP_BASE_URL=********
```

专家模块不使用独立的 `.env`，而是复用 `DB_URI` 和上述支付宝应用配置，不需要重复配置支付密钥。三个 `EXPERT_*` 配置项仅用于覆盖支付回调地址或私有存储目录，普通部署可以不填写。

### 配置项用途

| 配置项 | 用途 |
| --- | --- |
| `DB_URI` | 业务数据库连接地址 |
| `MAIL_USERNAME` | 邮件服务登录用户名 |
| `MAIL_PASSWORD` | 邮件服务登录密码 |
| `MAIL_FROM` | 发件人邮箱地址 |
| `MAIL_PORT` | 邮件服务器端口 |
| `MAIL_SERVER` | 邮件服务器地址 |
| `MAIL_FROM_NAME` | 邮件中显示的发件人名称 |
| `MAIL_STARTTLS` | 是否使用 STARTTLS 加密连接 |
| `MAIL_SSL_TLS` | 是否直接使用 SSL/TLS 加密连接 |
| `USE_CREDENTIALS` | 是否使用用户名和密码登录邮件服务 |
| `VALIDATE_CERTS` | 是否校验邮件服务器的 TLS 证书 |
| `REDIS_URL` | Redis 连接地址 |
| `JWT_SECRET_KEY` | 登录令牌签名密钥；生产环境必须使用足够长的随机值 |
| `ADMIN_BOOTSTRAP_SECRET` | 首任管理员网页初始化部署密钥，要求至少 32 个字符；不配置时初始化入口关闭，创建成功后接口不再允许初始化 |
| `DEEP_SEEKER_API_KEY` | DeepSeek 模型接口密钥 |
| `PAYMENT_ENABLED` | 支付功能总开关。`true` 会在启动时校验支付宝配置并运行主动查单/查退任务；`false` 会停用创建支付订单和后台支付对账。建议始终明确填写，不依赖默认值 |
| `ALIPAY_ENVIRONMENT` | 支付宝运行环境，只能填写 `sandbox` 或 `production`。前者使用沙箱 SDK 模式和沙箱默认网关，后者使用正式环境；切换时必须同时更换应用号、商户 PID 和密钥等整套配置 |
| `ALIPAY_APP_ID` | 支付宝开放平台应用 ID。异步通知和同步回跳中的 `app_id` 必须与此值一致；沙箱应用和生产应用使用不同的 App ID |
| `ALIPAY_SELLER_ID` | 实际收款商户的 PID/支付宝账户 ID，通常是以 2088 开头的数字；它不是 App ID 或支付宝登录邮箱，服务商模式下应填写实际收款商户 PID |
| `ALIPAY_GATEWAY` | 可选的支付宝 API 网关覆盖地址。通常留空，由 `ALIPAY_ENVIRONMENT` 自动选择沙箱网关 `https://openapi-sandbox.dl.alipaydev.com/gateway.do` 或正式网关 `https://openapi.alipay.com/gateway.do`；仅在使用代理或支付宝明确要求特殊网关时覆盖 |
| `ALIPAY_NOTIFY_URL` | 支付宝服务器异步通知地址，是正常订单唯一的入账依据。必须是支付宝可访问的公网地址，正式环境建议使用有效 HTTPS；后端路由为 `https://你的后端域名/pay/paySuccess`，注意 `paySuccess` 中的 `S` 为大写。后端会校验 RSA2 签名、App ID、Seller ID、订单号、交易号、金额和交易状态 |
| `ALIPAY_RETURN_URL` | 支付完成后的浏览器同步回跳地址，例如 `https://你的后端域名/pay/success`。该接口只验签并跳转前端结果页，不修改订单状态或发放次数；实际到账依赖异步通知或主动查单 |
| `ALIPAY_APP_PRIVATE_KEY` | 用于签署本应用发往支付宝请求的 RSA2 应用私钥，必须严格保密。代码会自动补充 PEM 头尾，只填写密钥中间的 Base64 正文，不要包含 `BEGIN`/`END` 行 |
| `ALIPAY_PUBLIC_KEY` | 用于验证支付宝响应和回调签名的支付宝公钥；必须填写开放平台提供的“支付宝公钥”，不要误填本应用的“应用公钥” |
| `PAYMENT_FRONTEND_RESULT_URL` | 支付宝同步回跳验签后进入的 UniApp 支付结果页。本地 H5 示例为 `http://127.0.0.1:8080/#/pages/payment/result`，生产环境应替换为正式前端地址；后端会自动附加 `order_no` 和 `verified` 参数，供前端轮询订单状态 |
| `PAYMENT_ORDER_TIMEOUT_MINUTES` | 支付订单有效期，单位为分钟，默认 60，最小 1；同时用于本地 `expires_at` 和支付宝 `timeout_express`。过期待支付订单会由查单任务确认并关闭；已关闭订单若后续确认付款，将进入自动退款流程，不直接发放次数 |
| `PAYMENT_RECONCILE_INTERVAL_SECONDS` | 后台主动查单/查退任务的扫描间隔，单位为秒，默认 30，代码限制最小 10；它是任务扫描频率，不是单条失败记录的固定重试间隔，失败记录按数据库中的退避时间重试 |
| `PAYMENT_RECONCILE_BATCH_SIZE` | 每个后台进程每轮最多领取的待查订单数和待查退款数，默认 50，允许范围 1～100；多进程通过数据库行锁和租约避免同时处理同一条记录 |
| `REFUND_WINDOW_HOURS` | 用户从订单 `paid_at` 开始可提交整单退款申请的时限，单位为小时，默认 24，最小 1；该值只决定申请资格，退款仍需管理员审批，审批时会重新校验对应类型的次数余额 |
| `EXPERT_ALIPAY_NOTIFY_URL` | 可选的专家订单支付宝异步通知地址；不配置时根据 `ALIPAY_NOTIFY_URL` 的域名和反向代理前缀自动推导为 `/expert-pay/notify` |
| `EXPERT_ALIPAY_RETURN_URL` | 可选的专家订单支付宝同步回跳地址；不配置时根据 `ALIPAY_RETURN_URL` 的域名和反向代理前缀自动推导为 `/expert-pay/return` |
| `CHROMDB_PATH` | Chroma 向量数据库的本地保存目录 |
| `UPLOAD_FOLDER` | 上传文件的本地保存目录 |
| `EXPERT_PRIVATE_STORAGE_DIR` | 可选的专家资质和交付文件私有存储目录；不配置时使用 `projectback/wbq_ainame/private_storage/expert` |
| `POST_GRESQL_DB` | PostgreSQL 连接地址，供工作流等功能使用 |
| `RABBITMQ_URL` | RabbitMQ 消息队列连接地址 |
| `DASHSCOPE_API_KEY` | 阿里云百炼 API Key |
| `DASHSCOPE_BASE_URL` | 阿里云百炼接口基础地址 |
| `WANXIANG_MODEL` | 通义万相模型名称 |
| `APP_BASE_URL` | 用户或外部服务可访问的后端基础地址，例如本机开发地址 `http://127.0.0.1:8000` |

布尔开关通常填写 `true` 或 `false`。路径建议使用绝对路径；Windows 路径如遇转义问题，可使用正斜杠，例如 `D:/data/uploads`。

## 初始化数据库

确认 `.env` 中的数据库连接可用后，在后端目录执行迁移：

```bash
cd projectback/wbq_ainame
alembic upgrade head
```

如果系统找不到 `alembic` 命令，可改用：

```bash
python -m alembic upgrade head
```

## 启动后端

在 `projectback/wbq_ainame` 目录执行：

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

启动成功后访问：

- 服务检查：`http://127.0.0.1:8000/`
- 接口文档：`http://127.0.0.1:8000/docs`

如果要让同一局域网中的手机访问，将 `--host 127.0.0.1` 改为 `--host 0.0.0.0`，并在前端填写电脑的局域网 IP 地址。

## 启动知识库任务进程

知识库异步处理需要 RabbitMQ、PostgreSQL、Redis 和 Ollama。保持后端运行，再打开一个已激活相同 Python 环境的终端：

```bash
cd projectback/wbq_ainame
python rag_worker.py
```

只测试普通接口时，可先不启动该任务进程；知识库上传和处理功能将不可用。

## 后端运维与专家服务

后端运维脚本统一放在 `projectback/wbq_ainame/scripts`。进入后端目录后，以模块方式运行：

```bash
cd projectback/wbq_ainame
python -m scripts.manage_admin --help
python -m scripts.cleanup_expert_data --help
python -m scripts.check_db
```

专家服务的支付回调行为和数据库迁移说明见
[专家服务运维](projectback/wbq_ainame/docs/expert_service.md)。

## 启动前端

当前 `projectfront/package.json` 没有配置 npm 启动脚本，推荐使用 HBuilderX：

1. 打开 HBuilderX。
2. 选择“文件 → 导入 → 从本地目录导入”。
3. 选择仓库中的 `projectfront` 目录。
4. 选择“运行 → 运行到浏览器 → Chrome”。
5. 确认前端的后端地址为 `http://127.0.0.1:8000`；真机调试时改为电脑的局域网地址。

前端更详细的联调说明见 `projectfront/README.md`。

## 常用检查和故障排查

### 确认当前 Python 环境

```bash
python --version
python -m pip --version
```

两个命令显示的路径应属于同一个 Conda 或 venv 环境。

### pip 安装慢或失败

先升级 pip，再重新安装：

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

如果某个依赖安装失败，请保留完整错误信息，并确认 Python 版本与 `environment.yml` 一致。

### 后端启动时报连接错误

依次检查：

1. `.env` 文件是否位于 `projectback/wbq_ainame/.env`。
2. 数据库、PostgreSQL、Redis 和 RabbitMQ 是否已启动。
3. 连接地址、端口、用户名和密码是否正确。
4. 当前终端是否位于 `projectback/wbq_ainame`。

### 提交前检查敏感信息

```bash
git status --short
git check-ignore -v projectback/wbq_ainame/.env
```

第二条命令应显示 `.env` 被 `.gitignore` 排除。提交前请再次确认变更中没有真实密码、令牌、私钥或客户资料。
