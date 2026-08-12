<template>
  <view class="dev-auth">
    <view class="brand"><text>OPEN PLATFORM</text><view>开发者开放平台</view><small>独立账号、API Key、调用统计与批量命名</small></view>
    <view class="auth-card">
      <view class="tabs"><view :class="{ active: mode === 'login' }" @click="mode='login'">登录</view><view :class="{ active: mode === 'register' }" @click="mode='register'">注册</view></view>
      <input v-if="mode==='register'" v-model.trim="form.name" placeholder="开发者或企业名称" />
      <input v-model.trim="form.email" placeholder="邮箱" />
      <input v-model="form.password" password placeholder="密码（至少8位）" />
      <template v-if="mode==='register'">
        <input v-model="form.confirm_password" password placeholder="再次输入密码" />
        <view class="code-row"><input v-model.trim="form.code" maxlength="4" placeholder="邮箱验证码" /><button @click="sendCode">发送验证码</button></view>
        <input v-model.trim="form.referral_code" maxlength="20" placeholder="推广码（选填）" />
      </template>
      <button class="submit" :loading="loading" @click="submit">{{ mode==='login' ? '登录控制台' : '创建开发者账号' }}</button>
      <button class="back" @click="goHome">返回普通用户端</button>
    </view>
  </view>
</template>
<script>
import { developerApi } from '../../api/developer'
import { saveDeveloperLogin } from '../../utils/developer-auth'
export default {
  data() { return { mode: 'login', loading: false, form: { name: '', email: '', password: '', confirm_password: '', code: '', referral_code: '' } } },
  methods: {
    async sendCode() { if (!this.form.email) return uni.showToast({ title: '请先填写邮箱', icon: 'none' }); try { await developerApi.sendCode(this.form.email); uni.showToast({ title: '验证码已发送', icon: 'success' }) } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) } },
    async submit() {
      this.loading = true
      try {
        if (this.mode === 'register') { await developerApi.register(this.form); this.mode = 'login'; uni.showModal({ title: '注册成功', content: '邮箱已验证，开发者能力已开通，请登录。', showCancel: false }) }
        else { const data = await developerApi.login({ email: this.form.email, password: this.form.password }); saveDeveloperLogin(data); uni.reLaunch({ url: '/pages/developer/console' }) }
      } catch (e) { uni.showToast({ title: e.message, icon: 'none', duration: 3000 }) } finally { this.loading = false }
    },
    goHome() { uni.reLaunch({ url: '/pages/account/index' }) }
  }
}
</script>
<style scoped>
.dev-auth{min-height:100vh;padding:90rpx 28rpx;background:radial-gradient(circle at 80% 10%,#234d72,transparent 35%),#081827}.brand{color:#fff;text-align:center}.brand text{color:#56d6c9;font-size:18rpx;font-weight:800;letter-spacing:5rpx}.brand view{margin-top:20rpx;font-size:48rpx;font-weight:900}.brand small{display:block;margin-top:14rpx;color:#9eb2c5;font-size:22rpx}.auth-card{max-width:720rpx;margin:50rpx auto 0;padding:34rpx;background:#fff;border-radius:30rpx}.tabs{display:flex;margin-bottom:20rpx;padding:7rpx;background:#edf2f6;border-radius:17rpx}.tabs view{flex:1;padding:17rpx;text-align:center;color:#6a7786;border-radius:12rpx}.tabs .active{color:#fff;background:#0a5261;font-weight:800}input{height:88rpx;margin-top:16rpx;padding:0 22rpx;background:#f2f5f7;border-radius:17rpx;font-size:25rpx}.code-row{display:flex;gap:12rpx}.code-row input{flex:1}.code-row button{width:210rpx;height:88rpx;margin-top:16rpx;color:#0a6672;background:#dff6f3;border-radius:17rpx;font-size:22rpx;line-height:88rpx}.submit,.back{height:88rpx;margin-top:25rpx;border-radius:18rpx;line-height:88rpx}.submit{color:#fff;background:#0a5967;font-weight:800}.back{color:#607083;background:#edf1f4}
</style>
