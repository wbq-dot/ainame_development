<template>
  <view class="page-shell account-page">
    <view class="page-title">我的</view>
    <view class="page-subtitle">账户次数、套餐购买和本地联调设置。</view>

    <view class="profile-card">
      <view class="avatar">{{ avatarText }}</view>
      <view class="profile-main">
        <view class="profile-name">{{ user ? user.username : '尚未登录' }}</view>
        <view class="profile-email">{{ user ? user.email : '登录后查看次数并购买套餐' }}</view>
      </view>
      <button v-if="!user" class="mini-login" @click="goLogin">登录</button>
    </view>

    <view class="balance-banner">
      <view>
        <view class="balance-label">可用起名次数</view>
        <view class="balance-value">{{ user ? balance : '—' }}</view>
      </view>
      <button class="refresh-btn" :loading="balanceLoading" @click="loadBalance">刷新</button>
    </view>

    <view v-if="isAdmin" class="admin-entry" @click="openAdminUsers">
      <view class="admin-icon">管</view>
      <view class="admin-entry-main">
        <view class="admin-entry-title">用户管理</view>
        <view class="admin-entry-desc">查询、冻结、解冻或删除普通用户</view>
      </view>
      <view class="admin-arrow">›</view>
    </view>

    <view class="purchase-heading">
      <view class="purchase-mark">
        <view class="mark-ticket">充</view>
        <view class="mark-spark">✦</view>
      </view>
      <view class="purchase-title-wrap">
        <view class="purchase-title">套餐购买</view>
        <view class="purchase-subtitle">选择适合你的起名次数</view>
      </view>
      <view class="sandbox-tag">支付宝沙箱</view>
    </view>
    <view v-if="packageLoading" class="card center-text">正在加载套餐…</view>
    <view v-else-if="!packages.length" class="card center-text">暂无上架套餐，或后端尚未连接。</view>
    <view v-for="(item, index) in packages" :key="item.id" class="package-card" :class="{ featured: index === 1 }">
      <view v-if="index === 1" class="recommend-tag">推荐</view>
      <view class="package-info">
        <view class="package-name">{{ item.name }}</view>
        <view class="package-count">包含 {{ item.credit_count }} 次起名</view>
      </view>
      <view class="price-wrap">
        <view class="price"><text>¥</text>{{ item.price }}</view>
        <button class="buy-btn" :loading="buyingId === item.id" :disabled="Boolean(buyingId)" @click="confirmCreateOrder(item)">购买</button>
      </view>
    </view>

    <view class="section-head">
      <text class="section-title">服务设置</text>
    </view>
    <view class="card settings-card">
      <view class="setting-title">后端服务地址</view>
      <view class="setting-desc">真机测试请改为电脑局域网 IP，不要使用 127.0.0.1。</view>
      <input v-model.trim="apiBaseUrl" class="server-input" placeholder="http://127.0.0.1:8000" />
      <button class="secondary-btn save-btn" @click="confirmSaveServer">保存并检查连接</button>
    </view>

    <button v-if="user" class="danger-btn logout-btn" @click="confirmLogout">退出登录</button>
  </view>
</template>

<script>
import { api } from '../../api'
import { clearLogin, getAccessToken, getUser, requireLogin } from '../../utils/auth'
import { getApiBaseUrl, setApiBaseUrl } from '../../utils/config'

export default {
  data() {
    return {
      user: null,
      balance: 0,
      balanceLoading: false,
      packageLoading: false,
      packages: [],
      buyingId: null,
      apiBaseUrl: ''
    }
  },
  computed: {
    isAdmin() {
      return Boolean(this.user && this.user.role === 'admin')
    },
    avatarText() {
      return this.user && this.user.username ? this.user.username.slice(0, 1).toUpperCase() : '访'
    }
  },
  onShow() {
    this.user = getUser()
    this.apiBaseUrl = getApiBaseUrl()
    this.loadPackages()
    if (getAccessToken()) this.loadBalance()
  },
  methods: {
    goLogin() { uni.navigateTo({ url: '/pages/auth/login' }) },
    openAdminUsers() { uni.navigateTo({ url: '/pages/admin/users' }) },
    async loadPackages() {
      this.packageLoading = true
      try { this.packages = await api.getPackages() }
      catch (error) { uni.showToast({ title: error.message, icon: 'none' }) }
      finally { this.packageLoading = false }
    },
    async loadBalance() {
      if (!requireLogin()) return
      this.balanceLoading = true
      try {
        const data = await api.getBalance()
        this.balance = data.balance
      } catch (error) {
        this.user = null
        uni.showToast({ title: error.message, icon: 'none' })
      } finally {
        this.balanceLoading = false
      }
    },
    confirmCreateOrder(item) {
      if (!requireLogin()) return
      uni.showModal({
        title: '确认创建支付订单',
        content: `准确动作：\n1. 为“${item.name}”创建一笔 ¥${item.price} 的未支付订单；\n2. 后端返回支付宝沙箱链接；\n3. 再由你决定是否打开支付宝页面。\n\n现在创建订单吗？`,
        confirmText: '创建订单',
        success: ({ confirm }) => {
          if (confirm) this.createOrder(item)
        }
      })
    },
    async createOrder(item) {
      this.buyingId = item.id
      try {
        const order = await api.createOrder(item.id)
        uni.showModal({
          title: '订单已创建',
          content: `订单号：${order.order_no}\n金额：¥${order.amount}\n到账次数：${order.credit_count}\n\n点击“打开支付宝”只会进入沙箱支付页，实际付款仍需你在支付宝页面确认。`,
          confirmText: '打开支付宝',
          cancelText: '暂不支付',
          success: ({ confirm }) => {
            if (confirm) this.openPayUrl(order.pay_url)
          }
        })
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 3000 })
      } finally {
        this.buyingId = null
      }
    },
    openPayUrl(url) {
      // #ifdef H5
      window.location.href = url
      // #endif

      // #ifndef H5
      uni.setClipboardData({
        data: url,
        success: () => uni.showModal({ title: '支付链接已复制', content: '请在浏览器中打开该链接完成沙箱支付。', showCancel: false })
      })
      // #endif
    },
    confirmSaveServer() {
      uni.showModal({
        title: '确认修改服务地址',
        content: `将本应用保存的后端地址修改为：\n${this.apiBaseUrl}\n\n之后所有接口测试都会访问这个地址。是否继续？`,
        confirmText: '确认修改',
        success: ({ confirm }) => {
          if (confirm) this.saveServer()
        }
      })
    },
    async saveServer() {
      try {
        setApiBaseUrl(this.apiBaseUrl)
        await api.health()
        uni.showToast({ title: '保存成功，后端可访问', icon: 'success' })
        this.loadPackages()
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 3200 })
      }
    },
    confirmLogout() {
      uni.showModal({
        title: '确认退出登录',
        content: '将删除本应用本地保存的 access token、refresh token 和用户信息，不会删除后端账号。',
        confirmColor: '#d94a64',
        success: ({ confirm }) => {
          if (confirm) {
            clearLogin()
            this.user = null
            this.balance = 0
            uni.showToast({ title: '已退出登录', icon: 'success' })
          }
        }
      })
    }
  }
}
</script>

<style scoped>
.account-page { background: radial-gradient(circle at 100% 0, #f0e7ff 0, transparent 25%), #f5f7fb; }
.profile-card { display: flex; align-items: center; margin-top: 28rpx; padding: 28rpx; background: #fff; border-radius: 28rpx; box-shadow: 0 14rpx 38rpx rgba(36, 55, 86, 0.06); }
.avatar { display: flex; align-items: center; justify-content: center; width: 88rpx; height: 88rpx; color: #fff; background: linear-gradient(135deg, #6257e8, #9a72ef); border-radius: 26rpx; font-size: 35rpx; font-weight: 850; }
.profile-main { flex: 1; min-width: 0; margin-left: 20rpx; }
.profile-name { font-size: 30rpx; font-weight: 800; }
.profile-email { margin-top: 7rpx; overflow: hidden; color: #8c95a7; font-size: 21rpx; text-overflow: ellipsis; white-space: nowrap; }
.mini-login { width: 110rpx; height: 62rpx; margin: 0; color: #6257e8; background: #ebe9ff; border-radius: 17rpx; font-size: 23rpx; line-height: 62rpx; }
.balance-banner { display: flex; align-items: center; justify-content: space-between; margin-top: 20rpx; padding: 30rpx; color: #fff; background: linear-gradient(135deg, #30305e, #5548c4); border-radius: 28rpx; }
.balance-label { color: #d5d2f5; font-size: 22rpx; }
.balance-value { margin-top: 4rpx; font-size: 52rpx; font-weight: 850; }
.refresh-btn { width: 120rpx; height: 64rpx; margin: 0; color: #fff; background: rgba(255, 255, 255, 0.15); border: 1rpx solid rgba(255, 255, 255, 0.2); border-radius: 18rpx; font-size: 22rpx; line-height: 64rpx; }
.admin-entry { display: flex; align-items: center; margin-top: 20rpx; padding: 25rpx 27rpx; color: #fff; background: linear-gradient(135deg, #172033, #353c56); border-radius: 25rpx; box-shadow: 0 13rpx 30rpx rgba(23, 32, 51, 0.18); }
.admin-icon { display: flex; align-items: center; justify-content: center; width: 72rpx; height: 72rpx; color: #2d3150; background: #f2d586; border-radius: 19rpx; font-size: 27rpx; font-weight: 850; }
.admin-entry-main { flex: 1; margin-left: 19rpx; }
.admin-entry-title { font-size: 28rpx; font-weight: 800; }
.admin-entry-desc { margin-top: 6rpx; color: #c9cedb; font-size: 20rpx; }
.admin-arrow { color: #f2d586; font-size: 46rpx; font-weight: 300; }
.purchase-heading { display: flex; align-items: center; margin-top: 38rpx; padding: 24rpx 26rpx; background: linear-gradient(135deg, #ece9ff, #f7f5ff); border: 2rpx solid #ded9ff; border-radius: 25rpx; }
.purchase-mark { position: relative; flex: 0 0 76rpx; height: 76rpx; }
.mark-ticket { display: flex; align-items: center; justify-content: center; width: 68rpx; height: 68rpx; color: #fff; background: linear-gradient(135deg, #6257e8, #9673f0); border-radius: 20rpx; box-shadow: 0 10rpx 22rpx rgba(98, 87, 232, 0.22); font-size: 28rpx; font-weight: 850; }
.mark-spark { position: absolute; top: -12rpx; right: -2rpx; color: #f2a33a; font-size: 25rpx; }
.purchase-title-wrap { flex: 1; margin-left: 18rpx; }
.purchase-title { color: #332b78; font-size: 30rpx; font-weight: 820; }
.purchase-subtitle { margin-top: 5rpx; color: #827ca4; font-size: 21rpx; }
.sandbox-tag { padding: 9rpx 14rpx; color: #71652f; background: #fff5c9; border-radius: 999rpx; font-size: 18rpx; }
.package-card { position: relative; display: flex; align-items: center; justify-content: space-between; margin-top: 18rpx; padding: 27rpx; overflow: hidden; background: #fff; border: 2rpx solid transparent; border-radius: 25rpx; box-shadow: 0 12rpx 34rpx rgba(36, 55, 86, 0.05); }
.package-card.featured { border-color: #bbb3ff; background: linear-gradient(135deg, #fff, #f4f2ff); }
.recommend-tag { position: absolute; top: 0; left: 0; padding: 7rpx 18rpx; color: #fff; background: #7164e9; border-radius: 0 0 16rpx 0; font-size: 18rpx; }
.package-name { font-size: 28rpx; font-weight: 780; }
.package-count { margin-top: 8rpx; color: #8b94a5; font-size: 22rpx; }
.price-wrap { display: flex; align-items: center; gap: 18rpx; }
.price { color: #423893; font-size: 36rpx; font-weight: 850; }
.price text { margin-right: 3rpx; font-size: 19rpx; }
.buy-btn { width: 105rpx; height: 64rpx; margin: 0; color: #fff; background: #6257e8; border-radius: 18rpx; font-size: 22rpx; line-height: 64rpx; }
.center-text { color: #8b94a5; font-size: 24rpx; text-align: center; }
.settings-card { padding: 4rpx 28rpx 28rpx; }
.setting-title { font-size: 27rpx; font-weight: 720; }
.setting-desc { margin-top: 6rpx; color: #939cad; font-size: 21rpx; line-height: 1.5; }
.server-input { height: 82rpx; margin-top: 18rpx; padding: 0 20rpx; background: #f4f6fa; border-radius: 17rpx; font-size: 24rpx; }
.save-btn { height: 76rpx; margin-top: 16rpx; line-height: 76rpx; }
.logout-btn { margin-top: 26rpx; }
</style>
