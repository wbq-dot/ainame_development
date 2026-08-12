# 智能起名开放平台 API v1

## 认证与安全

在开发者控制台创建 API Key。明文只显示一次，请放入服务端环境变量，不要提交到前端代码或 Git。

每个请求携带：

```http
X-API-Key: zn_live_xxx
```

收费 POST 请求还必须提供唯一的 `Idempotency-Key`。同一业务请求重试时使用原值；不同业务请求必须换新值。相同键对应不同请求体会返回 `409`。每个 Key 默认每分钟最多 60 次，超限返回 `429`；限速服务不可用时返回 `503`。

## 单次命名

```bash
curl -X POST "http://127.0.0.1:8000/openapi/v1/names/generate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: zn_live_xxx" \
  -H "Idempotency-Key: customer-order-20260812-001" \
  -d '{"category":"人名","surname":"张","gender":"女","length":"两字","other":"温柔大方","exclude":[]}'
```

成功生成扣 1 次，模型或知识服务失败不扣费。开放平台调用不会读取普通用户的私人知识库。

## 批量命名

`POST /openapi/v1/batches` 接受 `items` 数组，单批 1 至 100 条并返回 `202` 与 `task_id`。查询和导出：

```text
GET /openapi/v1/batches/{task_id}
GET /openapi/v1/batches/{task_id}/export
```

提交时预占总次数，成功条目结算，失败条目自动退回；任务重试不会重复扣成功条目。

## 常见错误

- `401`：API Key 无效、已吊销或账号被冻结。
- `402`：API 次数不足。
- `409`：幂等键冲突或相同请求仍在处理中。
- `429`：超过每分钟调用上限。
- `502/503`：模型、知识检索或限速服务暂不可用；失败调用不扣次数。

完整字段、校验规则和响应结构可在 FastAPI `/docs` 查看。
