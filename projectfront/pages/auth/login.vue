<template>
  <view class="auth-page">
    <view class="brand-mark">知</view>
    <view class="page-title">欢迎回来</view>
    <view class="page-subtitle">登录后开始 AI 起名，并查看你的剩余次数。</view>

    <view class="card auth-card">
      <view class="field">
        <text class="field-label">邮箱</text>
        <input v-model.trim="form.email" class="field-input" type="text" placeholder="请输入注册邮箱" />
      </view>
      <view class="field">
        <text class="field-label">密码</text>
        <input v-model="form.password" class="field-input" password maxlength="64" placeholder="请输入密码" />
      </view>
      <button class="primary-btn btn-gap" :loading="loading" :disabled="loading" @click="submit">
        登录
      </button>
      <button class="link-btn" @click="goRegister">还没有账号？立即注册</button>
      <button class="admin-link-btn" @click="goAdminLogin">管理员登录</button>
    </view>
  </view>
</template>

<script>
import { api } from '../../api'
import { saveLogin } from '../../utils/auth'

export default {
  data() {
    return {
      loading: false,
      form: { email: '', password: '' }
    }
  },
  methods: {
    async submit() {
      if (!this.form.email || !this.form.password) {
        uni.showToast({ title: '请填写邮箱和密码', icon: 'none' })
        return
      }
      this.loading = true
      try {
        const data = await api.login(this.form)
        saveLogin(data)
        uni.showToast({ title: '登录成功', icon: 'success' })
        setTimeout(() => uni.switchTab({ url: '/pages/index/index' }), 500)
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 2600 })
      } finally {
        this.loading = false
      }
    },
    goRegister() {
      uni.navigateTo({ url: '/pages/auth/register' })
    },
    goAdminLogin() {
      uni.navigateTo({ url: '/pages/admin/login' })
    }
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  padding: 100rpx 34rpx 60rpx;
  background: radial-gradient(circle at 90% 4%, #e7e2ff 0, transparent 34%), #f5f7fb;
}
.brand-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 92rpx;
  height: 92rpx;
  margin-bottom: 42rpx;
  color: #fff;
  background: linear-gradient(135deg, #6257e8, #9a72ef);
  border-radius: 26rpx;
  box-shadow: 0 18rpx 35rpx rgba(98, 87, 232, 0.25);
  font-size: 44rpx;
  font-weight: 800;
}
.auth-card { margin-top: 50rpx; }
.link-btn {
  margin-top: 22rpx;
  color: #6257e8;
  background: transparent;
  font-size: 25rpx;
}
.admin-link-btn {
  margin-top: 4rpx;
  color: #6f788b;
  background: transparent;
  font-size: 23rpx;
}
</style>
