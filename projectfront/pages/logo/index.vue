<template>
  <view class="page-shell logo-page">
    <view class="logo-hero">
      <view class="hero-copy"><view class="hero-tag">LOGO STUDIO</view><view class="hero-title">让品牌拥有<br />自己的视觉符号</view><view class="hero-desc">名称与风格交给你，构图与灵感交给 AI。</view></view>
      <view class="mark-art"><view class="mark-circle"></view><view class="mark-square">Z</view><view class="mark-star">✦</view><view class="mark-line"></view></view>
    </view>

    <view v-if="!loggedIn" class="card login-callout"><view class="login-icon">钥</view><view class="card-title">登录后进入 Logo 工作室</view><view class="card-note">生成作品和剩余次数都与你的账号绑定。</view><button class="primary-btn btn-gap" @click="goLogin">登录 / 注册</button></view>

    <template v-else>
      <view class="credit-bar"><view><view class="credit-caption">可用 Logo 次数</view><view class="credit-value">{{ logoBalance }}</view></view><view class="credit-cost">每次消耗 1 次</view></view>
      <view class="card form-card">
        <view class="form-heading"><view><view class="section-number">01</view><view class="card-title">描述你的品牌</view></view><view class="palette"><text></text><text></text><text></text></view></view>
        <view class="field"><text class="field-label">企业名称</text><input v-model.trim="logoForm.company_name" class="field-input" maxlength="50" placeholder="例如：青衍科技" /></view>
        <view class="field"><text class="field-label">风格要求（选填）</text><textarea v-model.trim="logoForm.style_feedback" class="field-textarea" maxlength="300" placeholder="例如：蓝紫渐变、科技感、图形简洁，不要文字" /><view class="counter">{{ logoForm.style_feedback.length }}/300</view></view>
        <view class="style-suggestions"><text v-for="item in styles" :key="item" @click="appendStyle(item)">{{ item }}</text></view>
        <view class="notice"><text>!</text><view>确认后先扣除 1 次；如果生成失败，后端会自动退回。</view></view>
        <button class="primary-btn btn-gap" :loading="logoLoading" :disabled="logoLoading || !logoForm.company_name || logoBalance <= 0" @click="confirmGenerateLogo">{{ logoBalance > 0 ? '生成 Logo（消耗 1 次）' : 'Logo 次数不足' }}</button>
        <button v-if="logoBalance <= 0" class="secondary-btn btn-gap" @click="goBuyLogo">购买 Logo 套餐</button>
      </view>

      <view v-if="logoResult" class="result-wrap"><view class="result-title">本次作品</view><view class="logo-frame"><image v-if="logoResult.logo_url" class="logo-image" :src="logoResult.logo_url" mode="aspectFit" @click="previewLogo" /><view v-else class="logo-empty">没有返回图片</view><view class="corner corner-a"></view><view class="corner corner-b"></view></view><view class="logo-status">{{ logoResult.logo_status }}</view><view class="prompt-box"><view class="prompt-title">实际生成提示词</view><view class="prompt-content">{{ logoResult.logo_prompt }}</view></view></view>
    </template>
  </view>
</template>

<script>
import { api } from '../../api'
import { getAccessToken, requireLogin } from '../../utils/auth'

export default {
  data() { return { loggedIn: false, logoBalance: 0, logoLoading: false, logoForm: { company_name: '', style_feedback: '' }, logoResult: null, styles: ['极简', '科技感', '自然', '高级感'] } },
  onShow() { this.loggedIn = Boolean(getAccessToken()); if (this.loggedIn) this.loadBalance() },
  methods: {
    goLogin() { uni.navigateTo({ url: '/pages/auth/login' }) },
    async loadBalance() { try { const data = await api.getBalance(); this.logoBalance = data.logo_balance ?? 0 } catch (error) { uni.showToast({ title: error.message, icon: 'none' }) } },
    goBuyLogo() { uni.setStorageSync('account_package_type', 'logo'); uni.switchTab({ url: '/pages/account/index' }) },
    appendStyle(style) { const current = this.logoForm.style_feedback.trim(); if (!current.includes(style)) this.logoForm.style_feedback = current ? `${current}、${style}` : style },
    confirmGenerateLogo() {
      if (!requireLogin()) return
      if (this.logoBalance <= 0) { this.goBuyLogo(); return }
      uni.showModal({ title: '确认生成 Logo', content: `准确动作：\n1. 为“${this.logoForm.company_name}”调用图片模型；\n2. 先扣除 1 次 Logo 次数；\n3. 失败时自动退回。\n\n生成后预计剩余 ${Math.max(0, this.logoBalance - 1)} 次，是否继续？`, confirmText: '确认生成', success: ({ confirm }) => { if (confirm) this.generateLogo() } })
    },
    async generateLogo() {
      this.logoLoading = true; this.logoResult = null
      try { this.logoResult = await api.generateLogo(this.logoForm); this.logoBalance = this.logoResult.remaining_logo_balance; uni.showToast({ title: this.logoResult.logo_status, icon: this.logoResult.logo_url ? 'success' : 'none' }) }
      catch (error) { uni.showToast({ title: error.message, icon: 'none', duration: 3200 }) }
      finally { await this.loadBalance(); this.logoLoading = false }
    },
    previewLogo() { uni.previewImage({ urls: [this.logoResult.logo_url], current: this.logoResult.logo_url }) }
  }
}
</script>

<style scoped>
.logo-page { background: radial-gradient(circle at 96% 2%, #ffead9 0, transparent 27%), #f5f7fb; }
.logo-hero { position: relative; min-height: 280rpx; padding: 36rpx; overflow: hidden; color: #fff; background: linear-gradient(140deg, #3f285c, #7b487b 55%, #dd7b72); border-radius: 35rpx; box-shadow: 0 21rpx 48rpx rgba(100,55,100,.2); }
.hero-copy { position: relative; z-index: 2; width: 65%; }
.hero-tag { color: #f5c8dd; font-size: 18rpx; font-weight: 850; letter-spacing: 3rpx; }
.hero-title { margin-top: 18rpx; font-size: 39rpx; font-weight: 900; line-height: 1.45; }
.hero-desc { margin-top: 14rpx; color: #f7dce8; font-size: 21rpx; line-height: 1.55; }
.mark-art { position: absolute; top: 0; right: 0; width: 270rpx; height: 100%; }
.mark-circle { position: absolute; top: 48rpx; right: -35rpx; width: 210rpx; height: 210rpx; background: rgba(255,204,142,.26); border: 3rpx solid rgba(255,255,255,.24); border-radius: 50%; }
.mark-square { position: absolute; top: 82rpx; right: 38rpx; display: flex; align-items: center; justify-content: center; width: 108rpx; height: 108rpx; color: #704064; background: #ffcf8c; border-radius: 32rpx; box-shadow: 0 15rpx 28rpx rgba(44,22,63,.25); font-size: 61rpx; font-weight: 900; transform: rotate(12deg); }
.mark-star { position: absolute; top: 29rpx; right: 154rpx; font-size: 38rpx; }
.mark-line { position: absolute; right: 153rpx; bottom: 41rpx; width: 62rpx; height: 13rpx; background: #8ee0cb; border-radius: 20rpx; transform: rotate(-25deg); }
.login-callout { padding: 50rpx 34rpx; text-align: center; }
.login-icon { display: flex; align-items: center; justify-content: center; width: 86rpx; height: 86rpx; margin: 0 auto 22rpx; color: #8d4c72; background: #ffe8ef; border-radius: 25rpx; font-weight: 850; }
.credit-bar { display: flex; align-items: center; justify-content: space-between; margin-top: 23rpx; padding: 25rpx 28rpx; color: #fff; background: linear-gradient(135deg, #392855, #70476f); border-radius: 26rpx; }
.credit-caption { color: #e7d6e4; font-size: 20rpx; }
.credit-value { margin-top: 3rpx; font-size: 42rpx; font-weight: 900; }
.credit-cost { padding: 11rpx 17rpx; color: #70476f; background: #fff; border-radius: 999rpx; font-size: 20rpx; font-weight: 750; }
.form-card { padding: 31rpx; }
.form-heading { display: flex; align-items: center; justify-content: space-between; }
.section-number { color: #bd7696; font-size: 18rpx; font-weight: 900; letter-spacing: 2rpx; }
.palette { display: flex; gap: 8rpx; }
.palette text { width: 25rpx; height: 25rpx; background: #70476f; border-radius: 50%; }
.palette text:nth-child(2) { background: #ee9f83; }
.palette text:nth-child(3) { background: #f2c879; }
.counter { margin-top: 7rpx; color: #a09aaa; font-size: 19rpx; text-align: right; }
.style-suggestions { display: flex; flex-wrap: wrap; gap: 11rpx; margin-top: 16rpx; }
.style-suggestions text { padding: 11rpx 18rpx; color: #85506e; background: #fff0f4; border-radius: 999rpx; font-size: 20rpx; }
.notice { display: flex; gap: 13rpx; margin-top: 23rpx; padding: 18rpx; color: #795c2f; background: #fff7e9; border-radius: 17rpx; font-size: 21rpx; line-height: 1.55; }
.notice > text { font-weight: 900; }
.result-wrap { margin-top: 32rpx; }
.result-title { font-size: 32rpx; font-weight: 850; }
.logo-frame { position: relative; margin-top: 18rpx; padding: 15rpx; background: #fff; border-radius: 29rpx; box-shadow: 0 14rpx 40rpx rgba(75,43,74,.1); }
.logo-image,.logo-empty { width: 100%; height: 560rpx; background: linear-gradient(135deg,#faf7f4,#f5eef4); border-radius: 22rpx; }
.logo-empty { display: flex; align-items: center; justify-content: center; color: #a49aa3; }
.corner { position: absolute; width: 42rpx; height: 42rpx; border-color: #d88799; }
.corner-a { top: 28rpx; left: 28rpx; border-top: 5rpx solid; border-left: 5rpx solid; }
.corner-b { right: 28rpx; bottom: 28rpx; border-right: 5rpx solid; border-bottom: 5rpx solid; }
.logo-status { margin-top: 16rpx; color: #84506f; font-size: 24rpx; font-weight: 750; text-align: center; }
.prompt-box { margin-top: 20rpx; padding: 22rpx; background: #f5f0f4; border-radius: 19rpx; }
.prompt-title { font-size: 23rpx; font-weight: 780; }
.prompt-content { margin-top: 10rpx; color: #756b76; font-size: 21rpx; line-height: 1.65; white-space: pre-wrap; }
</style>
