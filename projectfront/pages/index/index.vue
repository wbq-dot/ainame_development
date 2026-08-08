<template>
  <view class="home-page">
    <view class="topbar">
      <view>
        <view class="eyebrow">AI NAMING STUDIO</view>
        <view class="brand">知名台</view>
      </view>
      <view class="health" @click="checkHealth">
        <view class="status-dot" :class="healthClass"></view>
        <text>{{ healthText }}</text>
      </view>
    </view>

    <view class="hero">
      <view class="hero-tag">灵感，从一个好名字开始</view>
      <view class="hero-title">让名字拥有<br />被记住的力量</view>
      <view class="hero-desc">人名、企业名与宠物名，一次获得5个有出处、有寓意的候选方案。</view>
      <button class="hero-btn" @click="startNaming">开始创作</button>
      <view class="orb orb-one"></view>
      <view class="orb orb-two"></view>
    </view>

    <view class="stats-card" @click="openAccount">
      <view>
        <view class="stats-label">{{ loggedIn ? '剩余起名次数' : '登录后查看次数' }}</view>
        <view class="stats-value">{{ loggedIn ? balance : '—' }}</view>
      </view>
      <view class="stats-action">{{ loggedIn ? '查看账户 →' : '登录 / 注册 →' }}</view>
    </view>

    <view class="section-head">
      <text class="section-title">快捷功能</text>
      <text class="muted small">只连接现有后端</text>
    </view>
    <view class="quick-grid">
      <view v-for="item in quickActions" :key="item.title" class="quick-card" @click="go(item)">
        <view class="quick-icon" :style="{ background: item.background }">{{ item.icon }}</view>
        <view class="quick-title">{{ item.title }}</view>
        <view class="quick-desc">{{ item.desc }}</view>
      </view>
    </view>

    <view class="safe-bottom"></view>
  </view>
</template>

<script>
import { api } from '../../api'
import { getAccessToken } from '../../utils/auth'

export default {
  data() {
    return {
      healthState: 'checking',
      balance: 0,
      loggedIn: false,
      quickActions: [
        { title: 'AI 起名', desc: '人名 · 企业 · 宠物', icon: '名', page: '/pages/naming/index', tab: true, background: '#ebe9ff' },
        { title: '专属知识库', desc: '登录后上传 PDF 或 TXT', icon: '库', page: '/pages/knowledge/index', auth: true, background: '#e2f5ee' },
        { title: 'Logo 生成', desc: '登录后进行视觉创作', icon: '图', page: '/pages/logo/index', auth: true, background: '#fff0df' },
        { title: '套餐购买', desc: '无需登录即可查看', icon: '充', page: '/pages/account/index', tab: true, background: '#fff5c9' }
      ]
    }
  },
  computed: {
    healthText() {
      return { checking: '检查中', online: '服务正常', offline: '服务未连接' }[this.healthState]
    },
    healthClass() {
      return `dot-${this.healthState}`
    }
  },
  onShow() {
    this.loggedIn = Boolean(getAccessToken())
    this.loadData()
  },
  methods: {
    async loadData() {
      await Promise.allSettled([this.checkHealth(), this.loadBalance()])
    },
    async checkHealth() {
      this.healthState = 'checking'
      try {
        await api.health()
        this.healthState = 'online'
      } catch (error) {
        this.healthState = 'offline'
        uni.showToast({ title: error.message, icon: 'none' })
      }
    },
    async loadBalance() {
      if (!this.loggedIn) return
      try {
        const data = await api.getBalance()
        this.balance = data.balance
      } catch (error) {
        this.loggedIn = false
      }
    },
    startNaming() { uni.switchTab({ url: '/pages/naming/index' }) },
    openAccount() {
      if (this.loggedIn) uni.switchTab({ url: '/pages/account/index' })
      else uni.navigateTo({ url: '/pages/auth/login' })
    },
    go(item) {
      if (item.auth && !getAccessToken()) {
        uni.navigateTo({ url: '/pages/auth/login' })
        return
      }
      if (item.tab) uni.switchTab({ url: item.page })
      else uni.navigateTo({ url: item.page })
    }
  }
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  padding: calc(var(--status-bar-height) + 28rpx) 28rpx 46rpx;
  background: radial-gradient(circle at 90% 4%, #ebe6ff 0, transparent 28%), #f5f7fb;
}
.topbar { display: flex; align-items: center; justify-content: space-between; }
.eyebrow { color: #887cf1; font-size: 18rpx; font-weight: 800; letter-spacing: 4rpx; }
.brand { margin-top: 3rpx; font-size: 42rpx; font-weight: 850; }
.health {
  display: flex;
  align-items: center;
  gap: 10rpx;
  padding: 14rpx 18rpx;
  color: #667085;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 999rpx;
  font-size: 22rpx;
}
.dot-checking { background: #f2a33a; }
.dot-online { background: #22a06b; box-shadow: 0 0 0 7rpx rgba(34, 160, 107, 0.12); }
.dot-offline { background: #d94a64; }
.hero {
  position: relative;
  overflow: hidden;
  margin-top: 34rpx;
  padding: 46rpx 38rpx 42rpx;
  color: #fff;
  background: linear-gradient(145deg, #2c285e, #5c4bd8 58%, #7b63eb);
  border-radius: 38rpx;
  box-shadow: 0 25rpx 60rpx rgba(72, 57, 174, 0.25);
}
.hero-tag { position: relative; z-index: 2; color: #d8d3ff; font-size: 22rpx; }
.hero-title { position: relative; z-index: 2; margin-top: 20rpx; font-size: 54rpx; font-weight: 850; line-height: 1.25; }
.hero-desc { position: relative; z-index: 2; width: 82%; margin-top: 18rpx; color: #dedbfa; font-size: 24rpx; line-height: 1.7; }
.hero-btn {
  position: relative;
  z-index: 2;
  width: 220rpx;
  height: 76rpx;
  margin: 32rpx 0 0;
  color: #3b327d;
  background: #fff;
  border-radius: 20rpx;
  font-size: 26rpx;
  font-weight: 750;
  line-height: 76rpx;
}
.orb { position: absolute; border-radius: 50%; filter: blur(2rpx); }
.orb-one { top: -80rpx; right: -70rpx; width: 260rpx; height: 260rpx; background: rgba(196, 181, 253, 0.26); }
.orb-two { right: 70rpx; bottom: -130rpx; width: 220rpx; height: 220rpx; background: rgba(99, 215, 199, 0.16); }
.stats-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 24rpx;
  padding: 24rpx 28rpx;
  background: #fff;
  border-radius: 25rpx;
  box-shadow: 0 12rpx 35rpx rgba(36, 55, 86, 0.06);
}
.stats-label { color: #7f899d; font-size: 22rpx; }
.stats-value { margin-top: 4rpx; font-size: 42rpx; font-weight: 800; }
.stats-action { color: #6257e8; font-size: 24rpx; font-weight: 650; }
.small { font-size: 21rpx; }
.quick-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18rpx; margin-top: 20rpx; }
.quick-card { padding: 25rpx; background: #fff; border-radius: 25rpx; box-shadow: 0 12rpx 35rpx rgba(36, 55, 86, 0.05); }
.quick-icon { display: flex; align-items: center; justify-content: center; width: 68rpx; height: 68rpx; color: #443a9f; border-radius: 19rpx; font-size: 28rpx; font-weight: 800; }
.quick-title { margin-top: 20rpx; font-size: 28rpx; font-weight: 750; }
.quick-desc { margin-top: 7rpx; color: #9098a9; font-size: 21rpx; }
</style>
