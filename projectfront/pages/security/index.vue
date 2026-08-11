<template>
  <view class="page-shell security-page">
    <view class="security-hero">
      <view class="hero-copy">
        <view class="hero-tag">ACCOUNT SECURITY</view>
        <view class="hero-title">账号安全</view>
        <view class="hero-desc">管理登录密码、绑定邮箱与账号状态。</view>
      </view>
      <view class="shield-art">
        <view class="shield-shape"><text>✓</text></view>
        <view class="shield-orbit"></view>
        <view class="shield-dot"></view>
      </view>
    </view>

    <view v-if="user">
      <view class="account-card">
        <view class="account-avatar">{{ avatarText }}</view>
        <view class="account-copy">
          <view class="account-name">{{ user.username }}</view>
          <view class="account-email">{{ maskEmail(user.email) }}</view>
        </view>
        <view class="safe-badge"><text></text>安全登录</view>
      </view>

      <view class="section-heading">
        <view class="section-title">安全操作</view>
        <view class="section-note">同一时间仅展开一项设置</view>
      </view>

      <view class="action-list">
        <view class="action-block" :class="{ expanded: activeAction === 'password' }">
          <view class="action-row" @click="toggleAction('password')">
            <view class="action-icon purple">密</view>
            <view class="action-copy"><view class="action-title">修改密码</view><view class="action-desc">更新登录密码并退出所有设备</view></view>
            <view class="action-arrow">{{ activeAction === 'password' ? '−' : '›' }}</view>
          </view>
          <view v-if="activeAction === 'password'" class="action-panel">
            <view class="field first-field">
              <text class="field-label">原密码</text>
              <input v-model="passwordForm.current_password" class="field-input" password maxlength="64" placeholder="请输入当前密码" />
            </view>
            <view class="field">
              <text class="field-label">新密码</text>
              <input v-model="passwordForm.new_password" class="field-input" password maxlength="64" placeholder="请输入 8–64 位新密码" />
            </view>
            <view class="field">
              <text class="field-label">确认新密码</text>
              <input v-model="passwordForm.confirm_password" class="field-input" password maxlength="64" placeholder="请再次输入新密码" />
            </view>
            <button class="primary-btn btn-gap" :loading="passwordLoading" :disabled="passwordLoading" @click="submitPassword">确认修改</button>
          </view>
        </view>

        <view class="action-block" :class="{ expanded: activeAction === 'email' }">
          <view class="action-row" @click="toggleAction('email')">
            <view class="action-icon green">邮</view>
            <view class="action-copy"><view class="action-title">更换绑定邮箱</view><view class="action-desc">验证码将发送至新的邮箱地址</view></view>
            <view class="action-arrow">{{ activeAction === 'email' ? '−' : '›' }}</view>
          </view>
          <view v-if="activeAction === 'email'" class="action-panel">
            <view class="field first-field">
              <text class="field-label">新邮箱</text>
              <input v-model.trim="emailForm.new_email" class="field-input" type="text" maxlength="254" placeholder="请输入新的邮箱地址" />
            </view>
            <view class="field">
              <text class="field-label">邮箱验证码</text>
              <view class="code-row">
                <input v-model.trim="emailForm.code" class="field-input code-input" type="number" maxlength="6" placeholder="6 位验证码" />
                <button class="code-btn" :loading="codeLoading" :disabled="codeLoading || countdown > 0" @click="sendEmailCode">
                  {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
                </button>
              </view>
            </view>
            <button class="primary-btn btn-gap" :loading="emailLoading" :disabled="emailLoading || codeLoading" @click="submitEmail">确认更换</button>
          </view>
        </view>

        <view class="action-block danger-block" :class="{ expanded: activeAction === 'delete' }">
          <view class="action-row" @click="toggleAction('delete')">
            <view class="action-icon red">销</view>
            <view class="action-copy"><view class="action-title danger-title">注销账号</view><view class="action-desc">永久停用账号并清理个人内容</view></view>
            <view class="action-arrow danger-arrow">{{ activeAction === 'delete' ? '−' : '›' }}</view>
          </view>
          <view v-if="activeAction === 'delete'" class="action-panel danger-panel">
            <view class="warning-box">
              <view class="warning-mark">!</view>
              <view><view class="warning-title">此操作不可恢复</view><view class="warning-desc">账号会立即失效，知识库、Logo 和起名会话将由后台持续清理；订单及权益流水会按审计要求保留。</view></view>
            </view>
            <button class="danger-confirm-btn" :loading="deleteLoading" :disabled="deleteLoading" @click="confirmDelete">永久注销账号</button>
          </view>
        </view>
      </view>

      <view class="security-note"><view class="note-mark">i</view><view>修改密码或邮箱后，所有设备上的登录状态都会立即失效，需要重新登录。</view></view>
    </view>

    <view v-else class="login-card">
      <view class="login-icon">锁</view>
      <view class="login-title">登录后管理账号安全</view>
      <view class="login-desc">账号安全操作需要验证当前登录状态。</view>
      <button class="primary-btn btn-gap" @click="goLogin">前往登录</button>
    </view>
  </view>
</template>

<script>
import { api } from '../../api'
import { clearLogin, getUser } from '../../utils/auth'
import { clearNamingHistory } from '../../utils/history'

export default {
  data() {
    return {
      user: null,
      activeAction: '',
      passwordLoading: false,
      emailLoading: false,
      codeLoading: false,
      deleteLoading: false,
      countdown: 0,
      timer: null,
      passwordForm: { current_password: '', new_password: '', confirm_password: '' },
      emailForm: { new_email: '', code: '' }
    }
  },
  computed: {
    avatarText() {
      return this.user && this.user.username ? this.user.username.slice(0, 1).toUpperCase() : '安'
    }
  },
  onShow() {
    this.user = getUser()
  },
  onUnload() {
    this.stopCountdown()
  },
  methods: {
    maskEmail(email) {
      if (!email || !email.includes('@')) return email || ''
      const at = email.lastIndexOf('@')
      const name = email.slice(0, at)
      const domain = email.slice(at + 1)
      const visible = name.slice(0, Math.min(2, name.length))
      return `${visible}${name.length > 2 ? '***' : '*'}@${domain}`
    },
    validEmail(email) {
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
    },
    toggleAction(action) {
      this.activeAction = this.activeAction === action ? '' : action
    },
    showError(message) {
      uni.showToast({ title: message, icon: 'none', duration: 2800 })
    },
    goLogin() {
      uni.navigateTo({ url: '/pages/auth/login' })
    },
    stopCountdown() {
      if (this.timer) clearInterval(this.timer)
      this.timer = null
    },
    startCountdown() {
      this.stopCountdown()
      this.countdown = 60
      this.timer = setInterval(() => {
        this.countdown -= 1
        if (this.countdown <= 0) this.stopCountdown()
      }, 1000)
    },
    logoutAfterChange(message) {
      clearLogin()
      this.user = null
      uni.showToast({ title: message, icon: 'success', duration: 1200 })
      setTimeout(() => uni.reLaunch({ url: '/pages/auth/login' }), 650)
    },
    async submitPassword() {
      const form = this.passwordForm
      if (!form.current_password) {
        this.showError('请输入原密码')
        return
      }
      if (form.new_password.length < 8 || form.new_password.length > 64) {
        this.showError('新密码长度应为 8–64 位')
        return
      }
      if (form.new_password !== form.confirm_password) {
        this.showError('两次输入的新密码不一致')
        return
      }
      if (form.current_password === form.new_password) {
        this.showError('新密码不能与原密码相同')
        return
      }
      this.passwordLoading = true
      try {
        await api.changePassword(form)
        this.logoutAfterChange('密码已修改，请重新登录')
      } catch (error) {
        this.showError(error.message)
      } finally {
        this.passwordLoading = false
      }
    },
    async sendEmailCode() {
      const email = this.emailForm.new_email.trim().toLowerCase()
      if (!this.validEmail(email)) {
        this.showError('请输入正确的新邮箱地址')
        return
      }
      if (this.user.email && email === this.user.email.trim().toLowerCase()) {
        this.showError('新邮箱不能与当前邮箱相同')
        return
      }
      this.codeLoading = true
      try {
        await api.sendEmailChangeCode(email)
        this.emailForm.new_email = email
        this.startCountdown()
        uni.showToast({ title: '验证码已发送', icon: 'success' })
      } catch (error) {
        this.showError(error.message)
      } finally {
        this.codeLoading = false
      }
    },
    async submitEmail() {
      const email = this.emailForm.new_email.trim().toLowerCase()
      if (!this.validEmail(email)) {
        this.showError('请输入正确的新邮箱地址')
        return
      }
      if (this.user.email && email === this.user.email.trim().toLowerCase()) {
        this.showError('新邮箱不能与当前邮箱相同')
        return
      }
      if (!/^\d{6}$/.test(this.emailForm.code)) {
        this.showError('请输入 6 位邮箱验证码')
        return
      }
      this.emailLoading = true
      try {
        await api.changeEmail({ new_email: email, code: this.emailForm.code })
        this.stopCountdown()
        this.logoutAfterChange('邮箱已更换，请重新登录')
      } catch (error) {
        this.showError(error.message)
      } finally {
        this.emailLoading = false
      }
    },
    confirmDelete() {
      uni.showModal({
        title: '确认注销账号',
        content: '账号注销后无法恢复，原邮箱会被释放，个人知识库、Logo 和起名会话将持续清理。确认永久注销吗？',
        confirmText: '永久注销',
        confirmColor: '#d5445d',
        success: async ({ confirm }) => {
          if (!confirm || this.deleteLoading) return
          this.deleteLoading = true
          try {
            await api.deleteAccount()
            clearNamingHistory()
            clearLogin()
            this.user = null
            uni.showToast({ title: '账号已注销', icon: 'success', duration: 1200 })
            setTimeout(() => uni.reLaunch({ url: '/pages/auth/login' }), 650)
          } catch (error) {
            this.showError(error.message)
          } finally {
            this.deleteLoading = false
          }
        }
      })
    }
  }
}
</script>

<style scoped>
.security-page { background: radial-gradient(circle at 94% 2%,#e7e3ff 0,transparent 27%),#f5f7fb; }
.security-hero { position: relative; min-height: 245rpx; padding: 36rpx; overflow: hidden; color: #fff; background: linear-gradient(140deg,#232844,#465079 70%,#59658e); border-radius: 34rpx; box-shadow: 0 20rpx 46rpx rgba(35,40,68,.18); }
.hero-copy { position: relative; z-index: 2; width: 68%; }
.hero-tag { color: #cbd2ef; font-size: 17rpx; font-weight: 850; letter-spacing: 3rpx; }
.hero-title { margin-top: 16rpx; font-size: 42rpx; font-weight: 900; }
.hero-desc { margin-top: 13rpx; color: #dce1f4; font-size: 21rpx; line-height: 1.55; }
.shield-art { position: absolute; top: 0; right: 0; width: 235rpx; height: 100%; }
.shield-shape { position: absolute; top: 44rpx; right: 35rpx; display: flex; align-items: center; justify-content: center; width: 108rpx; height: 122rpx; color: #34465d; background: linear-gradient(145deg,#a1ecd5,#72caae); border-radius: 47% 47% 54% 54%; box-shadow: 0 17rpx 34rpx rgba(13,33,37,.2); transform: rotate(5deg); }
.shield-shape text { font-size: 51rpx; font-weight: 900; }
.shield-orbit { position: absolute; top: 25rpx; right: 18rpx; width: 173rpx; height: 173rpx; border: 2rpx solid rgba(255,255,255,.15); border-radius: 50%; }
.shield-dot { position: absolute; right: 174rpx; bottom: 48rpx; width: 23rpx; height: 23rpx; background: #f2cf79; border-radius: 50%; }
.account-card { display: flex; align-items: center; margin-top: 25rpx; padding: 26rpx; color: #fff; background: linear-gradient(135deg,#544abf,#7665d8); border-radius: 27rpx; box-shadow: 0 15rpx 34rpx rgba(73,62,171,.16); }
.account-avatar { display: flex; flex: 0 0 72rpx; align-items: center; justify-content: center; width: 72rpx; height: 72rpx; color: #544abf; background: #fff; border-radius: 21rpx; font-size: 30rpx; font-weight: 900; }
.account-copy { flex: 1; min-width: 0; margin-left: 18rpx; }
.account-name { overflow: hidden; font-size: 27rpx; font-weight: 850; text-overflow: ellipsis; white-space: nowrap; }
.account-email { margin-top: 5rpx; overflow: hidden; color: #dedaff; font-size: 20rpx; text-overflow: ellipsis; white-space: nowrap; }
.safe-badge { display: flex; align-items: center; padding: 9rpx 14rpx; color: #4e459f; background: #fff; border-radius: 999rpx; font-size: 18rpx; font-weight: 700; }
.safe-badge text { width: 10rpx; height: 10rpx; margin-right: 7rpx; background: #45a783; border-radius: 50%; }
.section-heading { display: flex; align-items: flex-end; justify-content: space-between; margin-top: 36rpx; }
.section-title { font-size: 31rpx; font-weight: 850; }
.section-note { color: #929aaa; font-size: 19rpx; }
.action-list { display: flex; flex-direction: column; gap: 16rpx; margin-top: 18rpx; }
.action-block { overflow: hidden; background: #fff; border: 1rpx solid rgba(31,55,90,.055); border-radius: 26rpx; box-shadow: 0 12rpx 34rpx rgba(36,55,86,.055); }
.action-block.expanded { border-color: #dcd7ff; box-shadow: 0 15rpx 38rpx rgba(71,60,166,.09); }
.action-row { display: flex; align-items: center; min-height: 122rpx; padding: 23rpx 25rpx; }
.action-row:active { background: #fafaff; }
.action-icon { display: flex; flex: 0 0 62rpx; align-items: center; justify-content: center; width: 62rpx; height: 62rpx; border-radius: 18rpx; font-size: 22rpx; font-weight: 900; }
.action-icon.purple { color: #5b51c2; background: #ebe9ff; }
.action-icon.green { color: #327c67; background: #e5f7f0; }
.action-icon.red { color: #c7435c; background: #fff0f3; }
.action-copy { flex: 1; min-width: 0; margin-left: 19rpx; }
.action-title { font-size: 25rpx; font-weight: 800; }
.action-desc { margin-top: 6rpx; color: #929aaa; font-size: 19rpx; line-height: 1.45; }
.action-arrow { margin-left: 15rpx; color: #8f87cf; font-size: 40rpx; font-weight: 300; }
.danger-title,.danger-arrow { color: #c7435c; }
.action-panel { padding: 3rpx 25rpx 27rpx; border-top: 1rpx solid #eeeff4; }
.first-field { margin-top: 24rpx; }
.field { margin-top: 22rpx; }
.field-label { font-size: 23rpx; }
.field-input { height: 86rpx; font-size: 25rpx; }
.code-row { display: flex; gap: 13rpx; }
.code-input { flex: 1; min-width: 0; }
.code-btn { flex: 0 0 205rpx; width: 205rpx; height: 86rpx; padding: 0; color: #5b51c2; background: #ebe9ff; border-radius: 20rpx; font-size: 22rpx; font-weight: 750; line-height: 86rpx; }
.danger-block.expanded { border-color: #ffd5dc; box-shadow: 0 15rpx 38rpx rgba(190,55,79,.08); }
.danger-panel { background: #fffbfc; border-top-color: #ffe1e6; }
.warning-box { display: flex; margin-top: 24rpx; padding: 21rpx; background: #fff0f3; border-radius: 20rpx; }
.warning-mark { display: flex; flex: 0 0 48rpx; align-items: center; justify-content: center; width: 48rpx; height: 48rpx; margin-right: 15rpx; color: #fff; background: #d94a64; border-radius: 50%; font-size: 25rpx; font-weight: 900; }
.warning-title { color: #a72f48; font-size: 23rpx; font-weight: 800; }
.warning-desc { margin-top: 6rpx; color: #9f6874; font-size: 19rpx; line-height: 1.55; }
.danger-confirm-btn { height: 86rpx; margin-top: 22rpx; color: #fff; background: linear-gradient(135deg,#ce3e58,#e35b71); border-radius: 22rpx; font-size: 27rpx; font-weight: 750; line-height: 86rpx; box-shadow: 0 12rpx 25rpx rgba(206,62,88,.18); }
.security-note { display: flex; align-items: center; margin-top: 21rpx; padding: 21rpx 23rpx; color: #767e91; background: #eef0f6; border-radius: 22rpx; font-size: 19rpx; line-height: 1.55; }
.note-mark { display: flex; flex: 0 0 47rpx; align-items: center; justify-content: center; width: 47rpx; height: 47rpx; margin-right: 14rpx; color: #5d52c7; background: #fff; border-radius: 15rpx; font-size: 22rpx; font-weight: 900; }
.login-card { margin-top: 25rpx; padding: 43rpx 30rpx 31rpx; text-align: center; background: #fff; border-radius: 28rpx; box-shadow: 0 14rpx 38rpx rgba(36,55,86,.07); }
.login-icon { display: flex; align-items: center; justify-content: center; width: 78rpx; height: 78rpx; margin: 0 auto; color: #5b51c2; background: #ebe9ff; border-radius: 23rpx; font-size: 27rpx; font-weight: 900; }
.login-title { margin-top: 20rpx; font-size: 29rpx; font-weight: 850; }
.login-desc { margin-top: 8rpx; color: #929aaa; font-size: 21rpx; }
</style>
