<template>
  <view class="page-shell settings-page">
    <view class="settings-hero"><view><view class="hero-tag">PREFERENCES</view><view class="hero-title">设置与安全</view><view class="hero-desc">管理界面显示与当前设备上的账号状态。</view></view><view class="gear-art"><view class="gear">⚙</view><view class="shield">✓</view></view></view>

    <view id="display" class="setting-section"><view class="section-title">界面显示</view><view class="section-note">偏好保存在当前设备。</view>
      <view class="settings-card">
        <view class="setting-row"><view><view class="row-title">大号文字</view><view class="row-desc">放大 H5 页面中的整体文字和间距</view></view><switch color="#6257e8" :checked="preferences.fontSize === 'large'" @change="setLargeText" /></view>
        <view class="setting-row"><view><view class="row-title">高对比度</view><view class="row-desc">增强底部导航与正文颜色区分</view></view><switch color="#6257e8" :checked="preferences.highContrast" @change="setHighContrast" /></view>
        <view class="setting-row"><view><view class="row-title">减少动画</view><view class="row-desc">关闭不必要的过渡效果，更加稳定</view></view><switch color="#6257e8" :checked="preferences.reduceMotion" @change="setReduceMotion" /></view>
      </view>
    </view>

    <view id="security" class="setting-section"><view class="section-title">账号安全</view><view class="section-note">仅展示当前登录状态，不显示令牌或密码。</view>
      <view class="security-card"><view class="security-avatar">{{ avatarText }}</view><view class="security-main"><view class="security-name">{{ user ? user.username : '尚未登录' }}</view><view class="security-email">{{ user ? maskEmail(user.email) : '登录后查看安全信息' }}</view></view><view class="safe-badge">{{ user ? '已登录' : '未登录' }}</view></view>
      <view class="security-list">
        <view><text class="security-icon">密</text><view><view>登录凭证</view><text>令牌仅保存在当前设备，不在页面中展示</text></view><text class="state-text">受保护</text></view>
        <view><text class="security-icon">邮</text><view><view>绑定邮箱</view><text>{{ user ? maskEmail(user.email) : '未绑定' }}</text></view><text class="state-text">{{ user ? '已验证' : '—' }}</text></view>
      </view>
      <button v-if="!user" class="primary-btn btn-gap" @click="goLogin">登录账号</button>
      <button v-else class="ghost-btn btn-gap" @click="reverify">重新登录验证</button>
    </view>
  </view>
</template>

<script>
import { getUser } from '../../utils/auth'
import { getDisplayPreferences, saveDisplayPreferences } from '../../utils/preferences'

export default {
  data() { return { user: null, preferences: getDisplayPreferences() } },
  computed: { avatarText() { return this.user && this.user.username ? this.user.username.slice(0, 1).toUpperCase() : '访' } },
  onShow() { this.user = getUser(); this.preferences = getDisplayPreferences() },
  methods: {
    maskEmail(email) { if (!email || !email.includes('@')) return email || ''; const [name, domain] = email.split('@'); return `${name.slice(0, 2)}${name.length > 2 ? '***' : '*'}@${domain}` },
    update(key, value) { this.preferences = { ...this.preferences, [key]: value }; saveDisplayPreferences(this.preferences); uni.showToast({ title: '设置已保存', icon: 'success' }) },
    setLargeText(event) { this.update('fontSize', event.detail.value ? 'large' : 'standard') },
    setHighContrast(event) { this.update('highContrast', event.detail.value) },
    setReduceMotion(event) { this.update('reduceMotion', event.detail.value) },
    goLogin() { uni.navigateTo({ url: '/pages/auth/login' }) },
    reverify() { uni.showModal({ title: '重新登录验证', content: '将打开登录页。现有登录状态不会在此步骤中删除，提交新登录信息成功后才会替换。', confirmText: '打开登录页', success: ({ confirm }) => { if (confirm) this.goLogin() } }) }
  }
}
</script>

<style scoped>
.settings-page { background: radial-gradient(circle at 95% 3%,#e9e5ff 0,transparent 26%),#f5f7fb; }
.settings-hero { position: relative; min-height: 235rpx; padding: 35rpx; overflow: hidden; color: #fff; background: linear-gradient(140deg,#222843,#48527e); border-radius: 34rpx; }
.hero-tag { color: #c9d0ef; font-size: 17rpx; font-weight: 850; letter-spacing: 3rpx; }
.hero-title { margin-top: 16rpx; font-size: 42rpx; font-weight: 900; }
.hero-desc { width: 66%; margin-top: 13rpx; color: #d9def2; font-size: 21rpx; line-height: 1.55; }
.gear-art { position: absolute; top: 0; right: 0; width: 230rpx; height: 100%; }
.gear { position: absolute; top: 36rpx; right: 27rpx; color: #f2cf79; font-size: 100rpx; transform: rotate(12deg); }
.shield { position: absolute; right: 108rpx; bottom: 28rpx; display: flex; align-items: center; justify-content: center; width: 73rpx; height: 83rpx; color: #3b496e; background: #8fe0c7; border-radius: 36rpx 36rpx 45rpx 45rpx; font-size: 35rpx; font-weight: 900; }
.setting-section { margin-top: 32rpx; }
.section-title { font-size: 31rpx; font-weight: 850; }
.section-note { margin-top: 7rpx; color: #929aaa; font-size: 21rpx; }
.settings-card,.security-list { margin-top: 18rpx; padding: 0 27rpx; background: #fff; border-radius: 27rpx; box-shadow: 0 12rpx 35rpx rgba(36,55,86,.06); }
.setting-row { display: flex; align-items: center; justify-content: space-between; min-height: 112rpx; border-top: 1rpx solid #eceef3; }
.setting-row:first-child { border-top: 0; }
.row-title { font-size: 25rpx; font-weight: 760; }
.row-desc { margin-top: 5rpx; color: #929aaa; font-size: 19rpx; }
.security-card { display: flex; align-items: center; margin-top: 18rpx; padding: 27rpx; color: #fff; background: linear-gradient(135deg,#5147b9,#7968dc); border-radius: 27rpx; }
.security-avatar { display: flex; align-items: center; justify-content: center; width: 75rpx; height: 75rpx; color: #5147b9; background: #fff; border-radius: 22rpx; font-size: 31rpx; font-weight: 900; }
.security-main { flex: 1; margin-left: 17rpx; }
.security-name { font-size: 27rpx; font-weight: 850; }
.security-email { margin-top: 5rpx; color: #ddd9ff; font-size: 20rpx; }
.safe-badge { padding: 8rpx 13rpx; color: #4f459f; background: #fff; border-radius: 999rpx; font-size: 18rpx; }
.security-list > view { display: flex; align-items: center; min-height: 112rpx; border-top: 1rpx solid #eceef3; }
.security-list > view:first-child { border-top: 0; }
.security-icon { display: flex; align-items: center; justify-content: center; width: 57rpx; height: 57rpx; margin-right: 17rpx; color: #5b51c2; background: #ebe9ff; border-radius: 17rpx; font-size: 21rpx; font-weight: 850; }
.security-list view > view { flex: 1; font-size: 24rpx; font-weight: 720; }
.security-list view > view text { display: block; margin-top: 4rpx; color: #949cab; font-size: 18rpx; font-weight: 400; }
.state-text { color: #39866e; font-size: 19rpx; }
</style>
