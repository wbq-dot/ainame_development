<template>
  <view class="admin-community-page">
    <view class="admin-hero">
      <view><view class="eyebrow">COMMUNITY OPERATIONS</view><view class="hero-title">社区内容管理</view><view class="hero-desc">管理投票、精选和举报，隐藏操作不会删除原始数据</view></view>
      <view class="hero-count">{{ tab === 'topics' ? total : reports.length }}</view>
    </view>

    <view class="console-nav">
      <view @click="go('/pages/admin/users')">用户管理</view>
      <view @click="go('/pages/admin/experts')">专家服务</view>
      <view class="active">社区管理</view>
    </view>

    <view class="main-tabs">
      <view :class="{ active: tab === 'topics' }" @click="changeTab('topics')">投票主题</view>
      <view :class="{ active: tab === 'reports' }" @click="changeTab('reports')">举报处理</view>
    </view>

    <template v-if="tab === 'topics'">
      <view class="filter-row">
        <view v-for="item in topicFilters" :key="item.value" :class="{ active: topicStatus === item.value }" @click="changeTopicStatus(item.value)">{{ item.label }}</view>
      </view>
      <view v-if="loading" class="state-card">正在加载投票主题…</view>
      <view v-else-if="!topics.length" class="state-card">当前分类没有投票主题</view>
      <view v-for="topic in topics" :key="topic.id" class="topic-card" :class="{ hidden: topic.status === 'hidden' }">
        <view class="card-head">
          <view class="head-main"><view class="topic-title">{{ topic.title }}</view><view class="meta">{{ topic.author_name }} · {{ formatDate(topic.created_at) }} · ID {{ topic.id }}</view></view>
          <view class="badges"><text v-if="topic.is_featured" class="badge featured">精选</text><text class="badge" :class="topic.status">{{ statusText(topic.status) }}</text></view>
        </view>
        <view class="description">{{ topic.description }}</view>
        <view class="stats"><text>{{ topic.vote_count }} 票</text><text>{{ topic.candidates.length }} 个候选</text><text>{{ topic.comments.length }} 条评论</text><text>{{ topic.report_count }} 次主题举报</text></view>
        <view class="actions">
          <button v-if="topic.status !== 'hidden'" class="small-btn feature" @click="openFeatured(topic)">{{ topic.is_featured ? '取消精选' : '设为精选' }}</button>
          <button v-if="topic.status !== 'hidden'" class="small-btn hide" @click="openModerate('topic', topic, 'hide')">隐藏主题</button>
          <button v-else class="small-btn restore" @click="openModerate('topic', topic, 'restore')">恢复主题</button>
        </view>

        <view class="subsection">
          <view class="sub-title">候选名</view>
          <view v-for="candidate in topic.candidates" :key="candidate.id" class="content-row" :class="{ muted: candidate.status === 'hidden' }">
            <view class="content-main"><view><text class="content-name">{{ candidate.name }}</text><text class="mini-status">{{ candidate.status === 'hidden' ? '已隐藏' : candidate.vote_count + ' 票' }}</text></view><view class="content-desc">{{ candidate.meaning }}</view><view class="content-author">{{ candidate.author_name }} · ID {{ candidate.id }}</view></view>
            <button v-if="candidate.status !== 'hidden'" class="row-btn hide" @click="openModerate('candidate', candidate, 'hide')">隐藏</button>
            <button v-else class="row-btn restore" @click="openModerate('candidate', candidate, 'restore')">恢复</button>
          </view>
        </view>

        <view class="subsection">
          <view class="sub-title">评论</view>
          <view v-if="!topic.comments.length" class="sub-empty">暂无评论</view>
          <view v-for="comment in topic.comments" :key="comment.id" class="content-row" :class="{ muted: comment.status === 'hidden' }">
            <view class="content-main"><view class="comment-text">{{ comment.content }}</view><view class="content-author">{{ comment.author_name }} · ID {{ comment.id }} · {{ comment.status === 'hidden' ? '已隐藏' : '正常' }}</view></view>
            <button v-if="comment.status !== 'hidden'" class="row-btn hide" @click="openModerate('comment', comment, 'hide')">隐藏</button>
            <button v-else class="row-btn restore" @click="openModerate('comment', comment, 'restore')">恢复</button>
          </view>
        </view>
      </view>
    </template>

    <template v-if="tab === 'reports'">
      <view class="filter-row two"><view :class="{ active: reportStatus === 'pending' }" @click="changeReportStatus('pending')">待处理</view><view :class="{ active: reportStatus === 'resolved' }" @click="changeReportStatus('resolved')">已处理</view></view>
      <view v-if="loading" class="state-card">正在加载举报记录…</view>
      <view v-else-if="!reports.length" class="state-card">当前没有举报记录</view>
      <view v-for="report in reports" :key="report.id" class="report-card">
        <view class="card-head"><view><view class="report-title">{{ targetTypeText(report.target_type) }}举报</view><view class="meta">举报人 {{ report.reporter_name }} · {{ formatDate(report.created_at) }}</view></view><view class="badge" :class="report.status">{{ report.status === 'pending' ? '待处理' : '已处理' }}</view></view>
        <view class="target-box"><view class="target-label">被举报内容 · {{ targetStatusText(report.target_status) }}</view><view>{{ report.target_summary }}</view></view>
        <view class="reason">原因：{{ reasonText(report.reason) }}<text v-if="report.detail"> · {{ report.detail }}</text></view>
        <view v-if="report.resolution" class="resolution">处理结果：{{ report.resolution }}</view>
        <view v-if="report.status === 'pending'" class="actions"><button class="small-btn dismiss" @click="openReport(report, 'dismiss')">忽略举报</button><button class="small-btn hide" @click="openReport(report, 'hide')">隐藏并处理</button></view>
      </view>
    </template>

    <view v-if="actionVisible" class="modal-mask" @click.self="closeAction">
      <view class="action-sheet">
        <view class="sheet-title">{{ actionTitle }}</view>
        <view class="impact">{{ actionImpact }}</view>
        <textarea v-if="actionKind === 'report'" v-model.trim="resolution" class="resolution-input" maxlength="500" placeholder="处理说明（选填，最多500字）" />
        <view class="sheet-actions"><button class="cancel-btn" @click="closeAction">取消</button><button class="confirm-btn" :class="{ danger: actionIsHide }" :loading="submitting" :disabled="submitting" @click="confirmAction">{{ actionConfirmText }}</button></view>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../api'
import { getUser } from '../../utils/auth'

export default {
  data() {
    return {
      tab: 'topics', topicStatus: 'all', reportStatus: 'pending',
      topicFilters: [{ label: '全部', value: 'all' }, { label: '正常', value: 'open' }, { label: '已隐藏', value: 'hidden' }],
      topics: [], reports: [], total: 0, loading: false, submitting: false,
      actionVisible: false, actionKind: '', action: '', targetType: '', selected: null, resolution: ''
    }
  },
  computed: {
    actionIsHide() { return this.action === 'hide' },
    actionTitle() {
      if (this.actionKind === 'featured') return this.selected && this.selected.is_featured ? '取消社区精选' : '设为社区精选'
      if (this.actionKind === 'report') return this.action === 'hide' ? '隐藏内容并处理举报' : '忽略举报'
      return `${this.action === 'hide' ? '隐藏' : '恢复'}${this.targetTypeText(this.targetType)}`
    },
    actionImpact() {
      if (!this.selected) return ''
      if (this.actionKind === 'featured') return this.selected.is_featured ? `投票“${this.selected.title}”将从精选列表移除，普通社区列表仍可见。` : `投票“${this.selected.title}”将展示在社区精选列表。`
      if (this.actionKind === 'report') return this.action === 'hide' ? `准确动作：隐藏被举报的${this.targetTypeText(this.selected.target_type)}（ID ${this.selected.target_id}），同时将举报标记为已处理。原始数据保留，可在主题管理中恢复。` : `举报将标记为已处理，被举报内容保持当前状态。`
      const label = this.selected.title || this.selected.name || this.selected.content
      return this.action === 'hide' ? `准确动作：隐藏${this.targetTypeText(this.targetType)}“${String(label).slice(0, 40)}”（ID ${this.selected.id}）。用户端将不可见，原始数据保留。` : `准确动作：恢复${this.targetTypeText(this.targetType)}（ID ${this.selected.id}），用户端将重新可见。`
    },
    actionConfirmText() {
      if (this.actionKind === 'featured') return this.selected && this.selected.is_featured ? '确认取消精选' : '确认设为精选'
      if (this.actionKind === 'report') return this.action === 'hide' ? '确认隐藏并处理' : '确认忽略'
      return this.action === 'hide' ? '确认隐藏' : '确认恢复'
    }
  },
  onLoad() {
    const user = getUser()
    if (!user || user.role !== 'admin') { uni.showModal({ title: '无权访问', content: '该页面仅限管理员使用。', showCancel: false, success: () => uni.navigateBack() }); return }
    this.loadTopics()
  },
  methods: {
    go(url) { uni.redirectTo({ url }) },
    changeTab(value) { if (this.tab === value) return; this.tab = value; if (value === 'topics') this.loadTopics(); else this.loadReports() },
    changeTopicStatus(value) { if (this.topicStatus === value) return; this.topicStatus = value; this.loadTopics() },
    changeReportStatus(value) { if (this.reportStatus === value) return; this.reportStatus = value; this.loadReports() },
    async loadTopics() { this.loading = true; try { const data = await api.getAdminCommunityTopics({ status: this.topicStatus }); this.topics = data.items; this.total = data.total } catch (error) { uni.showToast({ title: error.message, icon: 'none', duration: 3000 }) } finally { this.loading = false } },
    async loadReports() { this.loading = true; try { this.reports = await api.getAdminCommunityReports(this.reportStatus) } catch (error) { uni.showToast({ title: error.message, icon: 'none', duration: 3000 }) } finally { this.loading = false } },
    openFeatured(topic) { this.actionKind = 'featured'; this.action = topic.is_featured ? 'unfeature' : 'feature'; this.selected = topic; this.actionVisible = true },
    openModerate(type, item, action) { this.actionKind = 'moderate'; this.targetType = type; this.action = action; this.selected = item; this.actionVisible = true },
    openReport(report, action) { this.actionKind = 'report'; this.targetType = report.target_type; this.action = action; this.selected = report; this.resolution = ''; this.actionVisible = true },
    closeAction() { if (this.submitting) return; this.actionVisible = false; this.selected = null; this.actionKind = ''; this.action = ''; this.resolution = '' },
    async confirmAction() {
      this.submitting = true
      try {
        let result
        if (this.actionKind === 'featured') result = await api.setCommunityFeatured(this.selected.id, !this.selected.is_featured)
        if (this.actionKind === 'moderate') result = await api.moderateCommunityContent({ target_type: this.targetType, target_id: this.selected.id, action: this.action })
        if (this.actionKind === 'report') result = await api.resolveCommunityReport(this.selected.id, { action: this.action, resolution: this.resolution || null })
        uni.showToast({ title: result.message, icon: 'success' }); this.actionVisible = false
        if (this.tab === 'topics') await this.loadTopics(); else await this.loadReports()
      } catch (error) { uni.showToast({ title: error.message, icon: 'none', duration: 3000 }) }
      finally { this.submitting = false }
    },
    statusText(value) { return { open: '正常', closed: '已结束', hidden: '已隐藏' }[value] || value },
    targetTypeText(value) { return { topic: '投票主题', candidate: '候选名', comment: '评论' }[value] || value },
    targetStatusText(value) { return { open: '正常', visible: '正常', hidden: '已隐藏', missing: '已不存在' }[value] || value },
    reasonText(value) { return { spam: '垃圾广告', abuse: '攻击辱骂', privacy: '泄露隐私', illegal: '违法内容', other: '其他问题' }[value] || value },
    formatDate(value) { return value ? String(value).replace('T', ' ').slice(0, 16) : '—' }
  }
}
</script>

<style scoped>
.admin-community-page{min-height:100vh;padding:28rpx 28rpx 70rpx;background:#f3f5f9}.admin-hero{display:flex;align-items:center;justify-content:space-between;padding:34rpx 32rpx;color:#fff;background:linear-gradient(135deg,#171d2d,#373c55);border-radius:29rpx;box-shadow:0 18rpx 40rpx rgba(23,29,45,.2)}.eyebrow{color:#f2d586;font-size:17rpx;font-weight:800;letter-spacing:4rpx}.hero-title{margin-top:12rpx;font-size:39rpx;font-weight:850}.hero-desc{margin-top:10rpx;color:#c6cbd7;font-size:21rpx}.hero-count{display:flex;align-items:center;justify-content:center;min-width:82rpx;height:82rpx;color:#f2d586;background:rgba(255,255,255,.1);border-radius:22rpx;font-size:34rpx;font-weight:850}.console-nav,.main-tabs,.filter-row{display:flex;gap:12rpx}.console-nav{margin-top:20rpx;padding:8rpx;background:#e7e9ee;border-radius:18rpx}.console-nav view{flex:1;padding:15rpx 0;color:#70798c;border-radius:13rpx;font-size:21rpx;text-align:center}.console-nav view.active{color:#fff;background:#30364d;font-weight:750}.main-tabs{margin-top:22rpx}.main-tabs view{flex:1;padding:21rpx;color:#747e91;background:#fff;border-radius:19rpx;font-size:25rpx;font-weight:750;text-align:center}.main-tabs view.active{color:#fff;background:#6257e8}.filter-row{margin-top:18rpx;padding:8rpx;background:#e6e8ed;border-radius:17rpx}.filter-row view{flex:1;padding:13rpx 0;color:#7b8496;border-radius:12rpx;font-size:20rpx;text-align:center}.filter-row view.active{color:#363c50;background:#fff;font-weight:750}.state-card{margin-top:20rpx;padding:55rpx;color:#9099aa;background:#fff;border-radius:24rpx;text-align:center}.topic-card,.report-card{margin-top:20rpx;padding:26rpx;background:#fff;border-radius:25rpx;box-shadow:0 11rpx 32rpx rgba(36,55,86,.055)}.topic-card.hidden{border:2rpx dashed #d7a0aa}.card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:15rpx}.head-main{flex:1;min-width:0}.topic-title,.report-title{font-size:28rpx;font-weight:820}.meta{margin-top:6rpx;color:#929aaa;font-size:18rpx}.badges{display:flex;gap:7rpx}.badge{padding:7rpx 12rpx;color:#18764c;background:#e7f7ef;border-radius:999rpx;font-size:17rpx}.badge.featured{color:#91601a;background:#fff2d4}.badge.hidden{color:#b23f55;background:#fff0f3}.badge.pending{color:#96601a;background:#fff2d8}.badge.resolved{color:#596478;background:#edf0f4}.description{margin-top:17rpx;color:#626d81;font-size:22rpx;line-height:1.65}.stats{display:flex;flex-wrap:wrap;gap:10rpx 22rpx;margin-top:16rpx;padding:15rpx;color:#778196;background:#f6f7fa;border-radius:14rpx;font-size:19rpx}.actions{display:flex;gap:12rpx;margin-top:18rpx}.small-btn{flex:1;height:64rpx;margin:0;border-radius:15rpx;font-size:20rpx;line-height:64rpx}.small-btn.feature{color:#825818;background:#fff2d4}.small-btn.hide,.row-btn.hide{color:#b33e55;background:#fff0f3}.small-btn.restore,.row-btn.restore{color:#18764c;background:#e7f7ef}.small-btn.dismiss{color:#596478;background:#edf0f4}.subsection{margin-top:22rpx;padding-top:18rpx;border-top:1rpx solid #eceef2}.sub-title{font-size:23rpx;font-weight:800}.content-row{display:flex;align-items:center;gap:14rpx;margin-top:12rpx;padding:16rpx;background:#f7f8fa;border-radius:16rpx}.content-row.muted{opacity:.65;background:#fff4f5}.content-main{flex:1;min-width:0}.content-name{font-size:23rpx;font-weight:780}.mini-status{margin-left:10rpx;color:#7467d5;font-size:17rpx}.content-desc,.comment-text{margin-top:5rpx;color:#667185;font-size:20rpx;line-height:1.5}.content-author{margin-top:5rpx;color:#9aa2b0;font-size:17rpx}.row-btn{width:92rpx;height:58rpx;margin:0;border-radius:14rpx;font-size:19rpx;line-height:58rpx}.sub-empty{margin-top:12rpx;color:#9ca3b1;font-size:19rpx}.target-box{margin-top:18rpx;padding:18rpx;color:#4e596e;background:#f5f6f9;border-radius:16rpx;font-size:22rpx;line-height:1.55}.target-label{margin-bottom:6rpx;color:#8c95a6;font-size:18rpx}.reason,.resolution{margin-top:14rpx;color:#697489;font-size:21rpx}.resolution{padding:14rpx;color:#52705f;background:#eef8f3;border-radius:13rpx}.modal-mask{position:fixed;z-index:99;inset:0;display:flex;align-items:flex-end;padding:30rpx;background:rgba(16,21,34,.58)}.action-sheet{width:100%;padding:31rpx;background:#fff;border-radius:30rpx}.sheet-title{font-size:32rpx;font-weight:850}.impact{margin-top:18rpx;color:#657086;font-size:22rpx;line-height:1.65}.resolution-input{width:100%;height:145rpx;margin-top:18rpx;padding:18rpx;background:#f4f5f8;border-radius:16rpx;font-size:22rpx}.sheet-actions{display:flex;gap:14rpx;margin-top:23rpx}.sheet-actions button{flex:1;height:74rpx;margin:0;border-radius:17rpx;font-size:23rpx;line-height:74rpx}.cancel-btn{color:#687286;background:#edf0f4}.confirm-btn{color:#fff;background:#6257e8}.confirm-btn.danger{background:#d94a64}
</style>
