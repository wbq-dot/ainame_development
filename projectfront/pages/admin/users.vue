<template>
  <view class="admin-page">
    <view class="admin-hero">
      <view>
        <view class="hero-eyebrow">ADMIN CONSOLE</view>
        <view class="hero-title">普通用户管理</view>
        <view class="hero-desc">只管理普通用户，管理员账号不会出现在列表中。</view>
      </view>
      <view class="total-badge"><text>{{ total }}</text>位用户</view>
    </view>
    <view class="refund-entry" @click="openRefunds"><text>退</text><view><view>退款审批</view><small>处理用户整单退款与异常重试</small></view><b>›</b></view>

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

    <view v-for="user in users" :key="user.id" class="user-card">
      <view class="user-head">
        <view class="user-avatar">{{ user.username.slice(0, 1) }}</view>
        <view class="user-main">
          <view class="name-line">
            <text class="user-name">{{ user.username }}</text>
            <text class="status-badge" :class="user.status">{{ statusText(user.status) }}</text>
          </view>
          <view class="user-email">{{ user.email }}</view>
          <view class="user-id">用户 ID：{{ user.id }}</view>
        </view>
      </view>

      <view class="credit-grid">
        <view class="credit-item"><text>{{ user.balance }}</text><view>起名余额</view></view>
        <view class="credit-item"><text>{{ user.total_used }}</text><view>起名使用</view></view>
        <view class="credit-item"><text>{{ user.total_recharge }}</text><view>起名充值</view></view>
        <view class="credit-item"><text>{{ user.total_refund }}</text><view>起名退款</view></view>
        <view class="credit-item"><text>{{ user.logo_balance }}</text><view>Logo 余额</view></view>
        <view class="credit-item"><text>{{ user.logo_total_used }}</text><view>Logo 使用</view></view>
        <view class="credit-item"><text>{{ user.logo_total_recharge }}</text><view>Logo 充值</view></view>
        <view class="credit-item"><text>{{ user.logo_total_refund }}</text><view>Logo 退款</view></view>
      </view>

      <view class="time-line">
        <text>注册：{{ formatDate(user.created_at) }}</text>
        <text v-if="user.frozen_at">冻结：{{ formatDate(user.frozen_at) }}</text>
        <text v-if="user.deleted_at">删除：{{ formatDate(user.deleted_at) }}</text>
      </view>

      <view v-if="user.status !== 'deleted'" class="action-row">
        <button v-if="user.status === 'active'" class="action-btn freeze" @click="openAction('freeze', user)">冻结</button>
        <button v-if="user.status === 'frozen'" class="action-btn unfreeze" @click="openAction('unfreeze', user)">解冻</button>
        <button class="action-btn delete" @click="openAction('delete', user)">删除</button>
      </view>
      <view v-else class="deleted-note">账号已匿名化，订单、流水及私人知识库仍保留。</view>
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
    openRefunds() { uni.navigateTo({ url: '/pages/admin/refunds' }) },
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
    statusText(status) {
      return { active: '正常', frozen: '已冻结', deleted: '已删除' }[status] || status
    },
    formatDate(value) {
      if (!value) return '—'
      return String(value).replace('T', ' ').slice(0, 16)
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
        this.closeActionAfterSuccess()
        await this.loadUsers(true)
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 3000 })
      } finally {
        this.submitting = false
      }
    },
    closeActionAfterSuccess() {
      this.actionVisible = false
      this.selectedUser = null
      this.selectedAction = ''
      this.reason = ''
    }
  }
}
</script>

<style scoped>
.admin-page { min-height: 100vh; padding: 28rpx 28rpx 70rpx; background: #f3f5f9; }
.admin-hero { display: flex; align-items: center; justify-content: space-between; padding: 34rpx 32rpx; color: #fff; background: linear-gradient(135deg, #171d2d, #373c55); border-radius: 29rpx; box-shadow: 0 18rpx 40rpx rgba(23, 29, 45, 0.2); }
.refund-entry { display:flex; align-items:center; gap:18rpx; margin-top:20rpx; padding:22rpx 25rpx; color:#30364d; background:#fff; border-radius:22rpx; box-shadow:0 10rpx 30rpx rgba(36,55,86,.05); }
.refund-entry > text { display:flex; align-items:center; justify-content:center; width:62rpx; height:62rpx; color:#fff; background:#6257e8; border-radius:17rpx; font-weight:850; }
.refund-entry > view { flex:1; font-size:25rpx; font-weight:800; }
.refund-entry small { display:block; margin-top:5rpx; color:#8d95a5; font-size:19rpx; font-weight:400; }
.refund-entry b { color:#7168c8; font-size:40rpx; }
.hero-eyebrow { color: #f2d586; font-size: 17rpx; font-weight: 800; letter-spacing: 4rpx; }
.hero-title { margin-top: 12rpx; font-size: 39rpx; font-weight: 850; }
.hero-desc { margin-top: 10rpx; color: #c6cbd7; font-size: 21rpx; }
.total-badge { display: flex; flex-direction: column; align-items: center; min-width: 105rpx; padding: 15rpx; color: #d7dbea; background: rgba(255,255,255,.1); border-radius: 20rpx; font-size: 18rpx; }
.total-badge text { color: #f2d586; font-size: 34rpx; font-weight: 850; }
.search-panel { margin-top: 22rpx; padding: 24rpx; background: #fff; border-radius: 25rpx; box-shadow: 0 10rpx 30rpx rgba(36,55,86,.05); }
.search-row { display: flex; gap: 13rpx; }
.search-input { flex: 1; min-width: 0; height: 78rpx; padding: 0 20rpx; background: #f3f5f8; border-radius: 17rpx; font-size: 24rpx; }
.search-btn { width: 115rpx; height: 78rpx; margin: 0; color: #fff; background: #30364d; border-radius: 17rpx; font-size: 23rpx; line-height: 78rpx; }
.status-tabs { display: flex; gap: 12rpx; margin-top: 19rpx; }
.status-tab { flex: 1; padding: 13rpx 0; color: #7e8799; background: #f3f5f8; border-radius: 14rpx; font-size: 21rpx; text-align: center; }
.status-tab.active { color: #fff; background: #6257e8; }
.state-card { margin-top: 22rpx; padding: 55rpx 20rpx; color: #9099aa; background: #fff; border-radius: 24rpx; text-align: center; }
.empty-icon { display: flex; align-items: center; justify-content: center; width: 70rpx; height: 70rpx; margin: 0 auto 16rpx; color: #8b84d9; background: #eeecff; border-radius: 20rpx; font-weight: 800; }
.user-card { margin-top: 20rpx; padding: 27rpx; background: #fff; border-radius: 25rpx; box-shadow: 0 11rpx 32rpx rgba(36,55,86,.055); }
.user-head { display: flex; align-items: center; }
.user-avatar { display: flex; align-items: center; justify-content: center; width: 76rpx; height: 76rpx; color: #fff; background: linear-gradient(135deg, #6257e8, #9a72ef); border-radius: 21rpx; font-size: 29rpx; font-weight: 850; }
.user-main { flex: 1; min-width: 0; margin-left: 18rpx; }
.name-line { display: flex; align-items: center; gap: 13rpx; }
.user-name { font-size: 28rpx; font-weight: 800; }
.status-badge { padding: 6rpx 12rpx; border-radius: 999rpx; font-size: 17rpx; }
.status-badge.active { color: #19734b; background: #e7f7ef; }
.status-badge.frozen { color: #9b651b; background: #fff3dc; }
.status-badge.deleted { color: #a83b50; background: #fff0f3; }
.user-email { margin-top: 6rpx; overflow: hidden; color: #737e93; font-size: 22rpx; text-overflow: ellipsis; white-space: nowrap; }
.user-id { margin-top: 4rpx; color: #a0a8b7; font-size: 18rpx; }
.credit-grid { display: grid; grid-template-columns: repeat(3, 1fr); margin-top: 22rpx; padding: 20rpx 0; background: #f6f7fa; border-radius: 18rpx; }
.credit-item { padding: 10rpx 0; color: #8c95a6; border-right: 1rpx solid #e3e6ec; font-size: 18rpx; text-align: center; }
.credit-item:nth-child(3n) { border-right: 0; }
.credit-item text { display: block; margin-bottom: 4rpx; color: #30374c; font-size: 28rpx; font-weight: 800; }
.time-line { display: flex; flex-wrap: wrap; gap: 8rpx 20rpx; margin-top: 17rpx; color: #969faf; font-size: 18rpx; }
.action-row { display: flex; gap: 14rpx; margin-top: 22rpx; }
.action-btn { flex: 1; height: 66rpx; margin: 0; border-radius: 16rpx; font-size: 22rpx; line-height: 66rpx; }
.action-btn.freeze { color: #96601a; background: #fff2d8; }
.action-btn.unfreeze { color: #18764c; background: #e6f7ef; }
.action-btn.delete { color: #bd3f58; background: #fff0f3; }
.deleted-note { margin-top: 20rpx; padding: 16rpx; color: #8d6d73; background: #fff5f6; border-radius: 14rpx; font-size: 19rpx; line-height: 1.5; }
.load-more { height: 75rpx; margin-top: 22rpx; color: #6257e8; background: #eeecff; border-radius: 18rpx; font-size: 23rpx; line-height: 75rpx; }
.list-end { padding: 28rpx 0 0; color: #a2a9b7; font-size: 20rpx; text-align: center; }
.modal-mask { position: fixed; z-index: 99; inset: 0; display: flex; align-items: flex-end; padding: 30rpx; background: rgba(16,21,34,.55); }
.action-modal { width: 100%; padding: 31rpx; background: #fff; border-radius: 30rpx; }
.modal-title { font-size: 32rpx; font-weight: 850; }
.target-box { margin-top: 20rpx; padding: 19rpx; background: #f4f5f8; border-radius: 16rpx; font-size: 25rpx; font-weight: 750; }
.target-box text { display: block; margin-top: 5rpx; color: #8992a4; font-size: 20rpx; font-weight: 400; }
.impact-text { margin-top: 18rpx; color: #6e788c; font-size: 22rpx; line-height: 1.6; }
.reason-input { width: 100%; height: 150rpx; margin-top: 18rpx; padding: 18rpx; background: #f4f5f8; border-radius: 16rpx; font-size: 23rpx; }
.modal-actions { display: flex; gap: 15rpx; margin-top: 23rpx; }
.modal-btn { flex: 1; height: 74rpx; margin: 0; border-radius: 17rpx; font-size: 23rpx; line-height: 74rpx; }
.modal-btn.cancel { color: #6f788b; background: #eef0f4; }
.modal-btn.confirm { color: #fff; background: #6257e8; }
.modal-btn.confirm.delete { background: #d94a64; }
</style>
