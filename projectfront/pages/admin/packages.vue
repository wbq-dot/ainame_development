<template>
  <view class="admin-page">
    <view class="admin-hero">
      <view>
        <view class="hero-eyebrow">ADMIN CONSOLE</view>
        <view class="hero-title">套餐上下架管理</view>
        <view class="hero-desc">下架后禁止创建新订单，已经创建的订单仍按原套餐快照结算。</view>
      </view>
      <view class="total-badge"><text>{{ packages.length }}</text>个套餐</view>
    </view>

    <view class="admin-nav">
      <view class="nav-item" @click="goUsers">用户管理</view>
      <view class="nav-item active">套餐管理</view>
    </view>

    <view class="filter-panel">
      <view v-for="item in typeOptions" :key="item.value" class="filter-item" :class="{ active: packageType === item.value }" @click="packageType = item.value">
        {{ item.label }}
      </view>
    </view>

    <view v-if="loading" class="state-card">正在加载套餐…</view>
    <view v-else-if="!filteredPackages.length" class="state-card">暂无符合条件的套餐</view>

    <view v-else class="package-list">
      <view class="table-head">
        <view>套餐信息</view>
        <view>类型</view>
        <view>价格</view>
        <view>包含次数</view>
        <view>状态</view>
        <view class="head-action">操作</view>
      </view>

      <view v-for="item in filteredPackages" :key="item.id" class="package-row">
        <view class="package-identity">
          <view class="package-icon" :class="item.credit_type">{{ item.credit_type === 'logo' ? '标' : '名' }}</view>
          <view class="package-main">
            <view class="package-name">{{ item.name }}</view>
            <view class="package-meta">ID {{ item.id }} · 创建于 {{ formatDate(item.created_at) }}</view>
          </view>
        </view>
        <view class="data-cell" data-label="类型">{{ typeLabel(item.credit_type) }}</view>
        <view class="data-cell price-cell" data-label="价格">¥{{ formatPrice(item.price) }}</view>
        <view class="data-cell" data-label="包含次数">{{ item.credit_count }} 次</view>
        <view class="data-cell" data-label="状态">
          <text class="status-badge" :class="item.is_active ? 'active' : 'inactive'">{{ item.is_active ? '已上架' : '已下架' }}</text>
        </view>
        <view class="action-cell">
          <button class="status-btn" :class="item.is_active ? 'deactivate' : 'activate'" :loading="togglingId === item.id" :disabled="Boolean(togglingId)" @click="confirmToggle(item)">
            {{ item.is_active ? '下架' : '上架' }}
          </button>
        </view>
      </view>
    </view>

    <view class="management-note">
      <view class="note-title">状态规则</view>
      <view>上架：套餐会出现在用户购买列表中，并允许创建新订单。</view>
      <view>下架：立即从购买列表隐藏并拒绝新订单，已有订单不受影响。</view>
    </view>
  </view>
</template>

<script>
import { api } from '../../api'
import { getUser } from '../../utils/auth'

export default {
  data() {
    return {
      packages: [],
      loading: false,
      togglingId: null,
      packageType: '',
      typeOptions: [
        { label: '全部套餐', value: '' },
        { label: '起名套餐', value: 'name' },
        { label: 'Logo 套餐', value: 'logo' }
      ]
    }
  },
  computed: {
    filteredPackages() {
      if (!this.packageType) return this.packages
      return this.packages.filter((item) => item.credit_type === this.packageType)
    }
  },
  onLoad() {
    const currentUser = getUser()
    if (!currentUser || currentUser.role !== 'admin') {
      uni.showModal({
        title: '无权访问',
        content: '该页面仅限管理员使用。',
        showCancel: false,
        success: () => uni.navigateBack()
      })
      return
    }
    this.loadPackages()
  },
  methods: {
    goUsers() {
      uni.redirectTo({ url: '/pages/admin/users' })
    },
    async loadPackages() {
      this.loading = true
      try {
        this.packages = await api.getAdminPackages()
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 3000 })
        if (error.message.includes('管理员权限')) setTimeout(() => uni.navigateBack(), 800)
      } finally {
        this.loading = false
      }
    },
    typeLabel(type) {
      return type === 'logo' ? 'Logo 生成' : '智能起名'
    },
    formatPrice(value) {
      const price = Number(value)
      return Number.isFinite(price) ? price.toFixed(2) : value
    },
    formatDate(value) {
      if (!value) return '—'
      return String(value).replace('T', ' ').slice(0, 10)
    },
    confirmToggle(item) {
      const nextActive = !item.is_active
      const action = nextActive ? '上架' : '下架'
      const impact = nextActive
        ? '上架后，该套餐会重新出现在用户购买列表中，并允许创建新订单。'
        : '下架后，该套餐会立即从用户购买列表隐藏并拒绝新订单；已经创建的订单仍可继续支付。'
      uni.showModal({
        title: `确认${action}套餐`,
        content: `套餐：${item.name}\n类型：${this.typeLabel(item.credit_type)}\n价格：¥${this.formatPrice(item.price)}\n次数：${item.credit_count} 次\n\n${impact}`,
        confirmText: `确认${action}`,
        confirmColor: nextActive ? '#23815a' : '#c1782f',
        success: ({ confirm }) => {
          if (confirm) this.changeStatus(item, nextActive)
        }
      })
    },
    async changeStatus(item, isActive) {
      this.togglingId = item.id
      try {
        const result = await api.updateAdminPackageStatus(item.id, isActive)
        const index = this.packages.findIndex((current) => current.id === result.package.id)
        if (index >= 0) this.packages.splice(index, 1, result.package)
        uni.showToast({ title: result.message, icon: 'success' })
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 3000 })
      } finally {
        this.togglingId = null
      }
    }
  }
}
</script>

<style scoped>
.admin-page { min-height: 100vh; padding: 28rpx 28rpx 70rpx; background: #f3f5f9; }
.admin-hero { display: flex; align-items: center; justify-content: space-between; padding: 34rpx 32rpx; color: #fff; background: linear-gradient(135deg,#171d2d,#373c55); border-radius: 29rpx; box-shadow: 0 18rpx 40rpx rgba(23,29,45,.2); }
.hero-eyebrow { color: #f2d586; font-size: 17rpx; font-weight: 800; letter-spacing: 4rpx; }
.hero-title { margin-top: 12rpx; font-size: 39rpx; font-weight: 850; }
.hero-desc { max-width: 530rpx; margin-top: 10rpx; color: #c6cbd7; font-size: 21rpx; line-height: 1.5; }
.total-badge { display: flex; flex-direction: column; align-items: center; min-width: 105rpx; padding: 15rpx; color: #d7dbea; background: rgba(255,255,255,.1); border-radius: 20rpx; font-size: 18rpx; }
.total-badge text { color: #f2d586; font-size: 34rpx; font-weight: 850; }
.admin-nav { display: grid; grid-template-columns: 1fr 1fr; gap: 10rpx; margin-top: 20rpx; padding: 8rpx; background: #e4e7ed; border-radius: 20rpx; }
.nav-item { padding: 18rpx 0; color: #747e91; border-radius: 15rpx; font-size: 23rpx; font-weight: 750; text-align: center; }
.nav-item.active { color: #fff; background: #30364d; box-shadow: 0 8rpx 20rpx rgba(48,54,77,.18); }
.filter-panel { display: grid; grid-template-columns: repeat(3,1fr); gap: 10rpx; margin-top: 20rpx; padding: 9rpx; background: #fff; border-radius: 20rpx; box-shadow: 0 10rpx 30rpx rgba(36,55,86,.05); }
.filter-item { padding: 17rpx 5rpx; color: #7e8799; background: #f3f5f8; border-radius: 14rpx; font-size: 21rpx; text-align: center; }
.filter-item.active { color: #fff; background: #6257e8; }
.state-card { margin-top: 22rpx; padding: 55rpx 20rpx; color: #9099aa; background: #fff; border-radius: 24rpx; text-align: center; }
.table-head { display: none; }
.package-row { margin-top: 20rpx; padding: 27rpx; background: #fff; border-radius: 25rpx; box-shadow: 0 11rpx 32rpx rgba(36,55,86,.055); }
.package-identity { display: flex; align-items: center; }
.package-icon { display: flex; flex: 0 0 72rpx; align-items: center; justify-content: center; width: 72rpx; height: 72rpx; color: #fff; background: linear-gradient(135deg,#6257e8,#9574ef); border-radius: 20rpx; font-size: 25rpx; font-weight: 850; }
.package-icon.logo { background: linear-gradient(135deg,#287a69,#63b89f); }
.package-main { flex: 1; min-width: 0; margin-left: 17rpx; }
.package-name { overflow: hidden; font-size: 27rpx; font-weight: 820; text-overflow: ellipsis; white-space: nowrap; }
.package-meta { margin-top: 6rpx; color: #9aa2b1; font-size: 18rpx; }
.data-cell { display: flex; align-items: center; justify-content: space-between; margin-top: 14rpx; padding-top: 14rpx; color: #3c4457; border-top: 1rpx solid #edf0f4; font-size: 22rpx; }
.data-cell::before { color: #929aaa; font-size: 19rpx; content: attr(data-label); }
.price-cell { color: #4d43ae; font-size: 27rpx; font-weight: 800; }
.status-badge { padding: 7rpx 13rpx; border-radius: 999rpx; font-size: 18rpx; font-weight: 750; }
.status-badge.active { color: #18764c; background: #e6f7ef; }
.status-badge.inactive { color: #9b651b; background: #fff3dc; }
.action-cell { display: flex; justify-content: flex-end; margin-top: 20rpx; }
.status-btn { width: 100%; height: 66rpx; margin: 0; border-radius: 16rpx; font-size: 22rpx; line-height: 66rpx; }
.status-btn.activate { color: #18764c; background: #e6f7ef; }
.status-btn.deactivate { color: #9b651b; background: #fff3dc; }
.management-note { margin-top: 24rpx; padding: 24rpx; color: #7d8698; background: #e9ecf2; border-radius: 20rpx; font-size: 20rpx; line-height: 1.7; }
.note-title { margin-bottom: 7rpx; color: #3c4457; font-size: 23rpx; font-weight: 800; }

@media (min-width: 1000px) {
  .admin-page { max-width: 1400px; margin: 0 auto; padding-left: 34px; padding-right: 34px; }
  .table-head, .package-row { display: grid; grid-template-columns: minmax(270px,2fr) minmax(110px,.8fr) minmax(100px,.7fr) minmax(100px,.7fr) minmax(100px,.7fr) minmax(110px,.7fr); gap: 18px; align-items: center; }
  .table-head { margin-top: 22rpx; padding: 0 27rpx 10rpx; color: #8d96a7; font-size: 19rpx; font-weight: 750; }
  .head-action { text-align: right; }
  .package-row { min-height: 100px; margin-top: 10rpx; padding: 22rpx 27rpx; border-radius: 18rpx; }
  .data-cell { display: block; margin-top: 0; padding-top: 0; border-top: 0; }
  .data-cell::before { display: none; }
  .action-cell { margin-top: 0; }
  .status-btn { width: 105rpx; }
}
</style>
