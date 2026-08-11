<template>
  <view class="bootstrap-page">
    <view class="hero">
      <view class="hero-tag">FIRST-TIME SETUP</view>
      <view class="hero-title">初始化首个管理员</view>
      <view class="hero-desc">此入口仅在系统尚无管理员且后端已配置部署密钥时可用。</view>
    </view>

    <view v-if="checking" class="status-card">正在检查初始化状态…</view>
    <view v-else-if="!available" class="status-card unavailable">
      <view class="status-title">初始化入口不可用</view>
      <view class="status-desc">{{ unavailableMessage }}</view>
      <button class="secondary-btn" @click="goLogin">返回管理员登录</button>
    </view>

    <view v-else class="form-card">
      <view class="field first-field">
        <text class="field-label">管理员邮箱</text>
        <input v-model.trim="form.email" class="field-input" type="text" maxlength="100" placeholder="请输入管理员邮箱" />
      </view>
      <view class="field">
        <text class="field-label">用户名</text>
        <input v-model.trim="form.username" class="field-input" maxlength="8" placeholder="3-8 个字符" />
      </view>
      <view class="field">
        <text class="field-label">密码</text>
        <input v-model="form.password" class="field-input" password maxlength="64" placeholder="8-64 位" />
      </view>
      <view class="field">
        <text class="field-label">确认密码</text>
        <input v-model="confirmPassword" class="field-input" password maxlength="64" placeholder="请再次输入密码" />
      </view>
      <view class="field">
        <text class="field-label">部署密钥</text>
        <input v-model="form.bootstrap_secret" class="field-input" password maxlength="512" placeholder="请输入后端配置的部署密钥" @confirm="submit" />
      </view>
      <view class="security-tip">部署密钥只用于本次请求，不会保存到前端存储或数据库。</view>
      <button class="primary-btn" :loading="submitting" :disabled="submitting" @click="submit">创建首任管理员</button>
      <button class="back-btn" @click="goLogin">返回登录</button>
    </view>
  </view>
</template>

<script>
import { api } from '../../api'
import { enforceAdminConsoleRoute } from '../../utils/auth'

export default {
  data() {
    return {
      checking: true,
      available: false,
      unavailableMessage: '系统已经完成初始化，或后端尚未配置部署密钥。',
      submitting: false,
      confirmPassword: '',
      form: { email: '', username: '', password: '', bootstrap_secret: '' }
    }
  },
  onShow() {
    if (enforceAdminConsoleRoute()) return
    this.loadStatus()
  },
  methods: {
    async loadStatus() {
      this.checking = true
      try {
        const status = await api.getAdminBootstrapStatus()
        this.available = Boolean(status.initialization_required && status.bootstrap_enabled)
        if (!status.initialization_required) this.unavailableMessage = '系统已经存在管理员，请直接登录。'
        else if (!status.bootstrap_enabled) this.unavailableMessage = '后端未配置管理员部署密钥。'
      } catch (error) {
        this.available = false
        this.unavailableMessage = error.message || '无法查询初始化状态。'
      } finally {
        this.checking = false
      }
    },
    validate() {
      if (!this.form.email || !this.form.username || !this.form.password || !this.confirmPassword || !this.form.bootstrap_secret) return '请填写全部字段'
      if (!/^\S+@\S+\.\S+$/.test(this.form.email)) return '请输入正确的邮箱地址'
      if (this.form.username.length < 3 || this.form.username.length > 8) return '用户名长度必须为 3-8 个字符'
      if (this.form.password.length < 8 || this.form.password.length > 64) return '密码长度必须为 8-64 位'
      if (this.form.password !== this.confirmPassword) return '两次输入的密码不一致'
      return ''
    },
    async submit() {
      const validationError = this.validate()
      if (validationError) {
        uni.showToast({ title: validationError, icon: 'none' })
        return
      }
      this.submitting = true
      try {
        await api.bootstrapAdmin(this.form)
        this.form.bootstrap_secret = ''
        uni.showModal({
          title: '初始化成功',
          content: '首任管理员已经创建，请使用新账号登录。',
          showCancel: false,
          success: () => uni.redirectTo({ url: '/pages/admin/login' })
        })
      } catch (error) {
        this.form.bootstrap_secret = ''
        uni.showToast({ title: error.message, icon: 'none', duration: 3000 })
        await this.loadStatus()
      } finally {
        this.submitting = false
      }
    },
    goLogin() {
      uni.redirectTo({ url: '/pages/admin/login' })
    }
  }
}
</script>

<style scoped>
.bootstrap-page { min-height: 100vh; padding: 70rpx 34rpx 60rpx; color: #edf0f7; background: radial-gradient(circle at 90% 0, #444b69 0, transparent 28%), linear-gradient(160deg, #141927, #252b3e); }
.hero { padding: 12rpx 4rpx 30rpx; }
.hero-tag { color: #e6c978; font-size: 17rpx; font-weight: 800; letter-spacing: 4rpx; }
.hero-title { margin-top: 10rpx; font-size: 42rpx; font-weight: 850; }
.hero-desc { margin-top: 16rpx; color: #bfc5d2; font-size: 22rpx; line-height: 1.65; }
.form-card,.status-card { margin-top: 10rpx; padding: 32rpx; color: #202638; background: #fff; border-radius: 29rpx; box-shadow: 0 24rpx 55rpx rgba(0,0,0,.22); }
.field { margin-top: 24rpx; }
.first-field { margin-top: 0; }
.field-label { display: block; margin-bottom: 11rpx; color: #4f586c; font-size: 22rpx; font-weight: 700; }
.field-input { height: 82rpx; padding: 0 22rpx; background: #f1f3f7; border: 1rpx solid #e5e8ef; border-radius: 17rpx; font-size: 24rpx; }
.security-tip { margin-top: 24rpx; padding: 17rpx; color: #746330; background: #fbf5e4; border-radius: 15rpx; font-size: 20rpx; line-height: 1.55; }
.primary-btn { height: 88rpx; margin-top: 28rpx; color: #272b3f; background: linear-gradient(135deg, #f2d586, #dfbd62); border-radius: 21rpx; font-size: 27rpx; font-weight: 800; line-height: 88rpx; }
.back-btn,.secondary-btn { margin-top: 17rpx; color: #687286; background: transparent; font-size: 23rpx; }
.status-card { color: #687286; text-align: center; }
.status-title { color: #262d40; font-size: 29rpx; font-weight: 800; }
.status-desc { margin-top: 15rpx; font-size: 22rpx; line-height: 1.6; }
</style>
