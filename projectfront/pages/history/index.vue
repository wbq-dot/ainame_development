<template>
  <view class="page-shell history-page">
    <view class="history-hero"><view><view class="hero-tag">LOCAL HISTORY</view><view class="hero-title">创作记录</view><view class="hero-desc">最近生成的名字保存在当前设备，最多 30 组。</view></view><view class="history-art"><view class="sheet sheet-a"></view><view class="sheet sheet-b"></view><view class="clock">↺</view></view></view>

    <view v-if="!history.length" class="empty-card"><view class="empty-icon">记</view><view class="empty-title">还没有创作记录</view><view class="empty-desc">完成一次 AI 起名后，候选名字会自动出现在这里。</view><button class="primary-btn btn-gap" @click="goNaming">去起名</button></view>

    <template v-else>
      <view class="history-summary"><text>共 {{ history.length }} 组记录</text><view @click="confirmClear">清空全部</view></view>
      <view v-for="item in history" :key="item.threadId" class="history-card">
        <view class="card-head"><view><view class="category-badge">{{ item.category }}</view><view class="history-time">{{ formatTime(item.updatedAt) }}</view></view><view class="delete-btn" @click="confirmRemove(item)">删除</view></view>
        <view v-if="item.requirement" class="requirement">“{{ item.requirement }}”</view>
        <view class="names"><view v-for="(name, index) in item.names" :key="`${item.threadId}-${index}`"><text class="name-index">{{ String(index + 1).padStart(2, '0') }}</text><text class="name-text">{{ name.name }}</text><text class="copy" @click="copyName(name.name)">复制</text></view></view>
      </view>
    </template>
  </view>
</template>

<script>
import { clearNamingHistory, getNamingHistory, removeNamingHistory } from '../../utils/history'

export default {
  data() { return { history: [] } },
  onShow() { this.history = getNamingHistory() },
  methods: {
    goNaming() { uni.switchTab({ url: '/pages/naming/index' }) },
    formatTime(value) { if (!value) return ''; const date = new Date(value); return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}` },
    copyName(name) { uni.setClipboardData({ data: name, success: () => uni.showToast({ title: '名字已复制', icon: 'success' }) }) },
    confirmRemove(item) { uni.showModal({ title: '删除这组记录', content: `将从当前设备删除“${item.names.map((name) => name.name).join('、')}”，无法恢复。是否继续？`, confirmColor: '#d94a64', success: ({ confirm }) => { if (confirm) this.history = removeNamingHistory(item.threadId) } }) },
    confirmClear() { uni.showModal({ title: '清空全部记录', content: `将删除当前设备保存的 ${this.history.length} 组创作记录，无法恢复。是否继续？`, confirmColor: '#d94a64', success: ({ confirm }) => { if (confirm) { clearNamingHistory(); this.history = [] } } }) }
  }
}
</script>

<style scoped>
.history-page { background: radial-gradient(circle at 96% 2%, #e9e5ff 0, transparent 25%), #f5f7fb; }
.history-hero { position: relative; min-height: 230rpx; padding: 34rpx; overflow: hidden; color: #fff; background: linear-gradient(140deg,#2f315e,#6659d2); border-radius: 33rpx; }
.hero-tag { color: #ccc8ff; font-size: 17rpx; font-weight: 850; letter-spacing: 3rpx; }
.hero-title { margin-top: 15rpx; font-size: 43rpx; font-weight: 900; }
.hero-desc { width: 65%; margin-top: 13rpx; color: #dddafe; font-size: 21rpx; line-height: 1.55; }
.history-art { position: absolute; top: 0; right: 10rpx; width: 230rpx; height: 100%; }
.sheet { position: absolute; width: 110rpx; height: 140rpx; background: #fff; border-radius: 15rpx; box-shadow: 0 13rpx 25rpx rgba(28,28,74,.24); }
.sheet::after { position: absolute; top: 30rpx; right: 18rpx; left: 18rpx; height: 7rpx; content: ''; background: #c7c3ec; border-radius: 8rpx; box-shadow: 0 22rpx 0 #c7c3ec, 0 44rpx 0 #c7c3ec; }
.sheet-a { top: 43rpx; right: 38rpx; transform: rotate(10deg); }
.sheet-b { top: 59rpx; right: 83rpx; background: #f0edff; transform: rotate(-9deg); }
.clock { position: absolute; right: 14rpx; bottom: 25rpx; display: flex; align-items: center; justify-content: center; width: 65rpx; height: 65rpx; color: #5148b2; background: #f6c86f; border-radius: 50%; font-size: 36rpx; font-weight: 900; }
.empty-card { margin-top: 26rpx; padding: 60rpx 34rpx; background: #fff; border-radius: 29rpx; text-align: center; }
.empty-icon { display: flex; align-items: center; justify-content: center; width: 85rpx; height: 85rpx; margin: 0 auto 22rpx; color: #6257e8; background: #ebe9ff; border-radius: 25rpx; font-size: 30rpx; font-weight: 900; }
.empty-title { font-size: 29rpx; font-weight: 850; }
.empty-desc { margin-top: 10rpx; color: #8b94a6; font-size: 22rpx; line-height: 1.6; }
.history-summary { display: flex; align-items: center; justify-content: space-between; margin: 27rpx 5rpx 0; color: #7f899b; font-size: 22rpx; }
.history-summary view { color: #cb4963; }
.history-card { margin-top: 19rpx; padding: 27rpx; background: #fff; border-radius: 27rpx; box-shadow: 0 12rpx 35rpx rgba(36,55,86,.06); }
.card-head { display: flex; align-items: flex-start; justify-content: space-between; }
.category-badge { display: inline-block; padding: 9rpx 16rpx; color: #5147b9; background: #ebe9ff; border-radius: 999rpx; font-size: 20rpx; font-weight: 750; }
.history-time { margin-top: 8rpx; color: #a0a7b5; font-size: 19rpx; }
.delete-btn { padding: 8rpx 13rpx; color: #c84c64; background: #fff0f3; border-radius: 999rpx; font-size: 19rpx; }
.requirement { margin-top: 18rpx; padding: 15rpx 18rpx; color: #727b8c; background: #f6f7f9; border-radius: 15rpx; font-size: 21rpx; line-height: 1.55; }
.names { margin-top: 17rpx; }
.names > view { display: flex; align-items: center; padding: 17rpx 0; border-top: 1rpx solid #eef0f4; }
.name-index { width: 58rpx; color: #aaa5d4; font-size: 19rpx; font-weight: 850; }
.name-text { flex: 1; color: #292452; font-size: 28rpx; font-weight: 800; letter-spacing: 2rpx; }
.copy { color: #6257e8; font-size: 20rpx; }
</style>
