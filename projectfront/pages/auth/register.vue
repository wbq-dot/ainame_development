<template>
  <view class="auth-page">
    <view class="page-title">创建账号</view>
    <view class="page-subtitle">注册成功后，后端会赠送3次起名机会。</view>

    <view class="card">
      <view class="field">
        <text class="field-label">邮箱</text>
        <view class="code-row">
          <input v-model.trim="form.email" class="field-input code-input" type="text" placeholder="邮箱地址" />
          <button class="code-btn" :disabled="sendingCode || countdown > 0" @click="sendCode">
            {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
          </button>
        </view>
      </view>
      <view class="field">
        <text class="field-label">用户名</text>
        <input v-model.trim="form.username" class="field-input" maxlength="8" placeholder="3至8个字符" />
      </view>
      <view class="field">
        <text class="field-label">验证码</text>
        <input v-model.trim="form.code" class="field-input" type="number" maxlength="4" placeholder="4位邮箱验证码" />
      </view>
      <view class="field">
        <text class="field-label">密码</text>
        <input v-model="form.password" class="field-input" password maxlength="64" placeholder="8至64位密码" />
      </view>
      <view class="field">
        <text class="field-label">确认密码</text>
        <input v-model="form.confirm_password" class="field-input" password maxlength="64" placeholder="再次输入密码" />
      </view>
      <button class="primary-btn btn-gap" :loading="loading" :disabled="loading" @click="submit">注册</button>
    </view>
  </view>
</template>

<script>
import { api } from '../../api'

export default {
  data() {
    return {
      loading: false,
      sendingCode: false,
      countdown: 0,
      timer: null,
      form: { email: '', username: '', code: '', password: '', confirm_password: '' }
    }
  },
  onUnload() {
    if (this.timer) clearInterval(this.timer)
  },
  methods: {
    validEmail() {
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.form.email)
    },
    async sendCode() {
      if (!this.validEmail()) {
        uni.showToast({ title: '请输入正确的邮箱', icon: 'none' })
        return
      }
      this.sendingCode = true
      try {
        await api.sendRegisterCode(this.form.email)
        this.countdown = 60
        this.timer = setInterval(() => {
          this.countdown -= 1
          if (this.countdown <= 0) clearInterval(this.timer)
        }, 1000)
        uni.showToast({ title: '验证码已发送', icon: 'success' })
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 2600 })
      } finally {
        this.sendingCode = false
      }
    },
    async submit() {
      if (!this.validEmail() || this.form.username.length < 3 || this.form.username.length > 8) {
        uni.showToast({ title: '请检查邮箱和用户名', icon: 'none' })
        return
      }
      if (this.form.code.length !== 4 || this.form.password.length < 8 || this.form.password.length > 64) {
        uni.showToast({ title: '验证码应为4位，密码应为8至64位', icon: 'none' })
        return
      }
      if (this.form.password !== this.form.confirm_password) {
        uni.showToast({ title: '两次输入的密码不一致', icon: 'none' })
        return
      }
      this.loading = true
      try {
        const data = await api.register(this.form)
        uni.showModal({
          title: '注册成功',
          content: data.messages || '请使用新账号登录。',
          showCancel: false,
          success: () => uni.redirectTo({ url: '/pages/auth/login' })
        })
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 2800 })
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  padding: 46rpx 30rpx 70rpx;
  background: radial-gradient(circle at 10% 0, #e4f2ff 0, transparent 30%), #f5f7fb;
}
.code-row { display: flex; gap: 14rpx; }
.code-input { flex: 1; min-width: 0; }
.code-btn {
  width: 210rpx;
  height: 92rpx;
  padding: 0;
  color: #6257e8;
  background: #ebe9ff;
  border-radius: 20rpx;
  font-size: 24rpx;
  font-weight: 700;
  line-height: 92rpx;
}
</style>
