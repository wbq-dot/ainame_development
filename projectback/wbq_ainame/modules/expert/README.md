# 专家服务模块配置

本模块复用现有 `DB_URI` 与支付宝应用配置，不复制支付密钥。

可选环境变量：

```dotenv
# 不配置时，从 ALIPAY_NOTIFY_URL 的域名和代理前缀推导
EXPERT_ALIPAY_NOTIFY_URL=https://your-api.example.com/expert-pay/notify

# 不配置时，从 ALIPAY_RETURN_URL 的域名和代理前缀推导
EXPERT_ALIPAY_RETURN_URL=https://your-api.example.com/expert-pay/return

# 不配置时使用 wbq_ainame/private_storage/expert
EXPERT_PRIVATE_STORAGE_DIR=D:/private/ainame/expert
```

迁移命令必须由管理员主动执行，应用启动不会自动建表：

```powershell
conda run -n fastapi-env python -m alembic -c alembic.ini upgrade head
```

迁移会创建专家资料、专家套餐、专家订单、交付报告、评价、收入与结算申请七张表，不会回填或删除现有业务数据。
