<template>
  <view class="page-shell create-hub">
    <view class="page-title">创作工具</view>
    <view class="page-subtitle">每项工具拥有独立空间，操作更专注，结果更清晰。</view>

    <view class="hero-art">
      <view class="hero-copy">
        <view class="hero-kicker">CREATIVE LAB</view>
        <view class="hero-title">把规则变成灵感<br />把灵感变成标识</view>
        <view class="hero-note">知识沉淀 · 品牌视觉</view>
      </view>
      <view class="art-board">
        <view class="art-book"><text></text><text></text><text></text></view>
        <view class="art-spark">✦</view>
        <view class="art-logo">A</view>
        <view class="art-dot dot-one"></view>
        <view class="art-dot dot-two"></view>
      </view>
    </view>

    <view class="tool-list">
      <view class="tool-entry knowledge-entry" @click="openTool('/pages/knowledge/index')">
        <view class="entry-art knowledge-art">
          <view class="folder-back"></view>
          <view class="folder-front"><view class="folder-line"></view><view class="folder-line short"></view></view>
          <view class="entry-badge">资料</view>
        </view>
        <view class="entry-content">
          <view class="entry-eyebrow">KNOWLEDGE BASE</view>
          <view class="entry-title">专属知识库</view>
          <view class="entry-desc">上传 PDF / TXT，让人名、企业名和宠物名都参考你的专属资料。</view>
          <view class="entry-link">进入知识库 <text>→</text></view>
        </view>
      </view>

      <view class="tool-entry logo-entry" @click="openTool('/pages/logo/index')">
        <view class="entry-content">
          <view class="entry-eyebrow">LOGO STUDIO</view>
          <view class="entry-title">企业 Logo 生成</view>
          <view class="entry-desc">输入企业名称与风格，让模型生成一枚独立品牌标识。</view>
          <view class="entry-link">进入 Logo 图案 <text>→</text></view>
        </view>
        <view class="entry-art logo-art">
          <view class="logo-ring ring-one"></view>
          <view class="logo-ring ring-two"></view>
          <view class="logo-letter">Z</view>
          <view class="logo-star">✦</view>
        </view>
      </view>
    </view>

    <view v-if="!loggedIn" class="login-tip" @click="goLogin">
      <view class="tip-icon">钥</view>
      <view class="tip-main"><view class="tip-title">登录后即可使用</view><view class="tip-desc">知识库和 Logo 内容都会归入你的个人账号</view></view>
      <view class="tip-arrow">›</view>
    </view>
  </view>
</template>

<script>
import { getAccessToken } from '../../utils/auth'

export default {
  data() {
    return { loggedIn: false }
  },
  onShow() {
    this.loggedIn = Boolean(getAccessToken())
    const target = uni.getStorageSync('create_default_mode')
    uni.removeStorageSync('create_default_mode')
    if (this.loggedIn && target === 'knowledge') uni.navigateTo({ url: '/pages/knowledge/index' })
    if (this.loggedIn && target === 'logo') uni.switchTab({ url: '/pages/logo/index' })
  },
  methods: {
    goLogin() { uni.navigateTo({ url: '/pages/auth/login' }) },
    openTool(url) {
      if (!this.loggedIn) {
        uni.showModal({
          title: '登录后使用',
          content: '专属知识库和 Logo 作品需要保存到个人账号，请先登录。',
          confirmText: '去登录',
          success: ({ confirm }) => { if (confirm) this.goLogin() }
        })
        return
      }
      if (url === '/pages/logo/index') uni.switchTab({ url })
      else uni.navigateTo({ url })
    }
  }
}
</script>

<style scoped>
.create-hub { overflow: hidden; background: radial-gradient(circle at 95% 3%, #efe9ff 0, transparent 26%), #f5f7fb; }
.hero-art { position: relative; display: flex; min-height: 280rpx; margin-top: 30rpx; padding: 34rpx; overflow: hidden; color: #fff; background: linear-gradient(145deg, #252750, #5146b8 62%, #735edf); border-radius: 34rpx; box-shadow: 0 22rpx 50rpx rgba(70, 59, 164, .22); }
.hero-copy { position: relative; z-index: 2; width: 62%; }
.hero-kicker, .entry-eyebrow { font-size: 18rpx; font-weight: 800; letter-spacing: 3rpx; }
.hero-kicker { color: #cfcaff; }
.hero-title { margin-top: 18rpx; font-size: 38rpx; font-weight: 850; line-height: 1.45; }
.hero-note { margin-top: 16rpx; color: #ddd9ff; font-size: 22rpx; }
.art-board { position: absolute; top: 0; right: 0; width: 290rpx; height: 100%; }
.art-book { position: absolute; right: 70rpx; bottom: 54rpx; width: 112rpx; height: 86rpx; padding: 22rpx 18rpx; background: #fff; border-radius: 12rpx 24rpx 24rpx 12rpx; box-shadow: -12rpx 16rpx 28rpx rgba(15, 14, 61, .2); transform: rotate(-9deg); }
.art-book::before { position: absolute; top: 0; bottom: 0; left: 13rpx; width: 4rpx; content: ''; background: #f1b563; }
.art-book text { display: block; width: 62rpx; height: 5rpx; margin-bottom: 9rpx; background: #c9c5e8; border-radius: 9rpx; }
.art-logo { position: absolute; top: 43rpx; right: 29rpx; display: flex; align-items: center; justify-content: center; width: 102rpx; height: 102rpx; color: #5146b8; background: #f7c977; border-radius: 31rpx; box-shadow: 0 14rpx 30rpx rgba(18, 17, 65, .22); font-size: 55rpx; font-weight: 900; transform: rotate(10deg); }
.art-spark { position: absolute; top: 30rpx; right: 155rpx; color: #fff; font-size: 38rpx; }
.art-dot { position: absolute; border: 5rpx solid rgba(255,255,255,.4); border-radius: 50%; }
.dot-one { right: 15rpx; bottom: 25rpx; width: 48rpx; height: 48rpx; }
.dot-two { top: 25rpx; right: 8rpx; width: 20rpx; height: 20rpx; background: #77dec8; border: 0; }
.tool-list { margin-top: 26rpx; }
.tool-entry { display: flex; align-items: center; min-height: 260rpx; margin-top: 22rpx; padding: 28rpx; overflow: hidden; background: #fff; border-radius: 30rpx; box-shadow: 0 14rpx 38rpx rgba(36,55,86,.07); }
.tool-entry:active { transform: scale(.99); }
.entry-content { position: relative; z-index: 2; flex: 1; min-width: 0; }
.entry-eyebrow { color: #8c83c8; }
.entry-title { margin-top: 10rpx; color: #252452; font-size: 34rpx; font-weight: 850; }
.entry-desc { margin-top: 12rpx; color: #7b8496; font-size: 22rpx; line-height: 1.65; }
.entry-link { margin-top: 20rpx; color: #554bc2; font-size: 23rpx; font-weight: 760; }
.entry-link text { margin-left: 8rpx; }
.entry-art { position: relative; flex: 0 0 210rpx; height: 190rpx; }
.knowledge-entry { background: linear-gradient(135deg, #fff, #effaf6); }
.knowledge-art { margin-right: 18rpx; }
.folder-back { position: absolute; top: 35rpx; left: 18rpx; width: 160rpx; height: 110rpx; background: #8ad7bc; border-radius: 18rpx 26rpx 26rpx 18rpx; transform: rotate(-7deg); }
.folder-back::before { position: absolute; top: -20rpx; left: 14rpx; width: 68rpx; height: 30rpx; content: ''; background: #8ad7bc; border-radius: 13rpx 13rpx 0 0; }
.folder-front { position: absolute; top: 61rpx; left: 34rpx; width: 158rpx; height: 108rpx; padding: 30rpx 24rpx; background: #e2fff5; border: 3rpx solid #53b997; border-radius: 18rpx 29rpx 29rpx 18rpx; box-shadow: 0 12rpx 26rpx rgba(54,145,114,.18); transform: rotate(4deg); }
.folder-line { width: 88rpx; height: 8rpx; margin-bottom: 13rpx; background: #6ac4a6; border-radius: 8rpx; }
.folder-line.short { width: 55rpx; }
.entry-badge { position: absolute; top: 17rpx; right: 0; padding: 9rpx 15rpx; color: #26795f; background: #fff; border-radius: 999rpx; box-shadow: 0 8rpx 18rpx rgba(36,55,86,.1); font-size: 18rpx; font-weight: 800; }
.logo-entry { background: linear-gradient(135deg, #fff9f0, #fff); }
.logo-art { margin-left: 18rpx; }
.logo-ring { position: absolute; border-radius: 50%; }
.ring-one { top: 18rpx; right: 14rpx; width: 165rpx; height: 165rpx; background: linear-gradient(145deg, #ffcc82, #ec8a78); box-shadow: 0 17rpx 33rpx rgba(215,123,91,.2); }
.ring-two { top: 45rpx; right: 42rpx; width: 108rpx; height: 108rpx; background: #fff8ed; }
.logo-letter { position: absolute; top: 53rpx; right: 65rpx; color: #a64c67; font-size: 70rpx; font-weight: 900; transform: rotate(-8deg); }
.logo-star { position: absolute; top: 7rpx; left: 21rpx; color: #704fce; font-size: 38rpx; }
.login-tip { display: flex; align-items: center; margin-top: 24rpx; padding: 23rpx 25rpx; background: #ece9ff; border: 2rpx solid #ddd7ff; border-radius: 24rpx; }
.tip-icon { display: flex; align-items: center; justify-content: center; width: 62rpx; height: 62rpx; color: #5e53c7; background: #fff; border-radius: 18rpx; font-weight: 850; }
.tip-main { flex: 1; margin-left: 18rpx; }
.tip-title { color: #423a93; font-size: 25rpx; font-weight: 780; }
.tip-desc { margin-top: 4rpx; color: #8580a6; font-size: 19rpx; }
.tip-arrow { color: #6257e8; font-size: 44rpx; }
</style>
