<template>
  <view class="console-page">
    <view class="console-hero">
      <view class="hero-topline">
        <view class="brand-mark">管</view>
        <view class="hero-actions">
          <view class="secure-badge"><text></text>管理员会话</view>
          <button class="logout-btn" @click="confirmLogout">退出</button>
        </view>
      </view>
      <view class="hero-eyebrow">ADMIN CONSOLE</view>
      <view class="hero-title">管理控制台</view>
      <view class="hero-desc">从操作列表进入对应管理页面，每个模块独立处理、互不干扰。</view>
      <view class="admin-profile">
        <view class="admin-avatar">{{ avatarText }}</view>
        <view class="admin-copy">
          <view>{{ adminName }}</view>
          <text>{{ adminEmail }}</text>
        </view>
        <view class="operation-count"><b>{{ operationCount }}</b><text>项操作</text></view>
      </view>
    </view>

    <view class="overview-strip">
      <view><b>{{ operationGroups.length }}</b><text>管理分组</text></view>
      <view class="strip-divider"></view>
      <view><b>{{ operationCount }}</b><text>独立入口</text></view>
      <view class="strip-divider"></view>
      <view><b>1</b><text>统一控制台</text></view>
    </view>

    <view v-for="group in operationGroups" :key="group.key" class="operation-section">
      <view class="section-heading">
        <view>
          <view class="section-title">{{ group.title }}</view>
          <view class="section-desc">{{ group.description }}</view>
        </view>
        <view class="section-count">{{ group.items.length }}</view>
      </view>

      <view class="operation-list">
        <button
          v-for="item in group.items"
          :key="item.key"
          class="operation-item"
          hover-class="operation-item-hover"
          @click="openOperation(item)"
        >
          <view class="operation-icon" :class="item.tone">{{ item.icon }}</view>
          <view class="operation-main">
            <view class="operation-title-row">
              <view class="operation-title">{{ item.title }}</view>
              <text v-if="item.tag" class="operation-tag">{{ item.tag }}</text>
            </view>
            <view class="operation-desc">{{ item.description }}</view>
            <view class="operation-actions">{{ item.actions }}</view>
          </view>
          <view class="operation-arrow">›</view>
        </button>
      </view>
    </view>

    <view class="console-note">
      <view class="note-icon">记</view>
      <view><b>操作留痕</b><text>冻结、删除、套餐新建与编辑、审核、退款和结算等关键动作会按后端规则记录。</text></view>
    </view>
  </view>
</template>

<script>
import { getUser, logoutAdmin, requireAdminSession } from '../../utils/auth'

export default {
  data() {
    return {
      admin: null,
      operationGroups: [
        {
          key: 'accounts',
          title: '用户与权益',
          description: '维护用户账号、使用次数和平台套餐',
          items: [
            { key: 'users', title: '用户账户管理', description: '查询用户资料与账号状态', actions: '调整余额 · 冻结 / 解冻 · 删除账号', path: '/pages/admin/users', icon: '用', tone: 'purple', tag: '核心' },
            { key: 'packages', title: '平台套餐管理', description: '新建、编辑起名与 Logo 套餐', actions: '新建 · 编辑 · 筛选 · 上架 / 下架', path: '/pages/admin/packages', icon: '套', tone: 'blue' }
          ]
        },
        {
          key: 'transactions',
          title: '交易与售后',
          description: '处理用户退款申请与异常退款流程',
          items: [
            { key: 'refunds', title: '退款审批', description: '查询退款单并审核整单退款', actions: '批准 · 驳回 · 查退 / 重试', path: '/pages/admin/refunds', icon: '退', tone: 'orange', tag: '资金' }
          ]
        },
        {
          key: 'platform',
          title: '内容与开放平台',
          description: '管理社区内容、开发者、API 商品、增长分销与后台任务',
          items: [
            { key: 'community', title: '社区内容管理', description: '审核并处理社区话题、评论与举报', actions: '筛选 · 置顶 · 隐藏 / 恢复 · 举报处理', path: '/pages/admin/community', icon: '社', tone: 'purple' },
            { key: 'open-platform', title: '开放平台管理', description: '统一管理开发者与开放 API 业务', actions: '开发者 · 调用明细 · API 套餐 · 活动佣金 · 任务重试', path: '/pages/admin/platform', icon: 'B', tone: 'blue', tag: 'B端' }
          ]
        },
        {
          key: 'experts',
          title: '专家服务',
          description: '分开处理专家准入、商品、订单与结算',
          items: [
            { key: 'expert-applications', title: '专家资质审核', description: '审核入驻资料并管理专家资格', actions: '查看资质 · 通过 / 驳回 · 停用 / 恢复', path: '/pages/admin/experts', icon: '审', tone: 'green' },
            { key: 'expert-packages', title: '专家套餐审核', description: '审核专家提交的服务套餐', actions: '通过上架 · 驳回 · 下架', path: '/pages/admin/expert-packages', icon: '服', tone: 'cyan' },
            { key: 'expert-orders', title: '专家争议订单', description: '处理争议或取消的专家服务订单', actions: '判定完成 · 登记人工退款', path: '/pages/admin/expert-orders', icon: '争', tone: 'red', tag: '需谨慎' },
            { key: 'expert-settlements', title: '专家结算处理', description: '核对专家结算申请与线下打款', actions: '登记已打款 · 驳回申请', path: '/pages/admin/expert-settlements', icon: '结', tone: 'gold', tag: '资金' }
          ]
        }
      ]
    }
  },
  computed: {
    operationCount() {
      return this.operationGroups.reduce((total, group) => total + group.items.length, 0)
    },
    adminName() {
      return (this.admin && this.admin.username) || '管理员'
    },
    adminEmail() {
      return (this.admin && this.admin.email) || '已通过管理员权限验证'
    },
    avatarText() {
      return this.adminName.slice(0, 1).toUpperCase()
    }
  },
  onShow() {
    if (!requireAdminSession()) return
    this.admin = getUser()
  },
  methods: {
    openOperation(item) {
      uni.navigateTo({ url: item.path })
    },
    confirmLogout() {
      uni.showModal({
        title: '退出管理员登录',
        content: '退出后将清除当前设备保存的管理员登录状态。',
        confirmColor: '#d94a64',
        success: ({ confirm }) => {
          if (confirm) logoutAdmin()
        }
      })
    }
  }
}
</script>

<style scoped>
.console-page { min-height: 100vh; padding: 28rpx 28rpx 70rpx; background: radial-gradient(circle at 100% 0, #e9e5ff 0, transparent 25%), #f3f5f9; }
.console-hero { padding: 30rpx; color: #fff; background: radial-gradient(circle at 88% 10%, rgba(242,213,134,.22) 0, transparent 28%), linear-gradient(145deg,#151b2b,#343a54); border-radius: 30rpx; box-shadow: 0 20rpx 46rpx rgba(23,29,45,.2); }
.hero-topline { display: flex; align-items: center; justify-content: space-between; }
.brand-mark { display: flex; align-items: center; justify-content: center; width: 62rpx; height: 62rpx; color: #272d42; background: linear-gradient(135deg,#f5dc94,#d9b455); border-radius: 18rpx; font-size: 24rpx; font-weight: 900; }
.hero-actions { display: flex; align-items: center; gap: 12rpx; }
.secure-badge { display: flex; align-items: center; gap: 8rpx; padding: 10rpx 15rpx; color: #d9deea; background: rgba(255,255,255,.08); border-radius: 999rpx; font-size: 18rpx; }
.secure-badge text { width: 11rpx; height: 11rpx; background: #69d3a5; border-radius: 50%; box-shadow: 0 0 0 5rpx rgba(105,211,165,.12); }
.logout-btn { width: auto; height: 52rpx; margin: 0; padding: 0 18rpx; color: #f4dc99; background: transparent; border: 1rpx solid rgba(244,220,153,.35); border-radius: 15rpx; font-size: 18rpx; line-height: 50rpx; }
.hero-eyebrow { margin-top: 34rpx; color: #f2d586; font-size: 17rpx; font-weight: 800; letter-spacing: 4rpx; }
.hero-title { margin-top: 9rpx; font-size: 44rpx; font-weight: 880; letter-spacing: -1rpx; }
.hero-desc { max-width: 590rpx; margin-top: 10rpx; color: #c9cfdd; font-size: 21rpx; line-height: 1.55; }
.admin-profile { display: flex; align-items: center; margin-top: 28rpx; padding-top: 24rpx; border-top: 1rpx solid rgba(255,255,255,.1); }
.admin-avatar { display: flex; align-items: center; justify-content: center; width: 66rpx; height: 66rpx; color: #fff; background: linear-gradient(135deg,#7064e8,#a47cf0); border-radius: 19rpx; font-size: 26rpx; font-weight: 850; }
.admin-copy { flex: 1; min-width: 0; margin-left: 16rpx; }
.admin-copy view { font-size: 24rpx; font-weight: 800; }
.admin-copy text { display: block; margin-top: 5rpx; overflow: hidden; color: #aeb6c8; font-size: 18rpx; text-overflow: ellipsis; white-space: nowrap; }
.operation-count { display: flex; align-items: baseline; gap: 6rpx; color: #c5cad7; font-size: 18rpx; }
.operation-count b { color: #f2d586; font-size: 34rpx; }
.overview-strip { display: grid; grid-template-columns: 1fr auto 1fr auto 1fr; align-items: center; margin-top: 20rpx; padding: 23rpx 12rpx; background: #fff; border: 1rpx solid rgba(31,55,90,.05); border-radius: 23rpx; box-shadow: 0 10rpx 30rpx rgba(36,55,86,.05); }
.overview-strip > view:not(.strip-divider) { display: flex; flex-direction: column; align-items: center; }
.overview-strip b { color: #30364d; font-size: 28rpx; }
.overview-strip text { margin-top: 4rpx; color: #929aaa; font-size: 17rpx; }
.strip-divider { width: 1rpx; height: 46rpx; background: #e7e9ef; }
.operation-section { margin-top: 34rpx; }
.section-heading { display: flex; align-items: flex-end; justify-content: space-between; padding: 0 4rpx; }
.section-title { font-size: 31rpx; font-weight: 850; }
.section-desc { margin-top: 6rpx; color: #8c95a6; font-size: 19rpx; }
.section-count { display: flex; align-items: center; justify-content: center; width: 46rpx; height: 46rpx; color: #6257e8; background: #e9e7ff; border-radius: 14rpx; font-size: 21rpx; font-weight: 850; }
.operation-list { display: flex; flex-direction: column; gap: 14rpx; margin-top: 17rpx; }
.operation-item { display: flex; align-items: center; width: 100%; min-height: 142rpx; margin: 0; padding: 24rpx; color: #172033; background: #fff; border: 1rpx solid rgba(31,55,90,.055); border-radius: 25rpx; box-shadow: 0 11rpx 32rpx rgba(36,55,86,.055); line-height: normal; text-align: left; }
.operation-item-hover { opacity: .82; transform: scale(.99); }
.operation-icon { display: flex; flex: 0 0 68rpx; align-items: center; justify-content: center; width: 68rpx; height: 68rpx; border-radius: 20rpx; font-size: 24rpx; font-weight: 900; }
.operation-icon.purple { color: #584bbd; background: #eceaff; }
.operation-icon.blue { color: #3d64a9; background: #e9f0ff; }
.operation-icon.orange { color: #9b641e; background: #fff1d9; }
.operation-icon.green { color: #207552; background: #e4f7ef; }
.operation-icon.cyan { color: #27777d; background: #e4f6f6; }
.operation-icon.red { color: #a94157; background: #fff0f3; }
.operation-icon.gold { color: #806321; background: #faf1d7; }
.operation-main { flex: 1; min-width: 0; margin-left: 19rpx; }
.operation-title-row { display: flex; align-items: center; gap: 10rpx; }
.operation-title { font-size: 26rpx; font-weight: 830; }
.operation-tag { padding: 5rpx 9rpx; color: #75661f; background: #fff4c7; border-radius: 999rpx; font-size: 15rpx; }
.operation-desc { margin-top: 7rpx; color: #7c8596; font-size: 20rpx; line-height: 1.4; }
.operation-actions { margin-top: 7rpx; color: #6257a5; font-size: 17rpx; }
.operation-arrow { margin-left: 14rpx; color: #928ad0; font-size: 44rpx; font-weight: 300; }
.console-note { display: flex; align-items: flex-start; gap: 15rpx; margin-top: 30rpx; padding: 22rpx; color: #687286; background: #e7eaf0; border-radius: 20rpx; }
.note-icon { display: flex; flex: 0 0 48rpx; align-items: center; justify-content: center; width: 48rpx; height: 48rpx; color: #4a5267; background: #fff; border-radius: 14rpx; font-size: 18rpx; font-weight: 850; }
.console-note b { display: block; color: #343b50; font-size: 21rpx; }
.console-note text { display: block; margin-top: 5rpx; font-size: 18rpx; line-height: 1.55; }

@media (min-width: 1000px) {
  .console-page { max-width: 1180px; margin: 0 auto; padding: 34px; }
  .console-hero { padding: 34px; }
  .operation-list { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); }
  .operation-section:nth-of-type(3) .operation-list { grid-template-columns: minmax(0,1fr); }
}
</style>
