<template>
  <view class="admin-page">
    <view class="admin-hero">
      <view>
        <view class="hero-eyebrow">ADMIN CONSOLE</view>
        <view class="hero-title">普通用户管理</view>
        <view class="hero-desc">账号信息在左，余额与使用数据居中，所有账号操作统一在右。</view>
      </view>
      <view class="total-badge"><text>{{ total }}</text>位用户</view>
    </view>

    <view class="admin-nav">
      <view class="nav-item active">用户管理</view>
      <view class="nav-item" @click="goPackages">套餐管理</view>
    </view>

    <view class="search-panel">
      <view class="search-row">
        <input v-model.trim="keyword" class="search-input" maxlength="100" placeholder="搜索邮箱或用户名" confirm-type="search" @confirm="search" />
        <button class="search-btn" @click="search">搜索</button>
      </view>
      <view class="status-tabs">
        <view v-for="item in statusOptions" :key="item.value" class="status-tab" :class="{ active: status === item.value }" @click="changeStatus(item.value)">
          {{ item.label }}
        </view>
      </view>
    </view>

    <view v-if="loading && !users.length" class="state-card">正在加载用户…</view>
    <view v-else-if="!users.length" class="state-card">
      <view class="empty-icon">空</view>
      <view>没有符合条件的用户</view>
    </view>

    <view v-else class="user-list">
      <view class="table-head">
        <view>账号信息</view>
        <view>余额与累计数据</view>
        <view class="head-actions">账号操作</view>
      </view>

      <view v-for="user in users" :key="user.id" class="user-row">
        <view class="identity-cell">
          <view class="user-avatar">{{ avatarText(user) }}</view>
          <view class="user-main">
            <view class="name-line">
              <text class="user-name">{{ user.username }}</text>
              <text class="status-badge" :class="user.status">{{ statusText(user.status) }}</text>
            </view>
            <view class="user-email">{{ user.email }}</view>
            <view class="identity-meta">
              <text>ID {{ user.id }}</text>
              <text>注册 {{ formatDate(user.created_at) }}</text>
              <text v-if="user.frozen_at">冻结 {{ formatDate(user.frozen_at) }}</text>
              <text v-if="user.deleted_at">删除 {{ formatDate(user.deleted_at) }}</text>
            </view>
          </view>
        </view>

        <view class="metrics-cell">
          <view v-for="metric in creditMetrics(user)" :key="metric.label" class="metric-item">
            <text>{{ metric.value }}</text>
            <view>{{ metric.label }}</view>
          </view>
        </view>

        <view v-if="user.status !== 'deleted'" class="operation-cell">
          <button class="operation-btn credit" @click="openCredit(user)">调整余额</button>
          <button v-if="user.status === 'active'" class="operation-btn freeze" @click="openAction('freeze', user)">冻结</button>
          <button v-if="user.status === 'frozen'" class="operation-btn unfreeze" @click="openAction('unfreeze', user)">解冻</button>
          <button class="operation-btn delete" @click="openAction('delete', user)">删除</button>
        </view>
        <view v-else class="deleted-note">账号已匿名化，不再提供调账或状态操作。</view>
      </view>
    </view>

    <button v-if="hasMore" class="load-more" :loading="loading" :disabled="loading" @click="loadMore">加载更多</button>
    <view v-else-if="users.length" class="list-end">已经到底了</view>

    <view v-if="actionVisible" class="modal-mask" @click.self="closeAction">
      <view class="action-modal">
        <view class="modal-title">{{ actionTitle }}</view>
        <view class="target-box">
          <view>{{ selectedUser.username }}</view>
          <text>{{ selectedUser.email }} · ID {{ selectedUser.id }}</text>
        </view>
        <view class="impact-text">{{ actionImpact }}</view>
        <textarea v-model.trim="reason" class="reason-input" maxlength="200" placeholder="操作原因（选填，最多200字）" />
        <view class="modal-actions">
          <button class="modal-btn cancel" @click="closeAction">取消</button>
          <button class="modal-btn confirm" :class="selectedAction" :loading="submitting" :disabled="submitting" @click="confirmAction">
            {{ actionConfirmText }}
          </button>
        </view>
      </view>
    </view>

    <view v-if="creditVisible" class="modal-mask" @click.self="closeCredit">
      <view class="action-modal credit-modal">
        <view class="modal-title">调整用户余额</view>
        <view class="target-box">
          <view>{{ creditUser.username }}</view>
          <text>{{ creditUser.email }} · ID {{ creditUser.id }}</text>
        </view>

        <view class="field-label">余额类型</view>
        <view class="credit-type-tabs">
          <view class="credit-type-tab" :class="{ active: creditForm.creditType === 'name' }" @click="creditForm.creditType = 'name'">起名次数</view>
          <view class="credit-type-tab" :class="{ active: creditForm.creditType === 'logo' }" @click="creditForm.creditType = 'logo'">Logo 次数</view>
        </view>

        <view class="balance-preview">
          <view><text>当前余额</text><strong>{{ currentCreditBalance }}</strong></view>
          <view><text>调整量</text><strong :class="{ negative: changeAmount < 0 }">{{ changeAmount === null ? '—' : signedAmount(changeAmount) }}</strong></view>
          <view><text>预计余额</text><strong :class="{ invalid: predictedBalance !== null && predictedBalance < 0 }">{{ predictedBalance === null ? '—' : predictedBalance }}</strong></view>
        </view>

        <view class="field-label">增减次数</view>
        <input v-model.trim="creditForm.changeText" class="adjust-input" type="text" maxlength="11" placeholder="例如 +10 或 -5" />
        <view class="input-tip">正数增加，负数扣减；调整后余额不能小于 0。</view>

        <view class="field-label">调整原因</view>
        <textarea v-model.trim="creditForm.reason" class="reason-input credit-reason" maxlength="200" placeholder="必填，例如：客服补偿、纠正误发" />

        <view class="modal-actions">
          <button class="modal-btn cancel" @click="closeCredit">取消</button>
          <button class="modal-btn confirm" :loading="creditSubmitting" :disabled="!creditCanSubmit || creditSubmitting" @click="submitCreditAdjustment">确认调整</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../api'
import { getUser } from '../../utils/auth'

export default {
  data() {
    return {
      users: [],
      total: 0,
      page: 1,
      pageSize: 10,
      keyword: '',
      status: '',
      loading: false,
      submitting: false,
      actionVisible: false,
      selectedAction: '',
      selectedUser: null,
      reason: '',
      creditVisible: false,
      creditSubmitting: false,
      creditUser: null,
      creditForm: { creditType: 'name', changeText: '', reason: '' },
      statusOptions: [
        { label: '全部', value: '' },
        { label: '正常', value: 'active' },
        { label: '冻结', value: 'frozen' },
        { label: '已删除', value: 'deleted' }
      ]
    }
  },
  computed: {
    hasMore() {
      return this.users.length < this.total
    },
    actionTitle() {
      return { freeze: '冻结用户', unfreeze: '解冻用户', delete: '删除用户' }[this.selectedAction] || ''
    },
    actionConfirmText() {
      return { freeze: '确认冻结', unfreeze: '确认解冻', delete: '继续删除' }[this.selectedAction] || '确认'
    },
    actionImpact() {
      if (this.selectedAction === 'freeze') return '冻结后，该用户现有登录令牌将立即失效，无法登录或使用受保护功能。'
      if (this.selectedAction === 'unfreeze') return '解冻后，该用户可以重新登录并继续使用原有余额和数据。'
      if (this.selectedAction === 'delete') return '删除会匿名化邮箱、用户名和密码，账号无法恢复；订单、次数流水及私人知识库会继续保留。'
      return ''
    },
    currentCreditBalance() {
      if (!this.creditUser) return 0
      return this.creditForm.creditType === 'logo' ? this.creditUser.logo_balance : this.creditUser.balance
    },
    changeAmount() {
      const value = String(this.creditForm.changeText || '').trim()
      if (!/^[+-]?\d+$/.test(value)) return null
      const parsed = Number(value)
      if (!Number.isSafeInteger(parsed) || parsed === 0 || Math.abs(parsed) > 2147483647) return null
      return parsed
    },
    predictedBalance() {
      return this.changeAmount === null ? null : this.currentCreditBalance + this.changeAmount
    },
    creditCanSubmit() {
      return this.changeAmount !== null && this.predictedBalance >= 0 && this.predictedBalance <= 2147483647 && Boolean(this.creditForm.reason.trim())
    }
  },
  onLoad() {
    const currentUser = getUser()
    if (!currentUser || currentUser.role !== 'admin') {
      uni.showModal({
        title: '无权访问',
        content: '该页面仅限管理员使用。',
        showCancel: false,
        success: () => uni.navigateBack()
      })
      return
    }
    this.loadUsers(true)
  },
  methods: {
    goPackages() {
      uni.redirectTo({ url: '/pages/admin/packages' })
    },
    async loadUsers(reset = false) {
      if (this.loading) return
      if (reset) {
        this.page = 1
        this.users = []
      }
      this.loading = true
      try {
        const data = await api.getAdminUsers({
          page: this.page,
          pageSize: this.pageSize,
          keyword: this.keyword,
          status: this.status
        })
        this.users = reset ? data.items : [...this.users, ...data.items]
        this.total = data.total
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 3000 })
        if (error.message.includes('管理员权限')) setTimeout(() => uni.navigateBack(), 800)
      } finally {
        this.loading = false
      }
    },
    search() {
      this.loadUsers(true)
    },
    changeStatus(value) {
      if (this.status === value) return
      this.status = value
      this.loadUsers(true)
    },
    loadMore() {
      this.page += 1
      this.loadUsers(false)
    },
    avatarText(user) {
      return user.username ? user.username.slice(0, 1).toUpperCase() : '用'
    },
    statusText(status) {
      return { active: '正常', frozen: '已冻结', deleted: '已删除' }[status] || status
    },
    formatDate(value) {
      if (!value) return '—'
      return String(value).replace('T', ' ').slice(0, 16)
    },
    creditMetrics(user) {
      return [
        { label: '起名余额', value: user.balance },
        { label: '起名使用', value: user.total_used },
        { label: '起名充值', value: user.total_recharge },
        { label: 'Logo 余额', value: user.logo_balance },
        { label: 'Logo 使用', value: user.logo_total_used },
        { label: 'Logo 充值', value: user.logo_total_recharge }
      ]
    },
    openAction(action, user) {
      this.selectedAction = action
      this.selectedUser = user
      this.reason = ''
      this.actionVisible = true
    },
    closeAction() {
      if (this.submitting) return
      this.actionVisible = false
      this.selectedUser = null
      this.selectedAction = ''
      this.reason = ''
    },
    confirmAction() {
      if (this.selectedAction !== 'delete') {
        this.executeAction()
        return
      }
      const user = this.selectedUser
      uni.showModal({
        title: '第二次确认删除',
        content: `准确动作：永久停用并匿名化用户“${user.username}”（ID ${user.id}）。账号身份无法恢复，但订单、次数流水和私人知识库会保留。是否确认？`,
        confirmText: '确认删除',
        confirmColor: '#d94a64',
        success: ({ confirm }) => {
          if (confirm) this.executeAction()
        }
      })
    },
    async executeAction() {
      this.submitting = true
      try {
        let result
        if (this.selectedAction === 'freeze') result = await api.freezeUser(this.selectedUser.id, this.reason)
        if (this.selectedAction === 'unfreeze') result = await api.unfreezeUser(this.selectedUser.id, this.reason)
        if (this.selectedAction === 'delete') result = await api.deleteUser(this.selectedUser.id, this.reason)
        uni.showToast({ title: result.message, icon: 'success' })
        this.actionVisible = false
        this.selectedUser = null
        this.selectedAction = ''
        this.reason = ''
        await this.loadUsers(true)
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 3000 })
      } finally {
        this.submitting = false
      }
    },
    openCredit(user) {
      this.creditUser = user
      this.creditForm = { creditType: 'name', changeText: '', reason: '' }
      this.creditVisible = true
    },
    closeCredit() {
      if (this.creditSubmitting) return
      this.creditVisible = false
      this.creditUser = null
      this.creditForm = { creditType: 'name', changeText: '', reason: '' }
    },
    signedAmount(value) {
      return value > 0 ? `+${value}` : String(value)
    },
    async submitCreditAdjustment() {
      if (!this.creditCanSubmit || this.creditSubmitting) {
        uni.showToast({ title: '请填写有效增减次数和调整原因', icon: 'none' })
        return
      }
      this.creditSubmitting = true
      try {
        const result = await api.adjustUserCredit(this.creditUser.id, {
          credit_type: this.creditForm.creditType,
          change_count: this.changeAmount,
          reason: this.creditForm.reason.trim()
        })
        const index = this.users.findIndex((item) => item.id === result.user.id)
        if (index >= 0) this.users.splice(index, 1, result.user)
        uni.showToast({ title: result.message, icon: 'success' })
        this.creditVisible = false
        this.creditUser = null
        this.creditForm = { creditType: 'name', changeText: '', reason: '' }
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 3000 })
      } finally {
        this.creditSubmitting = false
      }
    }
  }
}
</script>

<style scoped>
.admin-page { min-height: 100vh; padding: 28rpx 28rpx 70rpx; background: #f3f5f9; }
.admin-hero { display: flex; align-items: center; justify-content: space-between; padding: 34rpx 32rpx; color: #fff; background: linear-gradient(135deg, #171d2d, #373c55); border-radius: 29rpx; box-shadow: 0 18rpx 40rpx rgba(23,29,45,.2); }
.hero-eyebrow { color: #f2d586; font-size: 17rpx; font-weight: 800; letter-spacing: 4rpx; }
.hero-title { margin-top: 12rpx; font-size: 39rpx; font-weight: 850; }
.hero-desc { margin-top: 10rpx; color: #c6cbd7; font-size: 21rpx; }
.total-badge { display: flex; flex-direction: column; align-items: center; min-width: 105rpx; padding: 15rpx; color: #d7dbea; background: rgba(255,255,255,.1); border-radius: 20rpx; font-size: 18rpx; }
.total-badge text { color: #f2d586; font-size: 34rpx; font-weight: 850; }
.admin-nav { display: grid; grid-template-columns: 1fr 1fr; gap: 10rpx; margin-top: 20rpx; padding: 8rpx; background: #e4e7ed; border-radius: 20rpx; }
.nav-item { padding: 18rpx 0; color: #747e91; border-radius: 15rpx; font-size: 23rpx; font-weight: 750; text-align: center; }
.nav-item.active { color: #fff; background: #30364d; box-shadow: 0 8rpx 20rpx rgba(48,54,77,.18); }
.search-panel { margin-top: 20rpx; padding: 24rpx; background: #fff; border-radius: 25rpx; box-shadow: 0 10rpx 30rpx rgba(36,55,86,.05); }
.search-row { display: flex; gap: 13rpx; }
.search-input { flex: 1; min-width: 0; height: 78rpx; padding: 0 20rpx; background: #f3f5f8; border-radius: 17rpx; font-size: 24rpx; }
.search-btn { width: 115rpx; height: 78rpx; margin: 0; color: #fff; background: #30364d; border-radius: 17rpx; font-size: 23rpx; line-height: 78rpx; }
.status-tabs { display: flex; gap: 12rpx; margin-top: 19rpx; }
.status-tab { flex: 1; padding: 13rpx 0; color: #7e8799; background: #f3f5f8; border-radius: 14rpx; font-size: 21rpx; text-align: center; }
.status-tab.active { color: #fff; background: #6257e8; }
.state-card { margin-top: 22rpx; padding: 55rpx 20rpx; color: #9099aa; background: #fff; border-radius: 24rpx; text-align: center; }
.empty-icon { display: flex; align-items: center; justify-content: center; width: 70rpx; height: 70rpx; margin: 0 auto 16rpx; color: #8b84d9; background: #eeecff; border-radius: 20rpx; font-weight: 800; }
.table-head { display: none; }
.user-row { margin-top: 20rpx; padding: 27rpx; background: #fff; border-radius: 25rpx; box-shadow: 0 11rpx 32rpx rgba(36,55,86,.055); }
.identity-cell { display: flex; align-items: center; min-width: 0; }
.user-avatar { display: flex; flex: 0 0 76rpx; align-items: center; justify-content: center; width: 76rpx; height: 76rpx; color: #fff; background: linear-gradient(135deg,#6257e8,#9a72ef); border-radius: 21rpx; font-size: 29rpx; font-weight: 850; }
.user-main { flex: 1; min-width: 0; margin-left: 18rpx; }
.name-line { display: flex; align-items: center; gap: 13rpx; }
.user-name { overflow: hidden; font-size: 28rpx; font-weight: 800; text-overflow: ellipsis; white-space: nowrap; }
.status-badge { flex: 0 0 auto; padding: 6rpx 12rpx; border-radius: 999rpx; font-size: 17rpx; }
.status-badge.active { color: #19734b; background: #e7f7ef; }
.status-badge.frozen { color: #9b651b; background: #fff3dc; }
.status-badge.deleted { color: #a83b50; background: #fff0f3; }
.user-email { margin-top: 6rpx; overflow: hidden; color: #737e93; font-size: 22rpx; text-overflow: ellipsis; white-space: nowrap; }
.identity-meta { display: flex; flex-wrap: wrap; gap: 5rpx 14rpx; margin-top: 6rpx; color: #a0a8b7; font-size: 18rpx; }
.metrics-cell { display: grid; grid-template-columns: repeat(3,1fr); margin-top: 22rpx; padding: 12rpx 0; background: #f6f7fa; border-radius: 18rpx; }
.metric-item { padding: 10rpx 4rpx; color: #8c95a6; border-right: 1rpx solid #e3e6ec; font-size: 18rpx; text-align: center; }
.metric-item:nth-child(3n) { border-right: 0; }
.metric-item text { display: block; margin-bottom: 4rpx; color: #30374c; font-size: 28rpx; font-weight: 800; }
.operation-cell { display: flex; gap: 12rpx; margin-top: 21rpx; }
.operation-btn { flex: 1; height: 64rpx; margin: 0; border-radius: 15rpx; font-size: 21rpx; line-height: 64rpx; }
.operation-btn.credit { color: #5548c4; background: #eceaff; }
.operation-btn.freeze { color: #96601a; background: #fff2d8; }
.operation-btn.unfreeze { color: #18764c; background: #e6f7ef; }
.operation-btn.delete { color: #bd3f58; background: #fff0f3; }
.deleted-note { margin-top: 20rpx; padding: 16rpx; color: #8d6d73; background: #fff5f6; border-radius: 14rpx; font-size: 19rpx; line-height: 1.5; }
.load-more { height: 75rpx; margin-top: 22rpx; color: #6257e8; background: #eeecff; border-radius: 18rpx; font-size: 23rpx; line-height: 75rpx; }
.list-end { padding: 28rpx 0 0; color: #a2a9b7; font-size: 20rpx; text-align: center; }
.modal-mask { position: fixed; z-index: 99; inset: 0; display: flex; align-items: flex-end; padding: 30rpx; background: rgba(16,21,34,.55); }
.action-modal { width: 100%; max-height: 88vh; padding: 31rpx; overflow-y: auto; background: #fff; border-radius: 30rpx; }
.modal-title { font-size: 32rpx; font-weight: 850; }
.target-box { margin-top: 20rpx; padding: 19rpx; background: #f4f5f8; border-radius: 16rpx; font-size: 25rpx; font-weight: 750; }
.target-box text { display: block; margin-top: 5rpx; color: #8992a4; font-size: 20rpx; font-weight: 400; }
.impact-text { margin-top: 18rpx; color: #6e788c; font-size: 22rpx; line-height: 1.6; }
.reason-input { width: 100%; height: 150rpx; margin-top: 18rpx; padding: 18rpx; background: #f4f5f8; border-radius: 16rpx; font-size: 23rpx; box-sizing: border-box; }
.modal-actions { display: flex; gap: 15rpx; margin-top: 23rpx; }
.modal-btn { flex: 1; height: 74rpx; margin: 0; border-radius: 17rpx; font-size: 23rpx; line-height: 74rpx; }
.modal-btn.cancel { color: #6f788b; background: #eef0f4; }
.modal-btn.confirm { color: #fff; background: #6257e8; }
.modal-btn.confirm.delete { background: #d94a64; }
.field-label { margin-top: 23rpx; color: #4e576b; font-size: 21rpx; font-weight: 750; }
.credit-type-tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 10rpx; margin-top: 10rpx; padding: 7rpx; background: #eef0f4; border-radius: 16rpx; }
.credit-type-tab { padding: 15rpx; color: #7e8799; border-radius: 12rpx; font-size: 22rpx; text-align: center; }
.credit-type-tab.active { color: #fff; background: #6257e8; }
.balance-preview { display: grid; grid-template-columns: repeat(3,1fr); gap: 10rpx; margin-top: 18rpx; padding: 17rpx; background: #f7f7fb; border-radius: 17rpx; text-align: center; }
.balance-preview text { display: block; color: #929aaa; font-size: 18rpx; }
.balance-preview strong { display: block; margin-top: 7rpx; color: #30374c; font-size: 28rpx; }
.balance-preview strong.negative { color: #b36a2b; }
.balance-preview strong.invalid { color: #d94a64; }
.adjust-input { height: 74rpx; margin-top: 10rpx; padding: 0 18rpx; background: #f4f5f8; border-radius: 15rpx; font-size: 25rpx; }
.input-tip { margin-top: 8rpx; color: #929aaa; font-size: 18rpx; }
.credit-reason { margin-top: 10rpx; }

@media (min-width: 1100px) {
  .admin-page { max-width: 1500px; margin: 0 auto; padding-left: 34px; padding-right: 34px; }
  .table-head, .user-row { display: grid; grid-template-columns: minmax(280px,1.25fr) minmax(500px,2.2fr) minmax(240px,.95fr); gap: 22px; align-items: center; }
  .table-head { margin-top: 22rpx; padding: 0 27rpx 10rpx; color: #8d96a7; font-size: 19rpx; font-weight: 750; }
  .head-actions { text-align: right; }
  .user-row { min-height: 126px; margin-top: 10rpx; padding: 22rpx 27rpx; border-radius: 18rpx; }
  .metrics-cell { grid-template-columns: repeat(6,1fr); margin-top: 0; padding: 8rpx 0; }
  .metric-item { border-right: 1rpx solid #e3e6ec; }
  .metric-item:nth-child(3n) { border-right: 1rpx solid #e3e6ec; }
  .metric-item:last-child { border-right: 0; }
  .operation-cell { flex-wrap: wrap; justify-content: flex-end; margin-top: 0; }
  .operation-btn { flex: 0 0 auto; min-width: 82rpx; padding: 0 17rpx; }
  .operation-btn.credit { min-width: 118rpx; }
  .deleted-note { margin-top: 0; text-align: right; }
  .modal-mask { align-items: center; justify-content: center; }
  .action-modal { max-width: 620px; }
}
</style>
