# 知名台 UniApp 前端

该目录是知名台的 Vue 3 + UniApp 前端，与 `projectback/wbq_ainame` FastAPI 接口联调。当前已包含起名、Logo、知识库、账户与支付、专家服务和管理后台等页面。

## 目录结构

```text
projectfront/
├─ pages/              # 页面源码
│  ├─ index/         # 首页
│  ├─ auth/          # 登录与注册
│  ├─ naming/        # AI 起名
│  ├─ knowledge/     # 专属知识库
│  ├─ logo/          # Logo 生成
│  ├─ account/       # 账户、套餐与次数
│  ├─ orders/        # 订单与退款
│  ├─ payment/       # 支付结果
│  ├─ security/      # 账号安全
│  ├─ expert/        # 专家入驻、下单和工作台
│  └─ admin/         # 管理后台
├─ components/         # 可复用组件
├─ api/index.js        # 后端 API 统一封装
├─ utils/              # 请求、令牌、服务地址和本地偏好
├─ scripts/            # 前端源码检查脚本
├─ pages.json          # 页面路由和 tabBar
├─ manifest.json       # UniApp 应用配置
├─ App.vue             # 根组件
├─ main.js             # 应用入口
└─ unpackage/          # HBuilderX 构建缓存和输出
```

`unpackage/` 中的内容由 HBuilderX 生成，不要手动编辑其中代码。

## 运行前提

1. 按仓库根目录 [README](../README.md) 完成 Python 环境、`.env` 和数据库初始化。
2. 启动 FastAPI，并确认 `http://127.0.0.1:8000/` 可访问。
3. 按待测功能启动 Redis、RabbitMQ、Ollama 或其他外部服务。
4. 测试知识库上传时，另外启动 `python rag_worker.py`。

后端环境变量统一在根 README 中维护，本文不再复制，避免两份配置说明不同步。

## 在 HBuilderX 中运行

`package.json` 当前没有 npm 启动脚本，请使用 HBuilderX 运行：

1. 打开 HBuilderX。
2. 选择“文件 → 导入 → 从本地目录导入”。
3. 选择整个 `projectfront` 目录。
4. 选择“运行 → 运行到浏览器 → Chrome”。
5. 首页右上角显示“服务正常”后，即可进入各业务页面。

## 后端服务地址

前端默认访问：

```text
http://127.0.0.1:8000
```

- 同一台电脑的 H5 联调可保持默认值。
- 手机真机调试时，在“我的”页面将服务地址改为电脑的局域网地址，例如 `http://192.168.1.20:8000`。
- 真机调试时 Uvicorn 必须监听 `0.0.0.0`，手机和电脑需位于可互访的网络。
- 输入地址时必须保留 `http://` 或 `https://`，末尾的 `/` 会自动去除。

## 页面与业务范围

| 区域 | 主要内容 |
| --- | --- |
| 普通用户 | 登录注册、AI 起名、Logo、知识库、套餐次数、订单退款、账号安全 |
| 专家服务 | 专家列表、资料详情、入驻、专家订单和专家工作台 |
| 管理后台 | 管理员初始化、用户、套餐、退款、专家资质、专家套餐、争议订单和结算 |

实际页面注册以 `pages.json` 为准，后端请求封装集中在 `api/index.js`。

## 前端源码检查

运行检查需要 Node.js，不需要安装 npm 依赖：

```bash
cd projectfront
node --experimental-vm-modules scripts/check_sfc.mjs
```

该脚本会检查：

- `pages.json` 中是否有重复路由
- 每条路由是否存在对应 `.vue` 文件
- 页面是否包含 `template` 和 `script`
- 模板标签是否匹配
- JavaScript 是否存在基础语法错误

## 常见问题

### 首页显示“服务未连接”

1. 在浏览器直接访问当前服务地址的 `/` 路径。
2. 确认 FastAPI 启动端口为 `8000`。
3. 真机不能使用 `127.0.0.1`，应使用电脑局域网 IP。
4. 检查 Windows 防火墙、网络隔离和后端 CORS 配置。

### 某个功能页失败，但首页显示服务正常

首页只检查 FastAPI 的 `/` 路径，不会检查所有外部服务。请根据功能检查 MySQL、PostgreSQL、Redis、RabbitMQ、Ollama、邮件、模型或支付宝配置。

### 修改后页面没有更新

停止当前 HBuilderX 运行任务，清理构建缓存后重新运行。不要直接修改 `unpackage/` 中的生成文件。
