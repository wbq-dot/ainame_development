# 专家服务运维

专家订单仅以支付宝服务器发送到 `/expert-pay/notify` 的异步通知作为到账依据。
`/expert-pay/return` 是浏览器同步回跳地址，只负责验签和展示提示，不会修改订单状态。
用户返回知名台后可在专家订单页面查询最新支付状态。

迁移命令必须由管理员主动执行，应用启动不会自动建表：

```powershell
conda run -n fastapi-env python -m alembic -c alembic.ini upgrade head
```

迁移会创建专家资料、专家套餐、专家订单、交付报告、评价、收入与结算申请七张表，不会回填或删除现有业务数据。
