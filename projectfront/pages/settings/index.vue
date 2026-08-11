<template>
  <view class="page-shell settings-page">
    <view class="settings-hero">
      <view class="hero-copy">
        <view class="hero-tag">GENERAL SETTINGS</view>
        <view class="hero-title">通用设置</view>
        <view class="hero-desc">调整当前设备上的界面显示与交互体验。</view>
      </view>
      <view class="display-art">
        <view class="display-card">Aa</view>
        <view class="display-slider"><text></text></view>
        <view class="display-dot"></view>
      </view>
    </view>

    <view class="setting-section">
      <view class="section-title">界面显示</view>
      <view class="section-note">以下偏好仅保存在当前设备，可随时调整。</view>
      <view class="settings-card">
        <view class="setting-row">
          <view class="setting-icon purple">字</view>
          <view class="setting-copy"><view class="row-title">大号文字</view><view class="row-desc">放大页面中的整体文字和间距</view></view>
          <switch color="#6257e8" :checked="preferences.fontSize === 'large'" @change="setLargeText" />
        </view>
        <view class="setting-row">
          <view class="setting-icon green">明</view>
          <view class="setting-copy"><view class="row-title">高对比度</view><view class="row-desc">增强导航、正文与背景的颜色区分</view></view>
          <switch color="#6257e8" :checked="preferences.highContrast" @change="setHighContrast" />
        </view>
        <view class="setting-row">
          <view class="setting-icon amber">缓</view>
          <view class="setting-copy"><view class="row-title">减少动画</view><view class="row-desc">降低不必要的过渡与动态效果</view></view>
          <switch color="#6257e8" :checked="preferences.reduceMotion" @change="setReduceMotion" />
        </view>
      </view>
    </view>

    <view class="device-note">
      <view class="note-mark">i</view>
      <view><view class="note-title">设备偏好</view><view class="note-desc">退出登录或切换账号不会清除这些显示设置。</view></view>
    </view>
  </view>
</template>

<script>
import { getDisplayPreferences, saveDisplayPreferences } from '../../utils/preferences'

export default {
  data() { return { preferences: getDisplayPreferences() } },
  onShow() { this.preferences = getDisplayPreferences() },
  methods: {
    update(key, value) {
      this.preferences = { ...this.preferences, [key]: value }
      saveDisplayPreferences(this.preferences)
      uni.showToast({ title: '设置已保存', icon: 'success' })
    },
    setLargeText(event) { this.update('fontSize', event.detail.value ? 'large' : 'standard') },
    setHighContrast(event) { this.update('highContrast', event.detail.value) },
    setReduceMotion(event) { this.update('reduceMotion', event.detail.value) }
  }
}
</script>

<style scoped>
.settings-page { background: radial-gradient(circle at 95% 3%,#e9e5ff 0,transparent 26%),#f5f7fb; }
.settings-hero { position: relative; min-height: 245rpx; padding: 36rpx; overflow: hidden; color: #fff; background: linear-gradient(140deg,#2d315e,#6257c9 68%,#7c68dc); border-radius: 34rpx; box-shadow: 0 20rpx 46rpx rgba(66,57,155,.18); }
.hero-copy { position: relative; z-index: 2; width: 66%; }
.hero-tag { color: #d6d2ff; font-size: 17rpx; font-weight: 850; letter-spacing: 3rpx; }
.hero-title { margin-top: 16rpx; font-size: 42rpx; font-weight: 900; }
.hero-desc { margin-top: 13rpx; color: #e4e1ff; font-size: 21rpx; line-height: 1.55; }
.display-art { position: absolute; top: 0; right: 0; width: 245rpx; height: 100%; }
.display-card { position: absolute; top: 42rpx; right: 28rpx; display: flex; align-items: center; justify-content: center; width: 112rpx; height: 112rpx; color: #5a50bf; background: #fff; border-radius: 30rpx; box-shadow: 0 17rpx 35rpx rgba(30,25,91,.24); font-size: 42rpx; font-weight: 900; transform: rotate(7deg); }
.display-slider { position: absolute; right: 64rpx; bottom: 35rpx; width: 132rpx; height: 13rpx; background: rgba(255,255,255,.3); border-radius: 999rpx; }
.display-slider text { display: block; width: 76rpx; height: 100%; background: #f2cf79; border-radius: 999rpx; }
.display-dot { position: absolute; top: 33rpx; right: 166rpx; width: 24rpx; height: 24rpx; background: #82dfc5; border-radius: 50%; }
.setting-section { margin-top: 34rpx; }
.section-title { font-size: 31rpx; font-weight: 850; }
.section-note { margin-top: 7rpx; color: #929aaa; font-size: 21rpx; }
.settings-card { margin-top: 18rpx; padding: 0 27rpx; background: #fff; border: 1rpx solid rgba(31,55,90,.055); border-radius: 27rpx; box-shadow: 0 12rpx 35rpx rgba(36,55,86,.06); }
.setting-row { display: flex; align-items: center; min-height: 124rpx; border-top: 1rpx solid #eceef3; }
.setting-row:first-child { border-top: 0; }
.setting-icon { display: flex; flex: 0 0 58rpx; align-items: center; justify-content: center; width: 58rpx; height: 58rpx; border-radius: 17rpx; font-size: 21rpx; font-weight: 850; }
.setting-icon.purple { color: #5b51c2; background: #ebe9ff; }
.setting-icon.green { color: #327c67; background: #e5f7f0; }
.setting-icon.amber { color: #9b642d; background: #fff1df; }
.setting-copy { flex: 1; min-width: 0; margin: 0 18rpx; }
.row-title { font-size: 25rpx; font-weight: 760; }
.row-desc { margin-top: 6rpx; color: #929aaa; font-size: 19rpx; line-height: 1.45; }
.device-note { display: flex; align-items: center; margin-top: 22rpx; padding: 23rpx 25rpx; background: #eeecff; border: 2rpx solid #dfdbff; border-radius: 24rpx; }
.note-mark { display: flex; flex: 0 0 55rpx; align-items: center; justify-content: center; width: 55rpx; height: 55rpx; margin-right: 17rpx; color: #5d52c7; background: #fff; border-radius: 17rpx; font-size: 25rpx; font-weight: 900; }
.note-title { color: #423a93; font-size: 23rpx; font-weight: 780; }
.note-desc { margin-top: 4rpx; color: #8580a6; font-size: 19rpx; line-height: 1.5; }
</style>
