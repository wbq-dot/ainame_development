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
# 业务数据库
DB_URI=********

# 邮件服务
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

# Redis
REDIS_URL=********

# 登录认证
JWT_SECRET_KEY=********

# 首任管理员网页初始化部署密钥；要求至少32个字符
ADMIN_BOOTSTRAP_SECRET=********

# DeepSeek 模型接口
DEEP_SEEKER_API_KEY=********

# 支付宝
ALIPAY_APP_ID=********
ALIPAY_GATEWAY=********
ALIPAY_NOTIFY_URL=********
ALIPAY_RETURN_URL=********
ALIPAY_APP_PRIVATE_KEY=********
ALIPAY_PUBLIC_KEY=********

# 本地目录
CHROMDB_PATH=********
UPLOAD_FOLDER=********

# PostgreSQL 和 RabbitMQ
POST_GRESQL_DB=********
RABBITMQ_URL=********

# 阿里云百炼 / 通义万相
DASHSCOPE_API_KEY=********
DASHSCOPE_BASE_URL=********
WANXIANG_MODEL=********

# 后端公开访问地址，例如本机开发地址 http://127.0.0.1:8000
APP_BASE_URL=********
```

### 配置项用途

| 配置项 | 用途 |
| --- | --- |
| `DB_URI` | 业务数据库连接地址 |
| `MAIL_*` | 发件账号、服务器、端口和加密方式 |
| `USE_CREDENTIALS`、`VALIDATE_CERTS` | 邮件登录和证书校验开关 |
| `REDIS_URL` | Redis 连接地址 |
| `JWT_SECRET_KEY` | 登录令牌签名密钥；生产环境必须使用足够长的随机值 |
| `ADMIN_BOOTSTRAP_SECRET` | 首任管理员网页初始化密钥；不配置时初始化入口关闭，创建成功后接口不再允许初始化 |
| `DEEP_SEEKER_API_KEY` | DeepSeek 模型接口密钥 |
| `ALIPAY_*` | 支付宝应用、网关、回调地址和签名密钥 |
| `CHROMDB_PATH` | Chroma 向量数据库的本地保存目录 |
| `UPLOAD_FOLDER` | 上传文件的本地保存目录 |
| `POST_GRESQL_DB` | PostgreSQL 连接地址，供工作流等功能使用 |
| `RABBITMQ_URL` | RabbitMQ 消息队列连接地址 |
| `DASHSCOPE_API_KEY` | 阿里云百炼 API Key |
| `DASHSCOPE_BASE_URL` | 阿里云百炼接口基础地址 |
| `WANXIANG_MODEL` | 通义万相模型名称 |
| `APP_BASE_URL` | 用户或外部服务可访问的后端基础地址 |

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
