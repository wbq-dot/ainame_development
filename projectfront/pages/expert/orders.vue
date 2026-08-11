<template>
  <view class="page-shell orders-page">
    <view class="page-title">我的专家起名订单</view><view class="page-subtitle">查看付款、专家接单、结果交付、修改和评价进度。</view>
    <view class="filter-row"><view v-for="item in filters" :key="item.value" class="filter" :class="{active:filter===item.value}" @click="filter=item.value">{{ item.label }}</view></view>
    <view v-if="loading" class="card state">正在加载订单…</view>
    <view v-else-if="!filteredOrders.length" class="card state">暂无符合条件的专家订单</view>
    <view v-for="order in filteredOrders" :key="order.id" class="order-card">
      <view class="order-top"><view><view class="package-name">{{ order.package_name }}</view><view class="order-no">{{ order.order_no }}</view></view><view class="status" :class="order.service_status">{{ statusText(order.service_status) }}</view></view>
      <view class="expert-row"><text>{{ order.expert_name ? `接单专家：${order.expert_name}` : `${levelText(order.expert_level)}订单池` }}</text><text>¥{{ order.amount }}</text></view>
      <view class="target-name">{{ order.service_mode==='review' ? `精批名字：${order.candidate_name}` : `专家起名：${order.surname ? order.surname+'姓' : order.naming_type}` }}</view>
      <view class="summary"><text>重点：{{ order.focus }}</text><text v-if="order.birth_datetime">出生：{{ formatDate(order.birth_datetime) }}（{{ order.birth_calendar==='lunar'?'农历':'阳历' }}）</text><text v-if="order.image_count">客户图片：{{ order.image_count }} 张</text></view>
      <view class="timeline"><text v-if="order.accept_deadline">接单截止 {{ formatDate(order.accept_deadline) }}</text><text v-if="order.delivery_deadline">交付截止 {{ formatDate(order.delivery_deadline) }}</text><text v-if="order.confirm_deadline">确认截止 {{ formatDate(order.confirm_deadline) }}</text></view>
      <view v-if="order.dispute_reason" class="notice danger">争议原因：{{ order.dispute_reason }}</view><view v-if="order.admin_note" class="notice">管理员处理：{{ order.admin_note }}</view>
      <view class="actions">
        <button v-if="order.service_status==='pending_payment'" class="small-btn secondary-btn" @click="confirmPay(order)">继续支付</button><button v-if="order.service_status==='pending_payment'" class="small-btn danger-btn" @click="confirmCancel(order)">取消未付款订单</button>
        <button v-if="order.service_status==='delivered'" class="small-btn secondary-btn" @click="viewReport(order)">查看专家结果</button><button v-if="order.service_status==='delivered'&&!order.revision_used" class="small-btn ghost-btn" @click="openAction('revision',order)">申请修改</button><button v-if="order.service_status==='delivered'" class="small-btn primary-btn" @click="confirmComplete(order)">确认完成</button>
        <button v-if="['working','delivered','revision_requested'].includes(order.service_status)" class="small-btn danger-btn" @click="openAction('dispute',order)">发起争议</button><button v-if="order.service_status==='completed'" class="small-btn secondary-btn" @click="openAction('review',order)">评价服务</button>
      </view>
      <view v-if="expandedId===order.id&&report" class="report-box">
        <view class="report-version">第 {{ report.version }} 版专家结果</view>
        <template v-if="report.recommended_names"><view class="report-title">推荐名字</view><view class="recommended">{{ report.recommended_names }}</view></template>
        <view class="report-title">核心结论</view><view class="report-text">{{ report.conclusion }}</view>
        <template v-if="report.five_elements_analysis"><view class="report-title">五行与时辰分析</view><view class="report-text">{{ report.five_elements_analysis }}</view></template>
        <view class="report-title">详细分析</view><view class="report-text">{{ report.analysis }}</view><view class="report-title">使用建议</view><view class="report-text">{{ report.suggestions }}</view>
        <template v-if="report.final_reply"><view class="report-title">专家最终回复</view><view class="final-reply">{{ report.final_reply }}</view></template>
        <button v-if="report.attachment_name" class="secondary-btn btn-gap" @click="downloadReport(order)">下载 {{ report.attachment_name }}</button>
      </view>
    </view>
    <view v-if="actionVisible" class="modal-mask" @click.self="closeAction"><view class="action-sheet"><view class="sheet-title">{{ actionTitle }}</view><view v-if="actionType==='review'" class="rating-row"><view v-for="n in 5" :key="n" class="star" :class="{active:n<=rating}" @click="rating=n">★</view></view><textarea v-model.trim="actionText" class="field-textarea" maxlength="1000" :placeholder="actionPlaceholder"/><view class="sheet-buttons"><button class="ghost-btn" @click="closeAction">取消</button><button class="primary-btn" :loading="submitting" @click="submitAction">确认提交</button></view></view></view>
  </view>
</template>

<script>
import { api } from '../../api'
export default {
  data() { return { orders: [], loading: false, filter: 'all', filters: [{ label: '全部', value: 'all' }, { label: '进行中', value: 'doing' }, { label: '待确认', value: 'delivered' }, { label: '已完成', value: 'completed' }], expandedId: null, report: null, actionVisible: false, actionType: '', selected: null, actionText: '', rating: 5, submitting: false } },
  computed: { filteredOrders() { if (this.filter === 'all') return this.orders; if (this.filter === 'doing') return this.orders.filter(item => ['pending_payment','pending_acceptance','working','revision_requested','disputed'].includes(item.service_status)); return this.orders.filter(item => item.service_status === this.filter) }, actionTitle() { return { revision: '申请一次免费修改', dispute: '发起订单争议', review: '评价专家服务' }[this.actionType] || '' }, actionPlaceholder() { return this.actionType === 'review' ? '写下本次服务感受（选填）' : '请具体说明原因，至少 2 字' } },
  onShow() { this.load() },
  methods: {
    async load() { this.loading = true; try { this.orders = await api.getMyExpertOrders() } catch (error) { uni.showToast({ title: error.message, icon: 'none' }) } finally { this.loading = false } },
    levelText(v) { return { ordinary: '普通专家', renowned: '知名专家', top: '顶级专家' }[v] || '专家' },
    statusText(v) { return { pending_payment: '待付款', pending_acceptance: '等待专家接单', working: '专家起名中', delivered: '结果待确认', revision_requested: '专家修改中', disputed: '争议处理中', completed: '已完成', cancelled: '已取消' }[v] || v },
    formatDate(v) { return v ? String(v).replace('T',' ').slice(0,16) : '—' },
    confirmCancel(order) { uni.showModal({ title: '确认取消订单', content: `准确动作：关闭未付款订单 ${order.order_no}；关闭后不能恢复，不产生退款。`, confirmColor: '#d94a64', success: async ({ confirm }) => { if (confirm) { try { await api.cancelExpertOrder(order.id); await this.load() } catch (error) { uni.showToast({ title: error.message, icon: 'none' }) } } } }) },
    confirmPay(order) { uni.showModal({ title: '继续支付专家订单', content: `将生成 ${order.order_no} 的支付宝沙箱链接，金额 ¥${order.amount}；是否付款仍由你在支付宝页面确认。`, confirmText: '打开支付宝', success: async ({ confirm }) => { if (confirm) { try { const result = await api.getExpertOrderPayLink(order.id); this.openPay(result.pay_url) } catch (error) { uni.showToast({ title: error.message, icon: 'none' }) } } } }) },
    openPay(url) {
      // #ifdef H5
      window.location.href = url
      // #endif
      // #ifndef H5
      uni.setClipboardData({ data: url })
      // #endif
    },
    confirmComplete(order) { uni.showModal({ title: '确认接受专家结果', content: `订单将立即完成，专家可结算 ¥${order.expert_income}；确认后不能再申请免费修改。`, confirmText: '确认完成', success: async ({ confirm }) => { if (confirm) { try { await api.confirmExpertOrder(order.id); await this.load() } catch (error) { uni.showToast({ title: error.message, icon: 'none' }) } } } }) },
    async viewReport(order) { try { this.report = await api.getExpertReport(order.id); this.expandedId = this.expandedId === order.id ? null : order.id } catch (error) { uni.showToast({ title: error.message, icon: 'none' }) } },
    async downloadReport(order) { try { const path = await api.downloadExpertReport(order.id); uni.openDocument({ filePath: path, fileType: 'pdf', showMenu: true }) } catch (error) { uni.showToast({ title: error.message, icon: 'none' }) } },
    openAction(type, order) { this.actionType = type; this.selected = order; this.actionText = ''; this.rating = 5; this.actionVisible = true }, closeAction() { if (!this.submitting) { this.actionVisible = false; this.selected = null } },
    async submitAction() { if (this.actionType !== 'review' && this.actionText.length < 2) { uni.showToast({ title: '请填写至少 2 字的具体原因', icon: 'none' }); return } this.submitting = true; try { if (this.actionType === 'revision') await api.reviseExpertOrder(this.selected.id, this.actionText); if (this.actionType === 'dispute') await api.disputeExpertOrder(this.selected.id, this.actionText); if (this.actionType === 'review') await api.reviewExpertOrder(this.selected.id, { rating: this.rating, content: this.actionText || null }); this.actionVisible = false; await this.load(); uni.showToast({ title: '提交成功', icon: 'success' }) } catch (error) { uni.showToast({ title: error.message, icon: 'none' }) } finally { this.submitting = false } }
  }
}
</script>

<style scoped>
.orders-page{background:#f5f7fb}.filter-row{display:flex;gap:10rpx;margin-top:25rpx;padding:8rpx;background:#e9ecf2;border-radius:18rpx}.filter{flex:1;height:60rpx;color:#7d8595;border-radius:13rpx;font-size:21rpx;line-height:60rpx;text-align:center}.filter.active{color:#493eaf;background:#fff}.state{text-align:center;color:#8d96a7}.order-card{margin-top:20rpx;padding:27rpx;background:#fff;border-radius:26rpx;box-shadow:0 11rpx 34rpx rgba(36,55,86,.055)}.order-top,.expert-row{display:flex;align-items:center;justify-content:space-between}.package-name{font-size:28rpx;font-weight:820}.order-no{margin-top:5rpx;color:#9aa1af;font-size:17rpx}.status{padding:8rpx 13rpx;color:#665baf;background:#efedff;border-radius:999rpx;font-size:18rpx}.status.completed{color:#19734b;background:#e7f7ef}.status.disputed,.status.cancelled{color:#a63e53;background:#fff0f3}.expert-row{margin-top:20rpx;padding:17rpx;background:#f5f6f9;border-radius:15rpx;color:#707b8f;font-size:21rpx}.expert-row text:last-child{color:#453b9c;font-size:27rpx;font-weight:850}.target-name{margin-top:17rpx;font-size:23rpx;font-weight:700}.summary text{display:block;margin-top:8rpx;color:#7c8698;font-size:19rpx}.timeline{display:flex;flex-wrap:wrap;gap:8rpx 15rpx;margin-top:11rpx;color:#969eac;font-size:18rpx}.notice{margin-top:14rpx;padding:14rpx;color:#80622a;background:#fff5dc;border-radius:13rpx;font-size:19rpx}.notice.danger{color:#9a4354;background:#fff0f3}.actions{display:flex;flex-wrap:wrap;gap:12rpx;margin-top:20rpx}.small-btn{width:auto;height:62rpx;margin:0;padding:0 20rpx;border-radius:15rpx;font-size:20rpx;line-height:62rpx}.report-box{margin-top:22rpx;padding:23rpx;background:#f6f4ff;border-radius:19rpx}.report-version{color:#6257e8;font-size:20rpx;font-weight:800}.report-title{margin-top:18rpx;font-size:23rpx;font-weight:800}.report-text,.recommended,.final-reply{margin-top:7rpx;color:#626d82;font-size:21rpx;line-height:1.75;white-space:pre-wrap}.recommended{padding:17rpx;color:#413793;background:#fff;border-radius:15rpx;font-weight:750}.final-reply{padding:17rpx;color:#4f4630;background:#fff9e8;border-radius:15rpx}.modal-mask{position:fixed;z-index:99;inset:0;display:flex;align-items:flex-end;padding:28rpx;background:rgba(15,20,35,.55)}.action-sheet{width:100%;padding:30rpx;background:#fff;border-radius:30rpx}.sheet-title{font-size:31rpx;font-weight:850}.action-sheet .field-textarea{margin-top:20rpx}.sheet-buttons{display:flex;gap:14rpx;margin-top:22rpx}.sheet-buttons button{flex:1;margin:0}.rating-row{display:flex;gap:10rpx;margin-top:20rpx}.star{color:#d9dce3;font-size:46rpx}.star.active{color:#f0a335}
</style>
