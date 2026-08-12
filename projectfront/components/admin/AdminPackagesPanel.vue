<template>
  <view class="packages-panel">
    <view class="filter-panel">
      <view
        v-for="item in typeOptions"
        :key="item.value"
        class="filter-item"
        :class="{ active: packageType === item.value }"
        @click="packageType = item.value"
      >
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
          <button v-if="!item.is_active" class="edit-btn" @click="$emit('edit', item)">编辑</button>
          <view v-else class="edit-locked">下架后编辑</view>
          <button
            class="status-btn"
            :class="item.is_active ? 'deactivate' : 'activate'"
            :loading="togglingId === item.id"
            :disabled="Boolean(togglingId)"
            @click="confirmToggle(item)"
          >
            {{ item.is_active ? '下架' : '上架' }}
          </button>
        </view>
      </view>
    </view>

    <view class="management-note">
      <view class="note-title">套餐管理规则</view>
      <view>新建：套餐保存后默认下架，复核无误后再手动上架。</view>
      <view>编辑：只有下架套餐可以修改名称、类型、价格和次数。</view>
      <view>上架：套餐会出现在用户购买列表中，并允许创建新订单。</view>
      <view>下架：立即从购买列表隐藏并拒绝新订单；历史订单保留原价格、次数和权益类型快照。</view>
    </view>
  </view>
</template>

<script>
import { api } from '../../api'
import { handleAdminAuthError, requireAdminSession } from '../../utils/auth'

export default {
  emits: ['total-change', 'edit'],
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
  mounted() {
    if (!requireAdminSession()) return
    this.loadPackages()
  },
  methods: {
    async loadPackages() {
      this.loading = true
      try {
        this.packages = await api.getAdminPackages()
        this.$emit('total-change', this.packages.length)
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 3000 })
        handleAdminAuthError(error)
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
        handleAdminAuthError(error)
      } finally {
        this.togglingId = null
      }
    }
  }
}
</script>

<style scoped>
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
.action-cell { display: grid; grid-template-columns: 1fr 1fr; gap: 12rpx; margin-top: 20rpx; }
.status-btn,.edit-btn,.edit-locked { height: 66rpx; margin: 0; border-radius: 16rpx; font-size: 22rpx; line-height: 66rpx; text-align: center; }
.edit-btn { color: #5147b5; background: #efedff; }
.edit-locked { color: #929aaa; background: #f0f2f5; }
.status-btn.activate { color: #18764c; background: #e6f7ef; }
.status-btn.deactivate { color: #9b651b; background: #fff3dc; }
.management-note { margin-top: 24rpx; padding: 24rpx; color: #7d8698; background: #e9ecf2; border-radius: 20rpx; font-size: 20rpx; line-height: 1.7; }
.note-title { margin-bottom: 7rpx; color: #3c4457; font-size: 23rpx; font-weight: 800; }

@media (min-width: 1000px) {
  .table-head, .package-row { display: grid; grid-template-columns: minmax(270px,2fr) minmax(110px,.8fr) minmax(100px,.7fr) minmax(100px,.7fr) minmax(100px,.7fr) minmax(220px,1.2fr); gap: 18px; align-items: center; }
  .table-head { margin-top: 22rpx; padding: 0 27rpx 10rpx; color: #8d96a7; font-size: 19rpx; font-weight: 750; }
  .head-action { text-align: right; }
  .package-row { min-height: 100px; margin-top: 10rpx; padding: 22rpx 27rpx; border-radius: 18rpx; }
  .data-cell { display: block; margin-top: 0; padding-top: 0; border-top: 0; }
  .data-cell::before { display: none; }
  .action-cell { margin-top: 0; }
  .status-btn,.edit-btn,.edit-locked { width: 105rpx; }
}
</style>
