<template>
  <view class="result-page">
    <view class="result-card">
      <view class="result-icon" :class="resultClass">{{ resultIcon }}</view>
      <view class="title">{{ title }}</view>
      <view class="message">{{ message }}</view>
      <view v-if="order" class="order-box"><text>订单号</text><b>{{ order.order_no }}</b><text>当前状态</text><b>{{ statusText(order.status) }}</b></view>
      <button v-if="canRefresh" :loading="loading" @click="refresh">重新查询</button>
      <button class="secondary" @click="goOrders">查看全部订单</button>
    </view>
  </view>
</template>

<script>
import { api } from '../../api'
import { isLoggedIn } from '../../utils/auth'

export default {
  data() { return { orderNo: '', verified: true, order: null, loading: false, attempts: 0, timer: null, title: '正在确认支付结果', message: '请稍候，系统正在等待支付宝异步通知或主动查单。' } },
  computed: {
    resultClass() { if (!this.verified || (this.order && this.order.status === 'closed')) return 'error'; if (this.order && ['paid', 'refunded'].includes(this.order.status)) return 'success'; return 'waiting' },
    resultIcon() { return this.resultClass === 'success' ? '✓' : this.resultClass === 'error' ? '!' : '…' },
    canRefresh() { return Boolean(this.orderNo && this.verified) }
  },
  onLoad(options) {
    this.orderNo = options.order_no || ''
    this.verified = String(options.verified || '1') === '1'
    if (!this.verified || !this.orderNo) { this.title = '支付回跳验签失败'; this.message = '请不要依据当前页面判断是否到账，返回订单列表重新查询。'; return }
    if (!isLoggedIn()) { this.title = '请先登录'; this.message = '登录后可安全查询本人订单状态。'; return }
    this.refresh()
    this.timer = setInterval(() => { if (this.attempts < 45 && this.shouldPoll()) this.refresh(); else this.stopPolling() }, 2000)
  },
  onUnload() { this.stopPolling() },
  methods: {
    shouldPoll() { return !this.order || ['pending', 'refunding'].includes(this.order.status) },
    stopPolling() { if (this.timer) clearInterval(this.timer); this.timer = null },
    async refresh() {
      if (this.loading) return
      this.loading = true; this.attempts += 1
      try {
        this.order = await api.getOrder(this.orderNo)
        const status = this.order.status
        if (status === 'paid') { this.title = '支付成功'; this.message = `已到账 ${this.order.credit_count} 次${this.order.credit_type === 'logo' ? 'Logo' : '起名'}权益。`; this.stopPolling(); await api.getBalance() }
        else if (status === 'closed') { this.title = '订单已关闭'; this.message = '支付宝未确认收款，本订单不会发放次数。'; this.stopPolling() }
        else if (status === 'refunded') { this.title = '款项已退回'; this.message = '该笔超时付款或退款申请已完成原路退回。'; this.stopPolling() }
        else if (status === 'refunding') { this.title = '正在退款'; this.message = '系统已确认超时付款，未发放次数，正在原路退款。' }
      } catch (error) { this.message = error.message }
      finally { this.loading = false }
    },
    statusText(status) { return { pending: '待确认', paid: '已支付', closed: '已关闭', refunding: '退款中', refunded: '已退款' }[status] || status },
    goOrders() { uni.redirectTo({ url: '/pages/orders/index' }) }
  }
}
</script>

<style scoped>
.result-page{min-height:100vh;padding:90rpx 34rpx;background:radial-gradient(circle at 50% 0,#ebe8ff,transparent 40%),#f5f7fb}.result-card{padding:50rpx 34rpx;background:#fff;border-radius:32rpx;box-shadow:0 20rpx 55rpx rgba(46,48,95,.12);text-align:center}.result-icon{display:flex;align-items:center;justify-content:center;width:100rpx;height:100rpx;margin:0 auto;color:#fff;background:#7369df;border-radius:50%;font-size:45rpx;font-weight:900}.result-icon.success{background:#34a876}.result-icon.error{background:#d75a6d}.title{margin-top:28rpx;font-size:38rpx;font-weight:850}.message{margin-top:14rpx;color:#788194;font-size:23rpx;line-height:1.65}.order-box{display:grid;grid-template-columns:auto 1fr;gap:12rpx 18rpx;margin-top:28rpx;padding:23rpx;background:#f5f6fa;border-radius:19rpx;text-align:left}.order-box text{color:#969dac;font-size:19rpx}.order-box b{overflow:hidden;color:#34394b;font-size:20rpx;text-overflow:ellipsis;white-space:nowrap}.result-card button{height:74rpx;margin-top:28rpx;color:#fff;background:#6257e8;border-radius:18rpx;font-size:23rpx;line-height:74rpx}.result-card .secondary{margin-top:14rpx;color:#6257e8;background:#eeecff}
</style>
