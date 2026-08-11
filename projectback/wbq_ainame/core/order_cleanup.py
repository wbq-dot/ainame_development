"""兼容旧导入；过期订单现在由支付对账任务关闭，不再删除。"""

from core.payment_service import payment_reconciliation_loop


cleanup_expired_orders_loop = payment_reconciliation_loop
