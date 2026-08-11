<template>
  <view class="page-shell workbench-page">
    <view class="workbench-hero">
      <view><view class="eyebrow">EXPERT ORDER POOL</view><view class="hero-title">{{ profile ? profile.display_name : '专家工作台' }}</view><view class="hero-desc">{{ levelText(profile && profile.expert_level) }} · 选择订单、交付起名结果</view></view>
      <view class="role-badge">专家</view>
    </view>
    <view class="tab-row"><view v-for="item in tabs" :key="item.value" class="tab" :class="{active:tab===item.value}" @click="tab=item.value">{{ item.label }}</view></view>

    <template v-if="tab==='orders'">
      <view class="pool-tip">待接订单只向同等级专家展示。接单成功后，其他专家将不再看到该订单。</view>
      <view v-if="!orders.length" class="card state">当前等级暂无可处理订单</view>
      <view v-for="order in orders" :key="order.id" class="item-card">
        <view class="item-top"><view><view class="item-name">{{ orderTitle(order) }}</view><view class="order-no">{{ order.order_no }}</view></view><view class="badge" :class="order.service_status">{{ orderStatus(order.service_status) }}</view></view>
        <view class="request-grid">
          <view v-if="order.surname"><text>姓氏</text><strong>{{ order.surname }}</strong></view>
          <view v-if="order.candidate_name"><text>已有名字</text><strong>{{ order.candidate_name }}</strong></view>
          <view v-if="order.gender"><text>性别</text><strong>{{ genderText(order.gender) }}</strong></view>
          <view v-if="order.birth_datetime"><text>出生时间</text><strong>{{ formatDate(order.birth_datetime) }}</strong></view>
          <view v-if="order.birth_calendar"><text>历法</text><strong>{{ order.birth_calendar==='lunar'?'农历':'阳历' }}</strong></view>
          <view v-if="order.birthplace"><text>出生地</text><strong>{{ order.birthplace }}</strong></view>
          <view v-if="order.five_elements"><text>已知五行</text><strong>{{ order.five_elements }}</strong></view>
          <view v-if="order.generation_character"><text>辈分字</text><strong>{{ order.generation_character }}</strong></view>
          <view v-if="order.avoid_characters"><text>避用字</text><strong>{{ order.avoid_characters }}</strong></view>
        </view>
        <view class="long-info"><text>背景与场景</text><view>{{ order.background }}</view></view>
        <view class="long-info"><text>重点关注</text><view>{{ order.focus }}</view></view>
        <view v-if="order.parent_expectations" class="long-info"><text>客户期望</text><view>{{ order.parent_expectations }}</view></view>
        <view v-if="order.submitted_content" class="long-info"><text>客户原始内容</text><view>{{ order.submitted_content }}</view></view>
        <view v-if="order.notes" class="long-info"><text>补充说明</text><view>{{ order.notes }}</view></view>
        <view class="meta"><text>订单 ¥{{ order.amount }}</text><text>预计收入 ¥{{ order.expert_income }}</text><text>{{ order.image_count }} 张图片</text></view>
        <view v-if="order.revision_reason" class="note">用户修改要求：{{ order.revision_reason }}</view>
        <view class="action-row">
          <button v-if="order.image_count" class="small-btn ghost-btn" @click="previewCustomerImages(order)">查看客户图片</button>
          <button v-if="order.service_status==='pending_acceptance'&&!order.expert_id" class="small-btn primary-btn" @click="confirmAccept(order)">选择并接单</button>
          <button v-if="['working','revision_requested'].includes(order.service_status)" class="small-btn primary-btn" @click="openReportForm(order)">{{ order.service_status==='revision_requested'?'提交修改结果':'填写起名结果' }}</button>
        </view>
      </view>
    </template>

    <template v-if="tab==='income'">
      <view class="income-grid"><view><text>可结算</text><strong>¥{{ income.available }}</strong></view><view><text>处理中</text><strong>¥{{ income.pending }}</strong></view><view><text>已打款</text><strong>¥{{ income.paid }}</strong></view></view>
      <button class="primary-btn btn-gap" :disabled="Number(income.available)<=0" @click="confirmSettlement">申请结算全部可用收入</button>
      <view class="settlement-note">平台按实付金额收取 20%。系统只登记线下打款结果，不保存银行卡或支付宝账号。</view>
      <view v-for="item in settlements" :key="item.id" class="item-card"><view class="item-top"><view class="item-name">结算 ¥{{ item.amount }}</view><view class="badge">{{ settlementStatus(item.status) }}</view></view><view class="meta"><text>{{ formatDate(item.created_at) }}</text><text v-if="item.payment_reference">流水号 {{ item.payment_reference }}</text></view></view>
    </template>

    <template v-if="tab==='profile'">
      <view class="card profile-card"><view class="card-title">专家身份</view><view class="profile-line"><text>显示名称</text><strong>{{ profile && profile.display_name }}</strong></view><view class="profile-line"><text>专家等级</text><strong>{{ levelText(profile && profile.expert_level) }}</strong></view><view class="profile-line"><text>审核状态</text><strong>已通过</strong></view><view class="profile-line"><text>擅长领域</text><strong>{{ profile && profile.specialties }}</strong></view></view>
    </template>

    <view v-if="reportFormVisible" class="modal-mask" @click.self="closeReportForm"><view class="sheet scroll-sheet">
      <view class="sheet-title">提交第 {{ selectedOrder&&selectedOrder.revision_used?2:1 }} 版专家结果</view>
      <view class="field"><text class="field-label">推荐名字 *</text><textarea v-model.trim="reportForm.recommended_names" class="field-textarea short" maxlength="5000" placeholder="每行一个名字，并可附简短寓意" /></view>
      <view class="field"><text class="field-label">核心结论 *</text><textarea v-model.trim="reportForm.conclusion" class="field-textarea short" maxlength="1000" /></view>
      <view class="field"><text class="field-label">五行与时辰分析</text><textarea v-model.trim="reportForm.five_elements_analysis" class="field-textarea" maxlength="10000" /></view>
      <view class="field"><text class="field-label">详细分析 *</text><textarea v-model.trim="reportForm.analysis" class="field-textarea" maxlength="10000" /></view>
      <view class="field"><text class="field-label">使用建议 *</text><textarea v-model.trim="reportForm.suggestions" class="field-textarea short" maxlength="5000" /></view>
      <view class="field"><text class="field-label">给客户的最终回复 *</text><textarea v-model.trim="reportForm.final_reply" class="field-textarea" maxlength="10000" placeholder="用完整、易懂的话向客户说明最终建议" /></view>
      <view class="file-row" @click="choosePdf"><view><view>PDF 附件（选填）</view><text>{{ reportForm.fileName || '不超过 10MB，仅限 PDF' }}</text></view><view>选择文件</view></view>
      <view class="sheet-buttons"><button class="ghost-btn" @click="closeReportForm">取消</button><button class="primary-btn" :loading="submitting" @click="submitReport">确认交付</button></view>
    </view></view>
  </view>
</template>

<script>
import { api } from '../../api'
export default {
  data() { return { profile: null, tab: 'orders', tabs: [{ label: '订单池', value: 'orders' }, { label: '收入结算', value: 'income' }, { label: '专家资料', value: 'profile' }], orders: [], income: { available: '0.00', pending: '0.00', paid: '0.00' }, settlements: [], reportFormVisible: false, reportForm: {}, selectedOrder: null, submitting: false } },
  onShow() { this.loadAll() },
  methods: {
    async loadAll() { try { const [profile, orders, income, settlements] = await Promise.all([api.getExpertWorkbenchProfile(), api.getWorkbenchOrders(), api.getExpertIncome(), api.getExpertSettlements()]); this.profile = profile; this.orders = orders; this.income = income; this.settlements = settlements } catch (error) { uni.showToast({ title: error.message, icon: 'none', duration: 3000 }) } },
    levelText(v) { return { ordinary: '普通专家', renowned: '知名专家', top: '顶级专家' }[v] || '普通专家' },
    genderText(v) { return { unspecified: '不限', male: '男', female: '女' }[v] || v },
    orderTitle(order) { return order.service_mode === 'review' ? `名字精批：${order.candidate_name || '待分析'}` : `${order.package_name}起名：${order.surname ? order.surname + '姓' : '客户需求'}` },
    orderStatus(v) { return { pending_acceptance: '订单池待接', working: '进行中', delivered: '待客户确认', revision_requested: '待修改', completed: '已完成', disputed: '争议中', cancelled: '已取消' }[v] || v },
    settlementStatus(v) { return { pending: '审核中', paid: '已打款', rejected: '已驳回' }[v] || v },
    formatDate(v) { return v ? String(v).replace('T', ' ').slice(0, 16) : '—' },
    confirmAccept(order) { uni.showModal({ title: '确认选择该起名订单', content: `准确动作：接单 ${order.order_no}；接单后其他专家无法再选择；需在 ${order.delivery_days} 天内交付。`, confirmText: '确认接单', success: async ({ confirm }) => { if (confirm) { try { await api.acceptWorkbenchOrder(order.id); await this.loadAll(); uni.showToast({ title: '接单成功', icon: 'success' }) } catch (error) { uni.showToast({ title: error.message, icon: 'none' }) } } } }) },
    async previewCustomerImages(order) { try { const files = await api.getExpertOrderImages(order.id); const paths = []; for (const item of files) paths.push(await api.downloadExpertOrderImage(order.id, item.id)); if (paths.length) uni.previewImage({ current: paths[0], urls: paths }) } catch (error) { uni.showToast({ title: error.message, icon: 'none' }) } },
    openReportForm(order) { this.selectedOrder = order; this.reportForm = { recommended_names: '', conclusion: '', five_elements_analysis: '', analysis: '', suggestions: '', final_reply: '', filePath: '', fileName: '' }; this.reportFormVisible = true },
    closeReportForm() { if (!this.submitting) { this.reportFormVisible = false; this.selectedOrder = null } },
    choosePdf() { uni.chooseFile({ count: 1, extension: ['.pdf'], success: ({ tempFiles }) => { const file = tempFiles[0]; if (file.size > 10 * 1024 * 1024) { uni.showToast({ title: 'PDF 不能超过 10MB', icon: 'none' }); return } this.reportForm.filePath = file.path; this.reportForm.fileName = file.name } }) },
    async submitReport() { if (this.reportForm.recommended_names.length < 2 || this.reportForm.conclusion.length < 10 || this.reportForm.analysis.length < 30 || this.reportForm.suggestions.length < 10 || this.reportForm.final_reply.length < 10) { uni.showToast({ title: '请完整填写起名结果和最终回复', icon: 'none' }); return } this.submitting = true; try { const data = { recommended_names: this.reportForm.recommended_names, conclusion: this.reportForm.conclusion, five_elements_analysis: this.reportForm.five_elements_analysis || null, analysis: this.reportForm.analysis, suggestions: this.reportForm.suggestions, final_reply: this.reportForm.final_reply }; if (this.reportForm.filePath) await api.uploadExpertReport(this.selectedOrder.id, this.reportForm.filePath, data); else await api.submitTextExpertReport(this.selectedOrder.id, data); this.reportFormVisible = false; await this.loadAll(); uni.showToast({ title: '结果已交付', icon: 'success' }) } catch (error) { uni.showToast({ title: error.message, icon: 'none', duration: 3000 }) } finally { this.submitting = false } },
    confirmSettlement() { uni.showModal({ title: '申请专家结算', content: `准确动作：申请结算全部可用收入 ¥${this.income.available}；提交后由管理员线下打款，系统不会自动付款。`, confirmText: '申请结算', success: async ({ confirm }) => { if (confirm) { try { await api.createExpertSettlement({ amount: this.income.available, remark: null }); await this.loadAll() } catch (error) { uni.showToast({ title: error.message, icon: 'none' }) } } } }) }
  }
}
</script>

<style scoped>
.workbench-page{background:#f3f5f9}.workbench-hero{display:flex;align-items:center;justify-content:space-between;padding:34rpx;color:#fff;background:linear-gradient(135deg,#171d2d,#3d405d);border-radius:29rpx}.eyebrow{color:#f2d586;font-size:17rpx;font-weight:800;letter-spacing:4rpx}.hero-title{margin-top:10rpx;font-size:39rpx;font-weight:850}.hero-desc{margin-top:7rpx;color:#cbd0dc;font-size:20rpx}.role-badge{padding:12rpx 17rpx;color:#312f46;background:#f2d586;border-radius:15rpx;font-size:21rpx;font-weight:850}.tab-row{display:flex;gap:8rpx;margin-top:20rpx;padding:8rpx;background:#e4e7ed;border-radius:18rpx}.tab{flex:1;height:64rpx;color:#777f90;border-radius:14rpx;line-height:64rpx;text-align:center}.tab.active{color:#4137a0;background:#fff;font-weight:800}.pool-tip,.settlement-note{margin-top:18rpx;padding:17rpx;color:#75612d;background:#fff6da;border-radius:15rpx;font-size:19rpx;line-height:1.6}.state{text-align:center;color:#8e97a8}.item-card{margin-top:18rpx;padding:26rpx;background:#fff;border-radius:24rpx;box-shadow:0 10rpx 30rpx rgba(36,55,86,.05)}.item-top{display:flex;align-items:center;justify-content:space-between}.item-name{font-size:27rpx;font-weight:820}.order-no{margin-top:5rpx;color:#9ca3b0;font-size:17rpx}.badge{padding:8rpx 13rpx;color:#6c61aa;background:#efedff;border-radius:999rpx;font-size:18rpx}.request-grid{display:grid;grid-template-columns:1fr 1fr;gap:10rpx;margin-top:17rpx}.request-grid view{padding:13rpx;background:#f5f6f9;border-radius:13rpx}.request-grid text{display:block;color:#929aaa;font-size:17rpx}.request-grid strong{display:block;margin-top:5rpx;font-size:20rpx}.long-info{margin-top:12rpx;padding:15rpx;background:#f7f8fa;border-radius:14rpx}.long-info text{color:#7d8798;font-size:18rpx}.long-info view{margin-top:5rpx;font-size:20rpx;line-height:1.55;white-space:pre-wrap}.meta{display:flex;flex-wrap:wrap;gap:11rpx 20rpx;margin-top:17rpx;color:#7e8798;font-size:20rpx}.meta text:first-child{color:#443a9f;font-weight:800}.note{margin-top:14rpx;padding:14rpx;color:#82642d;background:#fff5dc;border-radius:13rpx;font-size:19rpx}.action-row{display:flex;flex-wrap:wrap;gap:12rpx;margin-top:18rpx}.small-btn{width:auto;height:62rpx;margin:0;padding:0 20rpx;border-radius:15rpx;font-size:20rpx;line-height:62rpx}.income-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12rpx;margin-top:22rpx}.income-grid view{padding:23rpx 10rpx;background:#fff;border-radius:20rpx;text-align:center}.income-grid text{display:block;color:#8b94a5;font-size:19rpx}.income-grid strong{display:block;margin-top:9rpx;color:#403690;font-size:29rpx}.profile-card{margin-top:20rpx}.profile-line{display:flex;justify-content:space-between;margin-top:18rpx;padding-bottom:18rpx;border-bottom:1rpx solid #edf0f4;color:#838c9c;font-size:21rpx}.profile-line strong{max-width:65%;color:#22293a;text-align:right}.modal-mask{position:fixed;z-index:99;inset:0;display:flex;align-items:flex-end;padding:28rpx;background:rgba(15,20,35,.55)}.sheet{width:100%;padding:30rpx;background:#fff;border-radius:30rpx}.scroll-sheet{max-height:88vh;overflow-y:auto}.sheet-title{font-size:31rpx;font-weight:850}.short{min-height:130rpx}.sheet-buttons{display:flex;gap:14rpx;margin-top:24rpx}.sheet-buttons button{flex:1;margin:0}.file-row{display:flex;align-items:center;justify-content:space-between;margin-top:22rpx;padding:20rpx;background:#f3f4f8;border-radius:16rpx;font-size:22rpx}.file-row text{display:block;margin-top:5rpx;color:#939ba9;font-size:18rpx}.file-row>view:last-child{color:#6257e8;font-weight:750}
</style>
