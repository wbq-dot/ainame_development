<template>
  <view class="admin-login-page">
    <view class="admin-brand">
      <view class="brand-icon">管</view>
      <view class="brand-text">
        <view class="brand-eyebrow">ADMIN CONSOLE</view>
        <view class="brand-title">管理员登录</view>
      </view>
    </view>

    <view class="security-note">此入口仅允许管理员账号进入，普通用户请返回用户登录。</view>

    <view class="login-card">
      <view class="field first-field">
        <text class="field-label">管理员邮箱</text>
        <input v-model.trim="form.email" class="field-input admin-input" type="text" placeholder="请输入管理员邮箱" />
      </view>
      <view class="field">
        <text class="field-label">密码</text>
        <input v-model="form.password" class="field-input admin-input" password maxlength="64" placeholder="请输入管理员密码" @confirm="submit" />
      </view>
      <button class="admin-login-btn" :loading="loading" :disabled="loading" @click="submit">进入管理后台</button>
      <button v-if="showBootstrap" class="bootstrap-link" @click="goBootstrap">初始化首个管理员</button>
      <button class="user-login-link" @click="goUserLogin">返回普通用户登录</button>
    </view>

    <view class="safe-tip">
      <text>安全提示</text>
      <view>管理员操作会记录到审计日志；请勿在公共设备保存管理员账号。</view>
    </view>
  </view>
</template>

<script>
import { api } from '../../api'
import { clearLogin, saveLogin } from '../../utils/auth'

export default {
  data() {
    return {
      loading: false,
      showBootstrap: false,
      form: { email: '', password: '' }
    }
  },
  onShow() {
    this.loadBootstrapStatus()
  },
  methods: {
    async loadBootstrapStatus() {
      try {
        const status = await api.getAdminBootstrapStatus()
        this.showBootstrap = Boolean(status.initialization_required && status.bootstrap_enabled)
      } catch (error) {
        this.showBootstrap = false
      }
    },
    async submit() {
      if (!this.form.email || !this.form.password) {
        uni.showToast({ title: '请输入管理员邮箱和密码', icon: 'none' })
        return
      }
      this.loading = true
      try {
        const data = await api.login(this.form)
        if (!data.user || data.user.role !== 'admin') {
          clearLogin()
          uni.showModal({
            title: '无管理员权限',
            content: '账号验证成功，但该账号不是管理员，无法进入管理后台。',
            showCancel: false
          })
          return
        }
        saveLogin(data)
        uni.showToast({ title: '管理员登录成功', icon: 'success' })
        setTimeout(() => uni.redirectTo({ url: '/pages/admin/users' }), 450)
      } catch (error) {
        clearLogin()
        uni.showToast({ title: error.message, icon: 'none', duration: 2800 })
      } finally {
        this.loading = false
      }
    },
    goUserLogin() {
      uni.navigateBack()
    },
    goBootstrap() {
      uni.navigateTo({ url: '/pages/admin/bootstrap' })
    }
  }
}
</script>

<style scoped>
.admin-login-page { min-height: 100vh; padding: 90rpx 34rpx 60rpx; color: #edf0f7; background: radial-gradient(circle at 90% 0, #444b69 0, transparent 28%), linear-gradient(160deg, #141927, #252b3e); }
.admin-brand { display: flex; align-items: center; }
.brand-icon { display: flex; align-items: center; justify-content: center; width: 92rpx; height: 92rpx; color: #292d42; background: linear-gradient(135deg, #f4d98b, #dcb85b); border-radius: 26rpx; box-shadow: 0 17rpx 36rpx rgba(0,0,0,.25); font-size: 34rpx; font-weight: 850; }
.brand-text { margin-left: 22rpx; }
.brand-eyebrow { color: #e6c978; font-size: 17rpx; font-weight: 800; letter-spacing: 4rpx; }
.brand-title { margin-top: 6rpx; font-size: 43rpx; font-weight: 850; }
.security-note { margin-top: 38rpx; padding: 18rpx 21rpx; color: #c9cedb; background: rgba(255,255,255,.07); border: 1rpx solid rgba(255,255,255,.09); border-radius: 17rpx; font-size: 21rpx; line-height: 1.55; }
.login-card { margin-top: 25rpx; padding: 32rpx; color: #1e2638; background: #fff; border-radius: 29rpx; box-shadow: 0 24rpx 55rpx rgba(0,0,0,.22); }
.first-field { margin-top: 0; }
.admin-input { background: #f1f3f7; }
.admin-login-btn { height: 88rpx; margin-top: 30rpx; color: #272b3f; background: linear-gradient(135deg, #f2d586, #dfbd62); border-radius: 21rpx; box-shadow: 0 13rpx 26rpx rgba(210,174,79,.25); font-size: 27rpx; font-weight: 800; line-height: 88rpx; }
.bootstrap-link { margin-top: 17rpx; color: #66531e; background: #fbf4df; border: 1rpx solid #ead69a; font-size: 23rpx; }
.user-login-link { margin-top: 17rpx; color: #687286; background: transparent; font-size: 23rpx; }
.safe-tip { margin-top: 30rpx; padding: 22rpx; color: #9ea6b8; border-top: 1rpx solid rgba(255,255,255,.1); font-size: 20rpx; line-height: 1.6; }
.safe-tip text { display: block; margin-bottom: 5rpx; color: #e2c774; font-weight: 700; }
</style>
