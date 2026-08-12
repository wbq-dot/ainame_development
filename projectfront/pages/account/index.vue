<template>
  <view class="page-shell account-page">
    <view class="page-title">我的</view>
    <view class="page-subtitle">管理账户权益、安全与使用偏好。</view>

    <view class="profile-card">
      <view class="avatar">{{ avatarText }}</view>
      <view class="profile-main">
        <view class="profile-name">{{ user ? user.username : '尚未登录' }}</view>
        <view class="profile-email">{{ user ? user.email : '登录后查看次数并购买套餐' }}</view>
      </view>
      <view v-if="user" class="profile-qr" @click="showQr = true"><view class="mini-qr"><text v-for="cell in miniQrCells" :key="cell.index" :class="{ active: cell.active }"></text></view><text>二维码</text></view>
      <button v-if="!user" class="mini-login" @click="goLogin">登录</button>
    </view>

    <view class="balance-banner">
      <view class="balance-grid">
        <view class="balance-item">
          <view class="balance-label">起名次数</view>
          <view class="balance-value">{{ user ? nameBalance : '—' }}</view>
        </view>
        <view class="balance-divider"></view>
        <view class="balance-item">
          <view class="balance-label">Logo 次数</view>
          <view class="balance-value">{{ user ? logoBalance : '—' }}</view>
        </view>
      </view>
      <button class="refresh-btn" :loading="balanceLoading" @click="loadBalance">刷新</button>
    </view>

    <view v-if="user" class="expert-entry-grid">
      <view class="expert-entry" @click="openExpertCenter"><view class="expert-entry-icon purple">专</view><view><view class="expert-entry-title">专家服务</view><view class="expert-entry-desc">专家起名订单、入驻与工作台统一入口</view></view><view class="expert-entry-arrow">›</view></view>
    </view>
    <view class="expert-entry-grid">
      <view class="expert-entry" @click="openDeveloperPortal"><view class="expert-entry-icon purple">API</view><view><view class="expert-entry-title">开发者开放平台</view><view class="expert-entry-desc">独立账号、API Key、批量命名、统计与推广</view></view><view class="expert-entry-arrow">›</view></view>
    </view>

    <view v-if="isAdmin" class="admin-entry" @click="openAdminUsers">
      <view class="admin-icon">管</view>
      <view class="admin-entry-main">
        <view class="admin-entry-title">管理后台</view>
        <view class="admin-entry-desc">管理用户、账户余额和套餐状态</view>
      </view>
      <view class="admin-arrow">›</view>
    </view>
    <view v-if="isAdmin" class="admin-entry expert-admin" @click="openAdminExperts">
      <view class="admin-icon">专</view>
      <view class="admin-entry-main"><view class="admin-entry-title">专家服务管理</view><view class="admin-entry-desc">审核专家、套餐、争议退款与结算</view></view>
      <view class="admin-arrow">›</view>
    </view>
    <view v-if="isAdmin" class="admin-entry expert-admin" @click="openAdminPlatform">
      <view class="admin-icon">B</view><view class="admin-entry-main"><view class="admin-entry-title">开放平台管理</view><view class="admin-entry-desc">开发者、API 套餐、推广佣金与任务</view></view><view class="admin-arrow">›</view>
    </view>

    <view class="feature-section">
      <view class="feature-heading"><view><view class="feature-title">账号与设置</view><view class="feature-subtitle">安全、记录与设备偏好</view></view><view class="feature-decoration"><text></text><text></text><text></text></view></view>
      <view class="feature-list">
        <view v-for="item in featureMenus" :key="item.key" class="feature-item" @click="openFeature(item)">
          <view class="feature-icon" :style="{ color: item.color, background: item.background }">{{ item.icon }}</view>
          <view class="feature-copy"><view class="feature-name">{{ item.title }}</view><view class="feature-desc">{{ item.desc }}</view></view>
          <view class="feature-arrow">›</view>
        </view>
      </view>
    </view>

    <view class="purchase-heading" :class="{ expanded: packagesExpanded }" @click="togglePackages">
      <view class="purchase-mark">
        <view class="mark-ticket">充</view>
        <view class="mark-spark">✦</view>
      </view>
      <view class="purchase-title-wrap">
        <view class="purchase-title">套餐购买</view>
        <view class="purchase-subtitle">{{ packagesExpanded ? '收起套餐列表' : '点击查看套餐与价格' }}</view>
      </view>
      <view class="sandbox-tag">支付宝支付</view>
      <view class="purchase-arrow">⌄</view>
    </view>
    <view v-if="packagesExpanded" class="package-list">
      <view class="package-tabs">
        <view class="package-tab" :class="{ active: packageType === 'name' }" @click="setPackageType('name')">起名套餐</view>
        <view class="package-tab" :class="{ active: packageType === 'logo' }" @click="setPackageType('logo')">Logo 套餐</view>
      </view>
      <view v-if="packageLoading" class="card center-text">正在加载套餐…</view>
      <view v-else-if="!filteredPackages.length" class="card center-text">暂无上架的{{ packageType === 'logo' ? ' Logo ' : '起名' }}套餐。</view>
      <view v-for="(item, index) in filteredPackages" :key="item.id" class="package-card" :class="{ featured: index === 1 }">
        <view v-if="index === 1" class="recommend-tag">推荐</view>
        <view class="package-info">
          <view class="package-name">{{ item.name }}</view>
          <view class="package-count">到账 {{ item.credit_count }} 次{{ creditLabel(item.credit_type) }}</view>
        </view>
        <view class="price-wrap">
          <view class="price"><text>¥</text>{{ item.price }}</view>
          <button class="buy-btn" :loading="buyingId === item.id" :disabled="Boolean(buyingId)" @click.stop="confirmCreateOrder(item)">购买</button>
        </view>
      </view>
    </view>

    <button v-if="user" class="danger-btn logout-btn" @click="confirmLogout">退出登录</button>

    <view v-if="showQr" class="modal-mask" @click="showQr = false">
      <view class="qr-modal" @click.stop>
        <view class="qr-close" @click="showQr = false">×</view>
        <view class="qr-avatar">{{ avatarText }}</view>
        <view class="qr-name">{{ user ? user.username : '' }}</view>
        <view class="qr-email">{{ user ? user.email : '' }}</view>
        <view class="qr-code"><text v-for="cell in qrCells" :key="cell.index" :class="{ active: cell.active }"></text></view>
        <view class="qr-code-text">账号编码 {{ accountCode }}</view>
        <view class="qr-note">个人二维码预览不包含密码或登录令牌</view>
        <button class="secondary-btn copy-code" @click="copyAccountCode">复制账号编码</button>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../api'
import { clearLogin, getAccessToken, getUser, requireLogin, setUser } from '../../utils/auth'

export default {
  data() {
    return {
      user: null,
      nameBalance: 0,
      logoBalance: 0,
      balanceLoading: false,
      packageLoading: false,
      packages: [],
      packagesLoaded: false,
      packagesExpanded: false,
      buyingId: null,
      packageType: 'name',
      showQr: false,
      featureMenus: [
        { key: 'security', title: '账号安全', desc: '修改密码、绑定邮箱或注销账号', path: '/pages/security/index', icon: '盾', color: '#3d8b72', background: '#e5f7f0' },
        { key: 'orders', title: '订单与退款', desc: '查看支付状态并申请整单退款', path: '/pages/orders/index', icon: '单', color: '#4d63b3', background: '#e9eeff' },
        { key: 'history', title: '聊天记录', desc: '查看当前设备保存的起名记录', path: '/pages/history/index', icon: '记', color: '#b16b35', background: '#fff1df' },
        { key: 'settings', title: '通用设置', desc: '调整字号、对比度与动画效果', path: '/pages/settings/index', icon: '设', color: '#6257e8', background: '#ebe9ff' }
      ]
    }
  },
  computed: {
    isAdmin() {
      return Boolean(this.user && this.user.role === 'admin')
    },
    isExpert() {
      return Boolean(this.user && this.user.role === 'expert')
    },
    avatarText() {
      return this.user && this.user.username ? this.user.username.slice(0, 1).toUpperCase() : '访'
    },
    filteredPackages() {
      return this.packages.filter((item) => (item.credit_type || 'name') === this.packageType)
    },
    accountCode() {
      if (!this.user) return ''
      const id = this.user.id || this.user.user_id || 'USER'
      return `ZN-${String(id).padStart(6, '0')}`
    },
    qrCells() {
      return this.buildQrCells(11)
    },
    miniQrCells() {
      return this.buildQrCells(5)
    }
  },
  onShow() {
    this.user = getUser()
    if (getAccessToken()) {
      this.refreshUser()
      this.loadBalance()
    }
    const requestedType = uni.getStorageSync('account_package_type')
    if (requestedType === 'name' || requestedType === 'logo') {
      this.packageType = requestedType
      this.packagesExpanded = true
      uni.removeStorageSync('account_package_type')
      if (!this.packagesLoaded) this.loadPackages()
    }
  },
  methods: {
    goLogin() { uni.navigateTo({ url: '/pages/auth/login' }) },
    openAdminUsers() { uni.navigateTo({ url: '/pages/admin/users' }) },
    openAdminExperts() { uni.navigateTo({ url: '/pages/admin/experts' }) },
    openAdminPlatform() { uni.navigateTo({ url: '/pages/admin/platform' }) },
    openDeveloperPortal() { uni.navigateTo({ url: '/pages/developer/login' }) },
    openExpertCenter() { uni.navigateTo({ url: '/pages/expert/center' }) },
    async refreshUser() {
      try {
        this.user = await api.getMe()
        setUser(this.user)
      } catch (error) {
        // 请求层会在登录失效时清理本地状态。
      }
    },
    buildQrCells(size) {
      const seedText = this.accountCode || 'ZN'
      let seed = 0
      for (let index = 0; index < seedText.length; index += 1) seed = (seed * 31 + seedText.charCodeAt(index)) >>> 0
      return Array.from({ length: size * size }, (_, index) => {
        const row = Math.floor(index / size)
        const column = index % size
        const inTopLeft = row < 3 && column < 3
        const inTopRight = row < 3 && column >= size - 3
        const inBottomLeft = row >= size - 3 && column < 3
        const finder = inTopLeft || inTopRight || inBottomLeft
        const finderActive = finder && (row % (size - 3 || 1) !== 1 || column % (size - 3 || 1) !== 1)
        const randomActive = ((seed + index * 17 + row * column * 13) % 7) < 3
        return { index, active: finder ? finderActive : randomActive }
      })
    },
    openFeature(item) {
      if ((item.key === 'security' || item.key === 'orders') && !this.user) { this.goLogin(); return }
      uni.navigateTo({ url: item.path })
    },
    copyAccountCode() {
      uni.setClipboardData({ data: this.accountCode, success: () => uni.showToast({ title: '账号编码已复制', icon: 'success' }) })
    },
    async togglePackages() {
      this.packagesExpanded = !this.packagesExpanded
      if (this.packagesExpanded && !this.packagesLoaded) await this.loadPackages()
    },
    setPackageType(type) {
      this.packageType = type
    },
    creditLabel(type) {
      return type === 'logo' ? 'Logo' : '起名'
    },
    async loadPackages() {
      this.packageLoading = true
      try {
        this.packages = await api.getPackages()
        this.packagesLoaded = true
      }
      catch (error) { uni.showToast({ title: error.message, icon: 'none' }) }
      finally { this.packageLoading = false }
    },
    async loadBalance() {
      if (!requireLogin()) return
      this.balanceLoading = true
      try {
        const data = await api.getBalance()
        this.nameBalance = data.name_balance ?? data.balance ?? 0
        this.logoBalance = data.logo_balance ?? 0
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
        content: `准确动作：\n1. 为“${item.name}”创建一笔 ¥${item.price} 的未支付订单；\n2. 只有支付宝异步通知或主动查单确认后才会到账 ${item.credit_count} 次${this.creditLabel(item.credit_type)}；\n3. 订单支付窗口为 60 分钟。\n\n现在创建订单吗？`,
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
          content: `订单号：${order.order_no}\n金额：¥${order.amount}\n到账：${order.credit_count} 次${this.creditLabel(order.credit_type)}\n\n点击“打开支付宝”进入收银台，实际付款仍需你在支付宝页面确认。`,
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
        success: () => uni.showModal({ title: '支付链接已复制', content: '请在浏览器中打开该链接完成支付，返回应用后可在“订单与退款”查询状态。', showCancel: false })
      })
      // #endif
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
            this.nameBalance = 0
            this.logoBalance = 0
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
.profile-qr { display: flex; flex-direction: column; align-items: center; gap: 5rpx; color: #8a92a2; font-size: 17rpx; }
.mini-qr { display: grid; grid-template-columns: repeat(5, 5rpx); gap: 2rpx; padding: 7rpx; background: #f4f3ff; border-radius: 10rpx; }
.mini-qr text { width: 5rpx; height: 5rpx; background: transparent; }
.mini-qr text.active { background: #4d43ae; }
.mini-login { width: 110rpx; height: 62rpx; margin: 0; color: #6257e8; background: #ebe9ff; border-radius: 17rpx; font-size: 23rpx; line-height: 62rpx; }
.balance-banner { display: flex; align-items: center; justify-content: space-between; gap: 22rpx; margin-top: 20rpx; padding: 30rpx; color: #fff; background: linear-gradient(135deg, #30305e, #5548c4); border-radius: 28rpx; }
.balance-grid { display: flex; flex: 1; align-items: center; }
.balance-item { flex: 1; }
.balance-divider { width: 1rpx; height: 72rpx; margin: 0 26rpx; background: rgba(255, 255, 255, 0.2); }
.balance-label { color: #d5d2f5; font-size: 22rpx; }
.balance-value { margin-top: 4rpx; font-size: 52rpx; font-weight: 850; }
.expert-entry-grid { margin-top: 20rpx; }
.expert-entry { display: flex; align-items: center; min-height: 115rpx; padding: 21rpx; background: #fff; border-radius: 22rpx; box-shadow: 0 10rpx 28rpx rgba(36,55,86,.05); }
.expert-entry-icon { display: flex; flex: 0 0 58rpx; align-items: center; justify-content: center; width: 58rpx; height: 58rpx; margin-right: 14rpx; border-radius: 17rpx; font-size: 22rpx; font-weight: 850; }
.expert-entry-icon.purple { color: #5549be; background: #ebe9ff; }.expert-entry-icon.gold { color: #795c1f; background: #fff2d0; }.expert-entry-icon.green { color: #237553; background: #e6f7ef; }
.expert-entry-title { font-size: 23rpx; font-weight: 800; }.expert-entry-desc { margin-top: 4rpx; color: #929aaa; font-size: 17rpx; line-height: 1.4; }
.expert-entry-arrow { margin-left: auto; color: #776ce3; font-size: 36rpx; }
.refresh-btn { width: 120rpx; height: 64rpx; margin: 0; color: #fff; background: rgba(255, 255, 255, 0.15); border: 1rpx solid rgba(255, 255, 255, 0.2); border-radius: 18rpx; font-size: 22rpx; line-height: 64rpx; }
.admin-entry { display: flex; align-items: center; margin-top: 20rpx; padding: 25rpx 27rpx; color: #fff; background: linear-gradient(135deg, #172033, #353c56); border-radius: 25rpx; box-shadow: 0 13rpx 30rpx rgba(23, 32, 51, 0.18); }
.admin-entry.expert-admin { background: linear-gradient(135deg, #302b61, #594db1); }
.admin-icon { display: flex; align-items: center; justify-content: center; width: 72rpx; height: 72rpx; color: #2d3150; background: #f2d586; border-radius: 19rpx; font-size: 27rpx; font-weight: 850; }
.admin-entry-main { flex: 1; margin-left: 19rpx; }
.admin-entry-title { font-size: 28rpx; font-weight: 800; }
.admin-entry-desc { margin-top: 6rpx; color: #c9cedb; font-size: 20rpx; }
.admin-arrow { color: #f2d586; font-size: 46rpx; font-weight: 300; }
.feature-section { margin-top: 27rpx; }
.feature-heading { display: flex; align-items: center; justify-content: space-between; padding: 0 5rpx; }
.feature-title { font-size: 31rpx; font-weight: 850; }
.feature-subtitle { margin-top: 6rpx; color: #929aaa; font-size: 20rpx; }
.feature-decoration { display: flex; gap: 7rpx; }
.feature-decoration text { width: 12rpx; height: 12rpx; background: #6257e8; border-radius: 50%; }
.feature-decoration text:nth-child(2) { background: #79cfb7; }
.feature-decoration text:nth-child(3) { background: #f2bd68; }
.feature-list { display: flex; flex-direction: column; gap: 16rpx; margin-top: 18rpx; }
.feature-item { display: flex; align-items: center; min-height: 120rpx; padding: 23rpx 25rpx; background: #fff; border: 1rpx solid rgba(31,55,90,.055); border-radius: 25rpx; box-shadow: 0 11rpx 32rpx rgba(36,55,86,.055); }
.feature-item:active { transform: scale(.99); opacity: .84; }
.feature-icon { display: flex; flex: 0 0 64rpx; align-items: center; justify-content: center; width: 64rpx; height: 64rpx; border-radius: 19rpx; font-size: 23rpx; font-weight: 900; }
.feature-copy { flex: 1; min-width: 0; margin-left: 20rpx; }
.feature-name { font-size: 26rpx; font-weight: 800; }
.feature-desc { margin-top: 7rpx; color: #949cab; font-size: 20rpx; line-height: 1.45; }
.feature-arrow { margin-left: 18rpx; color: #8f87cf; font-size: 42rpx; font-weight: 300; }
.purchase-heading { display: flex; align-items: center; margin-top: 38rpx; padding: 24rpx 26rpx; background: linear-gradient(135deg, #ece9ff, #f7f5ff); border: 2rpx solid #ded9ff; border-radius: 25rpx; transition: border-radius 0.2s ease, box-shadow 0.2s ease; }
.purchase-heading.expanded { border-color: #c8c0ff; box-shadow: 0 12rpx 30rpx rgba(98, 87, 232, 0.1); }
.purchase-mark { position: relative; flex: 0 0 76rpx; height: 76rpx; }
.mark-ticket { display: flex; align-items: center; justify-content: center; width: 68rpx; height: 68rpx; color: #fff; background: linear-gradient(135deg, #6257e8, #9673f0); border-radius: 20rpx; box-shadow: 0 10rpx 22rpx rgba(98, 87, 232, 0.22); font-size: 28rpx; font-weight: 850; }
.mark-spark { position: absolute; top: -12rpx; right: -2rpx; color: #f2a33a; font-size: 25rpx; }
.purchase-title-wrap { flex: 1; margin-left: 18rpx; }
.purchase-title { color: #332b78; font-size: 30rpx; font-weight: 820; }
.purchase-subtitle { margin-top: 5rpx; color: #827ca4; font-size: 21rpx; }
.sandbox-tag { padding: 9rpx 14rpx; color: #71652f; background: #fff5c9; border-radius: 999rpx; font-size: 18rpx; }
.purchase-arrow { margin-left: 14rpx; color: #6257e8; font-size: 38rpx; line-height: 1; transform: rotate(0deg); transition: transform 0.2s ease; }
.purchase-heading.expanded .purchase-arrow { transform: rotate(180deg); }
.package-list { padding-top: 2rpx; }
.package-tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 8rpx; margin-top: 18rpx; padding: 8rpx; background: #e9ecf2; border-radius: 20rpx; }
.package-tab { height: 68rpx; color: #7c8494; border-radius: 15rpx; font-size: 23rpx; font-weight: 700; line-height: 68rpx; text-align: center; }
.package-tab.active { color: #4439b0; background: #fff; box-shadow: 0 7rpx 20rpx rgba(36, 55, 86, 0.08); }
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
.logout-btn { margin-top: 26rpx; }
.modal-mask { position: fixed; z-index: 999; top: 0; right: 0; bottom: 0; left: 0; display: flex; align-items: center; justify-content: center; padding: 40rpx; background: rgba(20,23,43,.55); backdrop-filter: blur(8rpx); }
.qr-modal { position: relative; width: 610rpx; padding: 40rpx 42rpx 38rpx; background: linear-gradient(155deg,#fff,#f4f2ff); border-radius: 35rpx; box-shadow: 0 30rpx 80rpx rgba(16,17,49,.28); text-align: center; }
.qr-close { position: absolute; top: 18rpx; right: 22rpx; width: 55rpx; height: 55rpx; color: #7e8594; background: #eceef3; border-radius: 50%; font-size: 38rpx; line-height: 50rpx; }
.qr-avatar { display: flex; align-items: center; justify-content: center; width: 82rpx; height: 82rpx; margin: 0 auto; color: #fff; background: linear-gradient(135deg,#6257e8,#9a72ef); border-radius: 24rpx; font-size: 34rpx; font-weight: 900; }
.qr-name { margin-top: 15rpx; color: #26224e; font-size: 30rpx; font-weight: 850; }
.qr-email { margin-top: 5rpx; color: #949baa; font-size: 20rpx; }
.qr-code { display: grid; grid-template-columns: repeat(11, 14rpx); gap: 4rpx; justify-content: center; width: 240rpx; margin: 25rpx auto 0; padding: 20rpx; background: #fff; border: 2rpx solid #e1def5; border-radius: 19rpx; box-shadow: 0 10rpx 28rpx rgba(68,56,147,.09); }
.qr-code text { width: 14rpx; height: 14rpx; background: transparent; border-radius: 2rpx; }
.qr-code text.active { background: #292452; }
.qr-code-text { margin-top: 17rpx; color: #5147b9; font-size: 22rpx; font-weight: 780; letter-spacing: 2rpx; }
.qr-note { margin-top: 9rpx; color: #9aa1af; font-size: 18rpx; }
.copy-code { margin-top: 23rpx; }
</style>
