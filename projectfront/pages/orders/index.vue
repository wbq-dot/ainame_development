<template>
  <view class="orders-page">
    <view class="hero">
      <view class="eyebrow">PAYMENT CENTER</view>
      <view class="title">订单与退款</view>
      <view class="subtitle">订单永久保留；支付到账以支付宝异步通知或主动查单结果为准。</view>
    </view>

    <view v-if="loading && !orders.length" class="state-card">正在读取订单…</view>
    <view v-else-if="!orders.length" class="state-card">暂无订单记录</view>
    <view v-for="order in orders" :key="order.order_no" class="order-card">
      <view class="order-head">
        <view><view class="package-type">{{ creditLabel(order.credit_type) }}套餐</view><view class="order-no">{{ order.order_no }}</view></view>
        <text class="status" :class="order.status">{{ statusText(order.status) }}</text>
      </view>
      <view class="order-main"><view><small>金额</small><b>¥{{ order.amount }}</b></view><view><small>到账权益</small><b>{{ order.credit_count }} 次</b></view></view>
      <view class="time-row"><text>创建 {{ formatDate(order.created_at) }}</text><text v-if="order.paid_at">支付 {{ formatDate(order.paid_at) }}</text></view>
      <view v-if="order.latest_refund" class="refund-box">
        <view>退款 {{ refundStatusText(order.latest_refund.status) }}</view>
        <text>{{ order.latest_refund.review_note || order.latest_refund.reason }}</text>
      </view>
      <view v-if="order.refund_deadline" class="deadline">退款申请截止：{{ formatDate(order.refund_deadline) }}</view>
      <button v-if="order.refund_eligible" class="refund-btn" @click="openRefund(order)">申请整单退款</button>
      <view v-else-if="order.refund_ineligible_reason" class="disabled-reason">{{ order.refund_ineligible_reason }}</view>
    </view>
    <button v-if="orders.length < total" class="load-more" :loading="loading" @click="loadMore">加载更多</button>

    <view v-if="refundVisible" class="modal-mask" @click.self="closeRefund">
      <view class="refund-modal">
        <view class="modal-title">申请整单退款</view>
        <view class="modal-order">{{ selectedOrder.order_no }} · ¥{{ selectedOrder.amount }}</view>
        <view class="notice">管理员审批时会再次检查{{ creditLabel(selectedOrder.credit_type) }}余额；余额不足将自动驳回。</view>
        <textarea v-model.trim="refundReason" maxlength="200" placeholder="请输入退款原因（必填）"></textarea>
        <view class="modal-actions"><button @click="closeRefund">取消</button><button class="confirm" :loading="submitting" :disabled="submitting" @click="submitRefund">提交申请</button></view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../api'
import { requireLogin } from '../../utils/auth'

export default {
  data() { return { orders: [], total: 0, page: 1, pageSize: 10, loading: false, submitting: false, refundVisible: false, selectedOrder: null, refundReason: '' } },
  onShow() { if (requireLogin()) this.loadOrders(true) },
  methods: {
    async loadOrders(reset = false) {
      if (this.loading) return
      if (reset) { this.page = 1; this.orders = [] }
      this.loading = true
      try {
        const data = await api.getOrders({ page: this.page, pageSize: this.pageSize })
        this.orders = reset ? data.items : [...this.orders, ...data.items]
        this.total = data.total
      } catch (error) { uni.showToast({ title: error.message, icon: 'none', duration: 3000 }) }
      finally { this.loading = false }
    },
    loadMore() { this.page += 1; this.loadOrders(false) },
    creditLabel(type) { return type === 'logo' ? 'Logo' : '起名' },
    statusText(status) { return { pending: '待支付', paid: '已支付', closed: '已关闭', refunding: '退款中', refunded: '已退款' }[status] || status },
    refundStatusText(status) { return { requested: '待审核', rejected: '已驳回', processing: '处理中', succeeded: '已完成', failed: '失败' }[status] || status },
    formatDate(value) { return value ? String(value).replace('T', ' ').slice(0, 16) : '—' },
    openRefund(order) { this.selectedOrder = order; this.refundReason = ''; this.refundVisible = true },
    closeRefund() { if (this.submitting) return; this.refundVisible = false; this.selectedOrder = null; this.refundReason = '' },
    async submitRefund() {
      if (!this.refundReason) { uni.showToast({ title: '请输入退款原因', icon: 'none' }); return }
      this.submitting = true
      try {
        await api.requestRefund(this.selectedOrder.order_no, this.refundReason)
        uni.showToast({ title: '退款申请已提交', icon: 'success' })
        this.refundVisible = false
        await this.loadOrders(true)
      } catch (error) { uni.showToast({ title: error.message, icon: 'none', duration: 3000 }) }
      finally { this.submitting = false }
    }
  }
}
</script>

<style scoped>
.orders-page { min-height:100vh; padding:28rpx 28rpx 70rpx; background:#f4f6fa; }
.hero { padding:34rpx; color:#fff; background:linear-gradient(135deg,#302d63,#6257e8); border-radius:30rpx; box-shadow:0 18rpx 42rpx rgba(70,60,160,.2); }
.eyebrow { color:#dcd8ff; font-size:17rpx; font-weight:800; letter-spacing:4rpx; }.title{margin-top:10rpx;font-size:40rpx;font-weight:850}.subtitle{margin-top:12rpx;color:#e5e2ff;font-size:21rpx;line-height:1.55}
.state-card,.order-card{margin-top:20rpx;padding:27rpx;background:#fff;border-radius:25rpx;box-shadow:0 10rpx 30rpx rgba(36,55,86,.05)}.state-card{padding:55rpx;text-align:center;color:#929aaa}
.order-head{display:flex;align-items:flex-start;justify-content:space-between}.package-type{font-size:27rpx;font-weight:800}.order-no{margin-top:6rpx;color:#9ba2af;font-size:17rpx}.status{padding:7rpx 13rpx;border-radius:999rpx;font-size:18rpx}.status.pending{color:#96601a;background:#fff2d8}.status.paid{color:#18764c;background:#e6f7ef}.status.closed,.status.refunded{color:#7c8494;background:#eef0f4}.status.refunding{color:#5546b8;background:#eeecff}
.order-main{display:grid;grid-template-columns:1fr 1fr;margin-top:22rpx;padding:20rpx;background:#f6f7fa;border-radius:18rpx}.order-main view{text-align:center}.order-main small{display:block;color:#8f97a6;font-size:18rpx}.order-main b{display:block;margin-top:7rpx;color:#30364d;font-size:29rpx}.time-row{display:flex;flex-wrap:wrap;gap:10rpx 20rpx;margin-top:16rpx;color:#969eac;font-size:18rpx}.refund-box{margin-top:18rpx;padding:17rpx;color:#554b99;background:#f1efff;border-radius:16rpx;font-size:21rpx}.refund-box text{display:block;margin-top:5rpx;color:#7f789e;font-size:18rpx}.deadline,.disabled-reason{margin-top:16rpx;color:#8d95a5;font-size:19rpx}.refund-btn,.load-more{height:68rpx;margin-top:18rpx;color:#fff;background:#6257e8;border-radius:17rpx;font-size:22rpx;line-height:68rpx}.load-more{color:#6257e8;background:#ebe9ff}
.modal-mask{position:fixed;z-index:100;inset:0;display:flex;align-items:flex-end;padding:30rpx;background:rgba(18,22,38,.55)}.refund-modal{width:100%;padding:31rpx;background:#fff;border-radius:30rpx}.modal-title{font-size:32rpx;font-weight:850}.modal-order{margin-top:13rpx;color:#6e7789;font-size:20rpx}.notice{margin-top:18rpx;padding:16rpx;color:#785f31;background:#fff6df;border-radius:15rpx;font-size:20rpx;line-height:1.5}.refund-modal textarea{box-sizing:border-box;width:100%;height:150rpx;margin-top:18rpx;padding:18rpx;background:#f4f5f8;border-radius:16rpx;font-size:23rpx}.modal-actions{display:flex;gap:14rpx;margin-top:22rpx}.modal-actions button{flex:1;height:72rpx;margin:0;background:#eef0f4;border-radius:17rpx;font-size:23rpx;line-height:72rpx}.modal-actions .confirm{color:#fff;background:#6257e8}
</style>
