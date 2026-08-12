<template>
  <view class="admin-page">
    <view class="admin-hero">
      <view>
        <view class="hero-eyebrow">ADMIN CONSOLE</view>
        <view class="hero-title">平台套餐管理</view>
        <view class="hero-desc">新建、编辑并管理起名与 Logo 套餐；修改后的内容只用于之后创建的新订单。</view>
      </view>
      <view class="hero-actions">
        <view class="total-badge"><text>{{ total }}</text>个套餐</view>
        <button class="create-package-btn" @click="createPackage">＋ 新建套餐</button>
        <button class="admin-home-btn" @click="backToConsole">操作列表</button>
      </view>
    </view>

    <AdminPackagesPanel ref="packagesPanel" @total-change="total = $event" @edit="editPackage" />
  </view>
</template>

<script>
import AdminPackagesPanel from '../../components/admin/AdminPackagesPanel.vue'
import { requireAdminSession } from '../../utils/auth'

export default {
  components: { AdminPackagesPanel },
  data() {
    return { total: 0, hasShown: false }
  },
  onShow() {
    if (!requireAdminSession()) return
    if (!this.hasShown) {
      this.hasShown = true
      return
    }
    this.$nextTick(() => {
      if (this.$refs.packagesPanel) this.$refs.packagesPanel.loadPackages()
    })
  },
  methods: {
    backToConsole() { uni.redirectTo({ url: '/pages/admin/index' }) },
    createPackage() { uni.navigateTo({ url: '/pages/admin/package-form' }) },
    editPackage(item) { uni.navigateTo({ url: `/pages/admin/package-form?id=${item.id}` }) }
  }
}
</script>

<style scoped>
.admin-page { min-height: 100vh; padding: 28rpx 28rpx 70rpx; background: #f3f5f9; }
.admin-hero { display: flex; align-items: center; justify-content: space-between; gap: 22rpx; padding: 34rpx 32rpx; color: #fff; background: linear-gradient(135deg,#171d2d,#373c55); border-radius: 29rpx; box-shadow: 0 18rpx 40rpx rgba(23,29,45,.2); }
.hero-eyebrow { color: #f2d586; font-size: 17rpx; font-weight: 800; letter-spacing: 4rpx; }
.hero-title { margin-top: 12rpx; font-size: 39rpx; font-weight: 850; }
.hero-desc { max-width: 530rpx; margin-top: 10rpx; color: #c6cbd7; font-size: 21rpx; line-height: 1.5; }
.hero-actions { display: flex; flex-direction: column; align-items: stretch; gap: 10rpx; }
.total-badge { display: flex; flex-direction: column; align-items: center; min-width: 105rpx; padding: 15rpx; color: #d7dbea; background: rgba(255,255,255,.1); border-radius: 20rpx; font-size: 18rpx; }
.total-badge text { color: #f2d586; font-size: 34rpx; font-weight: 850; }
.create-package-btn { height: 58rpx; margin: 0; padding: 0 18rpx; color: #292d42; background: linear-gradient(135deg,#f2d586,#dfbd62); border-radius: 15rpx; font-size: 19rpx; font-weight: 800; line-height: 58rpx; }
.admin-home-btn { height: 54rpx; margin: 0; padding: 0 18rpx; color: #f5df9e; background: rgba(255,255,255,.08); border: 1rpx solid rgba(245,223,158,.35); border-radius: 15rpx; font-size: 18rpx; line-height: 52rpx; }

@media (min-width: 1000px) {
  .admin-page { max-width: 1400px; margin: 0 auto; padding: 34px; }
}
</style>
