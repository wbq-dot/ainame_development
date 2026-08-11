<template>
  <view class="community-page page-shell">
    <view class="hero">
      <view class="hero-kicker">COMMUNITY NAMING</view>
      <view class="page-title">让好名字被大家看见</view>
      <view class="page-subtitle">发起命名投票，听听真实用户的选择，也可以为别人的灵感投上一票。</view>
      <button class="publish-btn" @click="openPublish">发布命名投票</button>
    </view>

    <view class="filter-row">
      <view v-for="item in filters" :key="item.value" class="filter" :class="{ active: sort === item.value }" @click="changeSort(item.value)">{{ item.label }}</view>
    </view>

    <view v-if="loading" class="state">正在加载社区灵感…</view>
    <view v-else-if="!topics.length" class="state empty">这里还没有投票，来发布第一个吧。</view>

    <view v-for="topic in topics" :key="topic.id" class="topic-card">
      <view class="topic-meta">
        <view class="author-row">
          <view class="avatar">{{ topic.author_name.slice(0, 1) }}</view>
          <view><view class="author">{{ topic.author_name }}</view><view class="time">{{ formatDate(topic.created_at) }}</view></view>
        </view>
        <view v-if="topic.is_featured" class="featured">社区精选</view>
      </view>
      <view class="topic-title">{{ topic.title }}</view>
      <view class="topic-desc">{{ topic.description }}</view>

      <view class="candidate-list">
        <view v-for="candidate in topic.candidates" :key="candidate.id" class="candidate" :class="{ voted: candidate.voted }" @click="vote(topic, candidate)">
          <view class="candidate-top">
            <view><text class="candidate-name">{{ candidate.name }}</text><text v-if="candidate.voted" class="my-vote">已投</text></view>
            <text class="vote-count">{{ candidate.vote_count }} 票</text>
          </view>
          <view class="meaning">{{ candidate.meaning }}</view>
          <view class="progress"><view class="progress-value" :style="{ width: votePercent(topic, candidate) + '%' }"></view></view>
          <view class="candidate-foot"><text>由 {{ candidate.author_name }} 提名</text><text @click.stop="report('candidate', candidate.id)">举报</text></view>
        </view>
      </view>

      <view class="topic-actions">
        <text @click="openCandidate(topic)">＋ 提名候选</text>
        <text @click="toggleComments(topic)">评论 {{ topic.comment_count }}</text>
        <text @click="report('topic', topic.id)">举报</text>
      </view>

      <view v-if="expandedId === topic.id" class="comments-panel">
        <view v-if="commentsLoading" class="comment-state">评论加载中…</view>
        <view v-else-if="!comments.length" class="comment-state">还没有评论，说说你的看法吧。</view>
        <view v-for="comment in comments" :key="comment.id" class="comment-item">
          <view class="comment-head"><text>{{ comment.author_name }}</text><text class="comment-report" @click="report('comment', comment.id)">举报</text></view>
          <view class="comment-content">{{ comment.content }}</view>
        </view>
        <view class="comment-form">
          <input v-model.trim="commentText" class="comment-input" maxlength="500" placeholder="友善交流，分享你的判断" />
          <button class="send-btn" :disabled="submitting || !commentText" @click="submitComment(topic)">发送</button>
        </view>
      </view>
    </view>

    <view v-if="publishVisible" class="modal-mask" @click.self="closePublish">
      <scroll-view scroll-y class="sheet">
        <view class="sheet-title">发布命名投票</view>
        <view class="sheet-note">至少准备 2 个候选名，发布后其他用户也可以继续提名。</view>
        <view class="field"><text class="field-label">投票主题</text><input v-model.trim="publishForm.title" class="field-input" maxlength="80" placeholder="例如：为新茶饮品牌选一个名字" /></view>
        <view class="field"><text class="field-label">背景与要求</text><textarea v-model.trim="publishForm.description" class="field-textarea" maxlength="2000" placeholder="介绍使用场景、定位和你在意的方向" /></view>
        <view v-for="(candidate, index) in publishForm.candidates" :key="index" class="candidate-form">
          <view class="candidate-number">候选 {{ index + 1 }}</view>
          <input v-model.trim="candidate.name" class="field-input" maxlength="50" placeholder="候选名" />
          <textarea v-model.trim="candidate.meaning" class="field-textarea short" maxlength="500" placeholder="名字寓意或推荐理由" />
        </view>
        <button v-if="publishForm.candidates.length < 10" class="ghost-btn btn-gap" @click="addPublishCandidate">＋ 再加一个候选</button>
        <view class="sheet-actions"><button class="ghost-btn" @click="closePublish">取消</button><button class="primary-btn" :disabled="submitting" @click="submitTopic">确认发布</button></view>
      </scroll-view>
    </view>

    <view v-if="candidateVisible" class="modal-mask" @click.self="closeCandidate">
      <view class="sheet compact-sheet">
        <view class="sheet-title">提名一个好名字</view>
        <view class="sheet-note">你的提名会立即加入该主题，供社区用户投票。</view>
        <view class="field"><text class="field-label">候选名</text><input v-model.trim="candidateForm.name" class="field-input" maxlength="50" placeholder="输入候选名" /></view>
        <view class="field"><text class="field-label">推荐理由</text><textarea v-model.trim="candidateForm.meaning" class="field-textarea short" maxlength="500" placeholder="说说它为什么合适" /></view>
        <view class="sheet-actions"><button class="ghost-btn" @click="closeCandidate">取消</button><button class="primary-btn" :disabled="submitting" @click="submitCandidate">提交提名</button></view>
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
      filters: [{ label: '最新', value: 'latest' }, { label: '热门', value: 'popular' }, { label: '精选', value: 'featured' }],
      sort: 'latest', topics: [], loading: false, submitting: false,
      publishVisible: false, candidateVisible: false, selectedTopic: null,
      publishForm: { title: '', description: '', candidates: [{ name: '', meaning: '' }, { name: '', meaning: '' }] },
      candidateForm: { name: '', meaning: '' },
      expandedId: null, comments: [], commentsLoading: false, commentText: ''
    }
  },
  onShow() { this.loadTopics() },
  methods: {
    ensureLogin() {
      if (getAccessToken()) return true
      uni.showToast({ title: '登录后即可参与社区互动', icon: 'none' })
      setTimeout(() => uni.navigateTo({ url: '/pages/auth/login' }), 500)
      return false
    },
    async loadTopics() {
      this.loading = true
      try {
        const data = await api.getCommunityTopics({ sort: this.sort })
        this.topics = data.items
      } catch (error) { uni.showToast({ title: error.message, icon: 'none' }) }
      finally { this.loading = false }
    },
    changeSort(value) { if (this.sort !== value) { this.sort = value; this.loadTopics() } },
    votePercent(topic, candidate) { return topic.vote_count ? Math.round(candidate.vote_count / topic.vote_count * 100) : 0 },
    replaceTopic(updated) { const index = this.topics.findIndex((item) => item.id === updated.id); if (index >= 0) this.topics.splice(index, 1, updated) },
    async vote(topic, candidate) {
      if (!this.ensureLogin() || this.submitting) return
      this.submitting = true
      try { this.replaceTopic(await api.voteCommunityCandidate(topic.id, candidate.id)); uni.showToast({ title: '投票成功', icon: 'success' }) }
      catch (error) { uni.showToast({ title: error.message, icon: 'none' }) }
      finally { this.submitting = false }
    },
    openPublish() { if (this.ensureLogin()) this.publishVisible = true },
    closePublish() { if (!this.submitting) this.publishVisible = false },
    addPublishCandidate() { this.publishForm.candidates.push({ name: '', meaning: '' }) },
    async submitTopic() {
      const data = { ...this.publishForm, candidates: this.publishForm.candidates.filter((item) => item.name && item.meaning) }
      if (data.title.length < 4 || data.description.length < 10 || data.candidates.length < 2) { uni.showToast({ title: '请填写主题、背景和至少 2 个候选名', icon: 'none' }); return }
      this.submitting = true
      try { const topic = await api.createCommunityTopic(data); this.publishVisible = false; this.publishForm = { title: '', description: '', candidates: [{ name: '', meaning: '' }, { name: '', meaning: '' }] }; this.sort = 'latest'; this.topics.unshift(topic); uni.showToast({ title: '发布成功', icon: 'success' }) }
      catch (error) { uni.showToast({ title: error.message, icon: 'none' }) }
      finally { this.submitting = false }
    },
    openCandidate(topic) { if (this.ensureLogin()) { this.selectedTopic = topic; this.candidateVisible = true } },
    closeCandidate() { if (!this.submitting) this.candidateVisible = false },
    async submitCandidate() {
      if (!this.candidateForm.name || this.candidateForm.meaning.length < 2) { uni.showToast({ title: '请填写候选名和推荐理由', icon: 'none' }); return }
      this.submitting = true
      try { this.replaceTopic(await api.addCommunityCandidate(this.selectedTopic.id, this.candidateForm)); this.candidateVisible = false; this.candidateForm = { name: '', meaning: '' }; uni.showToast({ title: '提名成功', icon: 'success' }) }
      catch (error) { uni.showToast({ title: error.message, icon: 'none' }) }
      finally { this.submitting = false }
    },
    async toggleComments(topic) {
      if (this.expandedId === topic.id) { this.expandedId = null; return }
      this.expandedId = topic.id; this.comments = []; this.commentsLoading = true
      try { this.comments = await api.getCommunityComments(topic.id) }
      catch (error) { uni.showToast({ title: error.message, icon: 'none' }) }
      finally { this.commentsLoading = false }
    },
    async submitComment(topic) {
      if (!this.ensureLogin() || !this.commentText || this.submitting) return
      this.submitting = true
      try { this.comments.push(await api.addCommunityComment(topic.id, this.commentText)); this.commentText = ''; topic.comment_count += 1 }
      catch (error) { uni.showToast({ title: error.message, icon: 'none' }) }
      finally { this.submitting = false }
    },
    report(targetType, targetId) {
      if (!this.ensureLogin()) return
      const reasons = [{ label: '垃圾广告', value: 'spam' }, { label: '攻击辱骂', value: 'abuse' }, { label: '泄露隐私', value: 'privacy' }, { label: '违法内容', value: 'illegal' }, { label: '其他问题', value: 'other' }]
      uni.showActionSheet({ itemList: reasons.map((item) => item.label), success: async ({ tapIndex }) => { try { await api.reportCommunityContent({ target_type: targetType, target_id: targetId, reason: reasons[tapIndex].value }); uni.showToast({ title: '举报已提交', icon: 'success' }) } catch (error) { uni.showToast({ title: error.message, icon: 'none' }) } } })
    },
    formatDate(value) { const date = new Date(value); return `${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}` }
  }
}
</script>

<style scoped>
.community-page{background:radial-gradient(circle at 90% 0,#f0eaff 0,transparent 24%),#f5f7fb}.hero{padding:34rpx;color:#fff;background:linear-gradient(145deg,#332b70,#6b55df 65%,#9270ee);border-radius:34rpx;box-shadow:0 22rpx 50rpx rgba(73,57,177,.2)}.hero-kicker{color:#dcd6ff;font-size:18rpx;font-weight:800;letter-spacing:4rpx}.hero .page-title{margin-top:15rpx}.hero .page-subtitle{color:#e5e1ff}.publish-btn{width:260rpx;height:76rpx;margin:28rpx 0 0;color:#4a3b9b;background:#fff;border-radius:20rpx;font-size:25rpx;font-weight:750;line-height:76rpx}.filter-row{display:flex;gap:10rpx;margin-top:26rpx;padding:8rpx;background:#e9ecf2;border-radius:20rpx}.filter{flex:1;height:64rpx;color:#7d8595;border-radius:14rpx;font-size:22rpx;line-height:64rpx;text-align:center}.filter.active{color:#4e43b3;background:#fff;font-weight:750}.state{padding:90rpx 0;text-align:center;color:#8792a7}.topic-card{margin-top:22rpx;padding:28rpx;background:#fff;border-radius:28rpx;box-shadow:0 12rpx 38rpx rgba(36,55,86,.06)}.topic-meta,.author-row,.candidate-top,.topic-actions,.comment-head,.sheet-actions{display:flex;align-items:center}.topic-meta,.candidate-top,.comment-head{justify-content:space-between}.author-row{gap:13rpx}.avatar{display:flex;align-items:center;justify-content:center;width:58rpx;height:58rpx;color:#fff;background:linear-gradient(135deg,#7465e9,#a383ed);border-radius:18rpx;font-size:24rpx;font-weight:800}.author{font-size:23rpx;font-weight:750}.time{margin-top:3rpx;color:#a0a7b5;font-size:18rpx}.featured{padding:9rpx 15rpx;color:#97671d;background:#fff3d1;border-radius:999rpx;font-size:19rpx;font-weight:750}.topic-title{margin-top:25rpx;font-size:32rpx;font-weight:820}.topic-desc{margin-top:10rpx;color:#657086;font-size:23rpx;line-height:1.7}.candidate-list{margin-top:20rpx}.candidate{margin-top:13rpx;padding:20rpx;background:#f6f7fa;border:2rpx solid transparent;border-radius:20rpx}.candidate.voted{background:#f1efff;border-color:#8778ed}.candidate-name{font-size:27rpx;font-weight:800}.my-vote{margin-left:12rpx;padding:5rpx 10rpx;color:#fff;background:#7163e7;border-radius:999rpx;font-size:16rpx}.vote-count{color:#584bc7;font-size:22rpx;font-weight:750}.meaning{margin-top:8rpx;color:#6f798c;font-size:21rpx;line-height:1.55}.progress{overflow:hidden;height:8rpx;margin-top:15rpx;background:#e4e6ec;border-radius:999rpx}.progress-value{height:100%;background:linear-gradient(90deg,#7869e9,#a28af1);border-radius:999rpx}.candidate-foot{display:flex;justify-content:space-between;margin-top:10rpx;color:#a0a7b5;font-size:18rpx}.topic-actions{gap:32rpx;margin-top:23rpx;padding-top:20rpx;border-top:1rpx solid #eef0f4;color:#6155c7;font-size:21rpx;font-weight:650}.comments-panel{margin-top:20rpx;padding:19rpx;background:#f7f8fb;border-radius:19rpx}.comment-state{padding:18rpx;color:#9299a8;text-align:center;font-size:20rpx}.comment-item{padding:14rpx 4rpx;border-bottom:1rpx solid #e9ebf0}.comment-head{font-size:20rpx;font-weight:750}.comment-report{color:#a0a7b5;font-weight:400}.comment-content{margin-top:7rpx;color:#5f697d;font-size:21rpx;line-height:1.55}.comment-form{display:flex;gap:10rpx;margin-top:17rpx}.comment-input{flex:1;height:68rpx;padding:0 19rpx;background:#fff;border-radius:15rpx;font-size:21rpx}.send-btn{width:118rpx;height:68rpx;margin:0;color:#fff;background:#6658d8;border-radius:15rpx;font-size:21rpx;line-height:68rpx}.modal-mask{position:fixed;z-index:99;inset:0;display:flex;align-items:flex-end;padding:26rpx;background:rgba(15,20,35,.55)}.sheet{width:100%;max-height:88vh;padding:31rpx;background:#fff;border-radius:31rpx}.compact-sheet{max-height:none}.sheet-title{font-size:32rpx;font-weight:850}.sheet-note{margin-top:8rpx;color:#8792a7;font-size:21rpx;line-height:1.55}.candidate-form{margin-top:23rpx;padding:18rpx;background:#f7f8fb;border-radius:19rpx}.candidate-number{margin-bottom:12rpx;color:#5e52c7;font-size:21rpx;font-weight:750}.candidate-form .field-input{background:#fff}.field-textarea.short{min-height:130rpx}.candidate-form .field-textarea{margin-top:12rpx;background:#fff}.sheet-actions{gap:14rpx;margin-top:27rpx}.sheet-actions button{flex:1;margin:0}.safe-bottom{height:40rpx}
</style>
