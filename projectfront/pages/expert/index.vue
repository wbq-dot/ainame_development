<template>
  <view class="page-shell expert-market">
    <view class="market-hero">
      <view class="eyebrow">HUMAN NAMING SERVICE</view>
      <view class="hero-title">把出生信息与期望，交给真正的起名专家</view>
      <view class="hero-desc">填写姓氏、出生时辰、五行情况和家庭期望，付款后进入对应等级订单池，由专家主动接单并交付完整答复。</view>
      <button class="hero-btn" @click="startNaming">开始填写起名资料</button>
    </view>

    <view class="section-head">
      <view><view class="section-title">三档专家套餐</view><view class="muted">先填资料，提交前再确认套餐</view></view>
      <view class="pool-tag">专家抢单</view>
    </view>
    <view v-if="loading" class="card state">正在加载套餐…</view>
    <view v-for="(item,index) in tiers" :key="item.code" class="tier-card" :class="`tier-${item.code}`" @click="startNaming(item.code)">
      <view class="tier-rank">0{{ index + 1 }}</view>
      <view class="tier-main">
        <view class="tier-name">{{ item.name }}</view>
        <view class="tier-desc">{{ item.description }}</view>
        <view class="tier-meta"><text>{{ item.delivery_days }} 天内交付</text><text>一次免费修改</text><text>{{ tierExpertText(item.code) }}</text></view>
      </view>
      <view class="tier-price"><text>¥</text>{{ item.price }}</view>
    </view>

    <view class="process-card">
      <view class="section-title">服务流程</view>
      <view class="process-row" v-for="(item,index) in process" :key="item.title">
        <view class="process-index">{{ index + 1 }}</view>
        <view><view class="process-title">{{ item.title }}</view><view class="process-desc">{{ item.desc }}</view></view>
      </view>
    </view>
    <view class="bottom-actions">
      <button class="ghost-action" @click="openOrders">我的专家订单</button>
      <button class="ghost-action" @click="openApply">专家服务中心</button>
    </view>
  </view>
</template>

<script>
import { api } from '../../api'
import { requireLogin } from '../../utils/auth'

export default {
  data() {
    return {
      loading: false,
      tiers: [],
      process: [
        { title: '提交资料与图片', desc: '填写姓氏、出生时辰、五行和希望避开的字。' },
        { title: '选择专家套餐', desc: '按需求选择普通、知名或顶级专家订单池。' },
        { title: '专家主动接单', desc: '同等级专家查看需求并由其中一位确认接单。' },
        { title: '查看结果与修改', desc: '收到推荐名字、五行分析和专家最终回复。' }
      ]
    }
  },
  onShow() { this.loadTiers() },
  methods: {
    async loadTiers() {
      this.loading = true
      try { this.tiers = await api.getExpertTiers() }
      catch (error) { uni.showToast({ title: error.message, icon: 'none' }) }
      finally { this.loading = false }
    },
    tierExpertText(code) { return { ordinary: '普通专家池', renowned: '知名专家池', top: '顶级专家池' }[code] || '专家池' },
    startNaming(tier = 'ordinary') {
      if (requireLogin()) uni.navigateTo({ url: `/pages/expert/detail?tier=${tier}` })
    },
    openOrders() { if (requireLogin()) uni.navigateTo({ url: '/pages/expert/orders' }) },
    openApply() { if (requireLogin()) uni.navigateTo({ url: '/pages/expert/center' }) }
  }
}
</script>

<style scoped>
.expert-market{min-height:100vh;background:radial-gradient(circle at 100% 0,#e9e3ff 0,transparent 28%),#f5f7fb}.market-hero{padding:42rpx 34rpx;color:#fff;background:linear-gradient(145deg,#252350,#5948c7 65%,#7d64e8);border-radius:34rpx;box-shadow:0 22rpx 55rpx rgba(69,55,164,.24)}.eyebrow{color:#d9d3ff;font-size:18rpx;font-weight:800;letter-spacing:4rpx}.hero-title{margin-top:18rpx;font-size:44rpx;font-weight:850;line-height:1.3}.hero-desc{margin-top:18rpx;color:#e1defa;font-size:23rpx;line-height:1.7}.hero-btn{height:76rpx;margin:30rpx 0 0;color:#40368e;background:#fff;border-radius:20rpx;font-size:23rpx;font-weight:800;line-height:76rpx}.section-head{display:flex;align-items:end;justify-content:space-between;margin:34rpx 4rpx 12rpx}.section-title{font-size:30rpx;font-weight:850}.muted{margin-top:6rpx;color:#929aaa;font-size:19rpx}.pool-tag{padding:9rpx 14rpx;color:#5c51c7;background:#ece9ff;border-radius:999rpx;font-size:18rpx}.state{text-align:center;color:#8c95a7}.tier-card{position:relative;display:flex;align-items:center;gap:18rpx;margin-top:18rpx;padding:27rpx;background:#fff;border:1rpx solid #eceef4;border-radius:27rpx;box-shadow:0 13rpx 38rpx rgba(36,55,86,.06)}.tier-top{border-color:#e8cf94;background:linear-gradient(135deg,#fffdf6,#fff)}.tier-rank{color:#c3c8d3;font-size:24rpx;font-weight:900}.tier-top .tier-rank{color:#c28a28}.tier-main{flex:1}.tier-name{font-size:29rpx;font-weight:850}.tier-desc{margin-top:8rpx;color:#737e92;font-size:20rpx;line-height:1.55}.tier-meta{display:flex;flex-wrap:wrap;gap:8rpx;margin-top:13rpx}.tier-meta text{padding:7rpx 10rpx;color:#655cad;background:#f1efff;border-radius:10rpx;font-size:16rpx}.tier-price{color:#4338a1;font-size:36rpx;font-weight:900}.tier-price text{font-size:19rpx}.process-card{margin-top:27rpx;padding:28rpx;background:#fff;border-radius:28rpx}.process-row{display:flex;gap:16rpx;margin-top:22rpx}.process-index{display:flex;align-items:center;justify-content:center;width:44rpx;height:44rpx;color:#fff;background:#6257e8;border-radius:14rpx;font-size:18rpx;font-weight:800}.process-title{font-size:23rpx;font-weight:800}.process-desc{margin-top:5rpx;color:#8a93a4;font-size:19rpx;line-height:1.5}.bottom-actions{display:flex;gap:14rpx;margin-top:22rpx}.ghost-action{flex:1;height:72rpx;margin:0;color:#5147b5;background:#eeecff;border-radius:18rpx;font-size:21rpx;line-height:72rpx}
</style>
