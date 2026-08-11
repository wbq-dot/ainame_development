<template>
  <view class="page-shell center-page">
    <view class="center-hero"><view class="eyebrow">EXPERT SERVICE</view><view class="hero-title">专家服务中心</view><view class="hero-desc">一个入口处理客户订单、专家申请和专家工作台。</view><view v-if="user" class="role-chip">当前身份：{{ roleText }}</view></view>
    <view class="entry-card" @click="openMarket"><view class="entry-icon purple">名</view><view class="entry-main"><view class="entry-title">专家起名</view><view class="entry-desc">填写出生、五行与客户期望，选择三档专家套餐</view></view><view class="arrow">›</view></view>
    <view class="entry-card" @click="openOrders"><view class="entry-icon blue">单</view><view class="entry-main"><view class="entry-title">我的专家订单</view><view class="entry-desc">查看付款、接单、专家回复、修改与评价</view></view><view class="arrow">›</view></view>
    <view v-if="isExpert" class="entry-card featured" @click="openWorkbench"><view class="entry-icon gold">专</view><view class="entry-main"><view class="entry-title">专家订单池与工作台</view><view class="entry-desc">选择同等级客户订单，交付结果并申请结算</view></view><view class="arrow">›</view></view>
    <view v-else-if="!isAdmin" class="entry-card" @click="openApply"><view class="entry-icon green">入</view><view class="entry-main"><view class="entry-title">申请成为起名专家</view><view class="entry-desc">提交专家资料，审核通过后获得专家角色</view></view><view class="arrow">›</view></view>
  </view>
</template>

<script>
import { getUser } from '../../utils/auth'
export default {
  data() { return { user: null } },
  computed: { isExpert() { return this.user && this.user.role === 'expert' }, isAdmin() { return this.user && this.user.role === 'admin' }, roleText() { return this.isExpert ? '专家' : this.isAdmin ? '管理员' : '普通用户' } },
  onShow() { this.user = getUser() },
  methods: { openMarket() { uni.navigateTo({ url: '/pages/expert/index' }) }, openOrders() { uni.navigateTo({ url: '/pages/expert/orders' }) }, openWorkbench() { uni.navigateTo({ url: '/pages/expert/workbench' }) }, openApply() { uni.navigateTo({ url: '/pages/expert/apply' }) } }
}
</script>

<style scoped>
.center-page{background:#f5f7fb}.center-hero{padding:37rpx;color:#fff;background:linear-gradient(145deg,#252350,#6451d6);border-radius:32rpx}.eyebrow{color:#d9d3ff;font-size:17rpx;font-weight:800;letter-spacing:4rpx}.hero-title{margin-top:13rpx;font-size:40rpx;font-weight:850}.hero-desc{margin-top:9rpx;color:#e1defa;font-size:21rpx;line-height:1.6}.role-chip{display:inline-block;margin-top:22rpx;padding:9rpx 14rpx;color:#453b9f;background:#fff;border-radius:999rpx;font-size:18rpx;font-weight:750}.entry-card{display:flex;align-items:center;margin-top:18rpx;padding:25rpx;background:#fff;border-radius:24rpx;box-shadow:0 10rpx 30rpx rgba(36,55,86,.05)}.entry-card.featured{border:2rpx solid #e6ce8e;background:linear-gradient(135deg,#fffdf6,#fff)}.entry-icon{display:flex;align-items:center;justify-content:center;width:66rpx;height:66rpx;margin-right:17rpx;border-radius:19rpx;font-size:23rpx;font-weight:850}.purple{color:#5549be;background:#ebe9ff}.blue{color:#32709b;background:#e8f5ff}.gold{color:#795c1f;background:#fff2d0}.green{color:#237553;background:#e6f7ef}.entry-main{flex:1}.entry-title{font-size:25rpx;font-weight:820}.entry-desc{margin-top:6rpx;color:#8e97a8;font-size:19rpx;line-height:1.5}.arrow{color:#786de4;font-size:38rpx}
</style>
