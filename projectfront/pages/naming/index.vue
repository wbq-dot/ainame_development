<template>
  <view class="page-shell naming-page">
    <view class="naming-center-head"><view><view class="center-eyebrow">NAMING CENTER</view><view class="center-title">起名</view><view class="center-desc">AI 灵感、真人专家与专属资料库，都在一个页面。</view></view></view>
    <view class="service-switch">
      <view class="service-item active"><view class="service-icon">AI</view><view><view class="service-name">AI 起名</view><view class="service-desc">立即生成候选名字</view></view></view>
      <view class="service-item" @click="openExpertNaming"><view class="service-icon expert">专</view><view><view class="service-name">专家起名</view><view class="service-desc">三档真人专家接单</view></view></view>
      <view class="service-item" @click="openKnowledge"><view class="service-icon knowledge">库</view><view><view class="service-name">专属知识库</view><view class="service-desc">上传自己的参考资料</view></view></view>
    </view>
    <view class="title-row">
      <view>
        <view class="page-title">AI 起名</view>
        <view class="page-subtitle">选择类型，告诉我你的期待。</view>
      </view>
      <view class="balance-pill" @click="loadBalance">
        <text class="balance-number">{{ loggedIn ? balance : '—' }}</text>
        <text>次可用</text>
      </view>
    </view>

    <view v-if="!loggedIn" class="card login-callout">
      <view class="callout-icon">钥</view>
      <view class="card-title">登录后开始起名</view>
      <view class="card-note">AI 起名与反馈会消耗账户次数。</view>
      <button class="primary-btn btn-gap" @click="goLogin">登录 / 注册</button>
    </view>

    <template v-else>
      <view class="card form-card">
        <view class="field first-field">
          <text class="field-label">起名类型</text>
          <view class="type-tabs">
            <view v-for="item in categories" :key="item.value" class="type-tab" :class="{ active: form.category === item.value }" @click="form.category = item.value">
              <view class="type-icon-wrap"><text class="type-icon">{{ item.icon }}</text></view>
              <text class="type-label">{{ item.label }}</text>
            </view>
          </view>
        </view>

        <template v-if="form.category === '人名'">
          <view class="field">
            <text class="field-label">姓氏（必填）</text>
            <input v-model.trim="form.surname" class="field-input" maxlength="10" placeholder="例如：林" />
          </view>
          <view class="field">
            <text class="field-label">性别倾向</text>
            <view class="chips">
              <view v-for="item in genders" :key="item" class="chip" :class="{ active: form.gender === item }" @click="form.gender = item">{{ item }}</view>
            </view>
          </view>
        </template>

        <view class="field">
          <text class="field-label">名字长度</text>
          <view class="chips">
            <view v-for="item in lengths" :key="item" class="chip" :class="{ active: form.length === item }" @click="form.length = item">{{ item }}</view>
          </view>
        </view>

        <view class="field">
          <text class="field-label">具体要求</text>
          <textarea v-model.trim="form.other" class="field-textarea" maxlength="500" :placeholder="requirementPlaceholder" />
          <view class="counter">{{ form.other.length }}/500</view>
        </view>

        <view class="field">
          <text class="field-label">避开的字（选填）</text>
          <input v-model.trim="excludeText" class="field-input" placeholder="多个字请用逗号或顿号分隔" />
        </view>

        <button class="primary-btn btn-gap" :loading="generating" :disabled="generating || balance <= 0" @click="generate">
          {{ generating ? '正在构思，请稍候…' : balance > 0 ? '生成5个好名字' : '次数不足，请先购买' }}
        </button>
      </view>

      <view v-if="results.length" class="result-section">
        <view class="section-head">
          <view>
            <view class="section-title">本轮候选</view>
            <view class="thread-id">会话 {{ threadId }}</view>
          </view>
          <view class="result-actions">
            <view class="round-badge">{{ results.length }} 个</view>
            <view class="copy-all-btn" @click="copyAllNames">复制全部</view>
          </view>
        </view>

        <view v-for="(item, index) in results" :key="`${item.name}-${index}`" class="name-card">
          <view class="name-head">
            <view class="name-title-wrap">
              <view class="rank">{{ String(index + 1).padStart(2, '0') }}</view>
              <view class="name-text">{{ item.name }}</view>
            </view>
            <view class="copy-name-btn" @click="copyName(item.name)">复制名字</view>
          </view>
          <view class="info-block">
            <text class="info-label">出处</text>
            <text class="info-value">{{ item.reference }}</text>
          </view>
          <view class="info-block">
            <text class="info-label">寓意</text>
            <text class="info-value">{{ item.moral }}</text>
          </view>
          <view v-if="form.category === '企业名'" class="domain-row">
            <text class="domain-name">{{ item.domain }}</text>
            <text class="domain-status">{{ item.domain_status }}</text>
          </view>
        </view>

        <view class="card feedback-card">
          <view class="card-title">继续调整这组名字</view>
          <view class="card-note">说出喜欢或不满意的部分，后端会沿用本次会话继续生成。</view>
          <view class="feedback-label">调整意见</view>
          <textarea v-model="feedback" class="field-textarea feedback-input" maxlength="500" placeholder="请在这里输入，例如：保留第一个名字，其余名字希望更简洁现代" />
          <view class="feedback-status" :class="{ ready: canSubmitFeedback }">
            {{ canSubmitFeedback ? `已输入 ${feedback.trim().length} 个字，可以提交` : '请先在输入框中填写真实的调整意见' }}
          </view>
          <button class="secondary-btn btn-gap" :loading="feedbackLoading" :disabled="feedbackLoading || !canSubmitFeedback" @click="submitFeedback">按意见重新生成</button>
        </view>
      </view>
    </template>
  </view>
</template>

<script>
import { api } from '../../api'
import { getAccessToken } from '../../utils/auth'
import { saveNamingHistory } from '../../utils/history'

export default {
  data() {
    return {
      loggedIn: false,
      balance: 0,
      generating: false,
      feedbackLoading: false,
      threadId: '',
      feedback: '',
      results: [],
      excludeText: '',
      categories: [
        { value: '人名', label: '人名', icon: '👤' },
        { value: '企业名', label: '企业', icon: '🏢' },
        { value: '宠物名', label: '宠物', icon: '🐾' }
      ],
      genders: ['不限', '男', '女'],
      lengths: ['不限', '一字', '两字', '三字', '四字'],
      form: {
        category: '人名',
        surname: '',
        gender: '不限',
        length: '不限',
        other: ''
      }
    }
  },
  computed: {
    canSubmitFeedback() {
      return Boolean(this.feedback.trim())
    },
    requirementPlaceholder() {
      return {
        '人名': '例如：希望温润大方，有山水意象，参考诗经楚辞',
        '企业名': '例如：芯片科技公司，名字现代、可靠、便于传播',
        '宠物名': '例如：一只活泼的白色小猫，名字可爱好记'
      }[this.form.category]
    }
  },
  onShow() {
    this.loggedIn = Boolean(getAccessToken())
    if (this.loggedIn) this.loadBalance()
  },
  methods: {
    openExpertNaming() { uni.navigateTo({ url: '/pages/expert/index' }) },
    openKnowledge() { uni.navigateTo({ url: '/pages/knowledge/index' }) },
    goLogin() { uni.navigateTo({ url: '/pages/auth/login' }) },
    async loadBalance() {
      try {
        const data = await api.getBalance()
        this.balance = data.name_balance ?? data.balance ?? 0
      } catch (error) {
        this.loggedIn = false
        uni.showToast({ title: error.message, icon: 'none' })
      }
    },
    payload() {
      return {
        ...this.form,
        surname: this.form.category === '人名' ? this.form.surname : '',
        gender: this.form.category === '人名' ? this.form.gender : '不限',
        other: this.form.other || '',
        exclude: this.excludeText.split(/[，,、\s]+/).map((item) => item.trim()).filter(Boolean)
      }
    },
    async generate() {
      if (this.form.category === '人名' && !this.form.surname) {
        uni.showToast({ title: '生成人名时必须填写姓氏', icon: 'none' })
        return
      }
      this.generating = true
      try {
        const data = await api.generateNames(this.payload())
        this.threadId = data.thread_id
        this.results = data.names || []
        this.feedback = ''
        this.saveCurrentHistory()
        await this.loadBalance()
        uni.pageScrollTo({ selector: '.result-section', duration: 350 })
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 3200 })
      } finally {
        this.generating = false
      }
    },
    async submitFeedback() {
      const feedback = this.feedback.trim()
      if (!feedback) {
        uni.showToast({ title: '请先输入调整意见', icon: 'none' })
        return
      }
      this.feedbackLoading = true
      try {
        const data = await api.feedbackNames({
          thread_id: this.threadId,
          category: this.form.category,
          feedback
        })
        this.results = data.names || []
        this.feedback = ''
        this.saveCurrentHistory()
        await this.loadBalance()
        uni.showToast({ title: '已按意见更新', icon: 'success' })
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 3200 })
      } finally {
        this.feedbackLoading = false
      }
    },
    saveCurrentHistory() {
      if (!this.threadId || !this.results.length) return
      saveNamingHistory({
        threadId: this.threadId,
        category: this.form.category,
        requirement: this.form.other,
        names: this.results
      })
    },
    copyName(name) {
      this.copyText(name, '名字已复制')
    },
    copyAllNames() {
      const content = this.results.map((item, index) => `${index + 1}. ${item.name}`).join('\n')
      this.copyText(content, '全部名字已复制')
    },
    copyText(content, successTitle) {
      uni.setClipboardData({
        data: content,
        success: () => uni.showToast({ title: successTitle, icon: 'success' }),
        fail: () => uni.showToast({ title: '复制失败，请长按名字复制', icon: 'none' })
      })
    }
  }
}
</script>

<style scoped>
.naming-center-head{padding:31rpx 32rpx;color:#fff;background:linear-gradient(135deg,#252350,#6451d6);border-radius:30rpx}.center-eyebrow{color:#d9d3ff;font-size:16rpx;font-weight:800;letter-spacing:4rpx}.center-title{margin-top:8rpx;font-size:39rpx;font-weight:900}.center-desc{margin-top:6rpx;color:#dfdcf8;font-size:20rpx}.service-switch{display:grid;grid-template-columns:repeat(3,1fr);gap:12rpx;margin-top:17rpx}.service-item{min-height:118rpx;padding:17rpx;background:#fff;border:2rpx solid transparent;border-radius:20rpx}.service-item.active{border-color:#bdb5ff;background:#f4f2ff}.service-icon{display:flex;align-items:center;justify-content:center;width:45rpx;height:45rpx;color:#fff;background:#6257e8;border-radius:13rpx;font-size:16rpx;font-weight:850}.service-icon.expert{background:#30906c}.service-icon.knowledge{background:#bd7540}.service-name{margin-top:10rpx;font-size:21rpx;font-weight:820}.service-desc{margin-top:4rpx;color:#929aaa;font-size:16rpx;line-height:1.35}.title-row{margin-top:30rpx}
.naming-page { background: radial-gradient(circle at 100% 0, #e9e5ff 0, transparent 25%), #f5f7fb; }
.title-row { display: flex; align-items: center; justify-content: space-between; }
.balance-pill { display: flex; flex-direction: column; align-items: center; min-width: 118rpx; padding: 15rpx 20rpx; color: #6f63d8; background: #ebe9ff; border-radius: 21rpx; font-size: 20rpx; }
.balance-number { font-size: 34rpx; font-weight: 850; line-height: 1.1; }
.login-callout { padding: 50rpx 34rpx; text-align: center; }
.callout-icon { display: flex; align-items: center; justify-content: center; width: 90rpx; height: 90rpx; margin: 0 auto 24rpx; color: #6257e8; background: #ebe9ff; border-radius: 26rpx; font-size: 36rpx; font-weight: 800; }
.first-field { margin-top: 0; }
.type-tabs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14rpx; }
.type-tab { display: flex; align-items: center; justify-content: center; gap: 12rpx; height: 92rpx; color: #6f7788; background: #f2f4f8; border: 2rpx solid transparent; border-radius: 20rpx; font-size: 25rpx; font-weight: 650; }
.type-tab.active { color: #4d42be; background: #eeecff; border-color: #bdb5ff; }
.type-icon-wrap { display: flex; align-items: center; justify-content: center; width: 48rpx; height: 48rpx; background: #fff; border-radius: 15rpx; box-shadow: 0 5rpx 14rpx rgba(64, 56, 147, 0.08); }
.type-icon { font-size: 27rpx; line-height: 1; }
.type-label { white-space: nowrap; }
.type-tab.active .type-icon-wrap { background: #fff; box-shadow: 0 6rpx 16rpx rgba(77, 66, 190, 0.14); }
.counter { margin-top: 7rpx; color: #9aa2b1; font-size: 20rpx; text-align: right; }
.result-section { margin-top: 42rpx; }
.thread-id { max-width: 500rpx; margin-top: 7rpx; overflow: hidden; color: #9aa2b1; font-size: 19rpx; text-overflow: ellipsis; white-space: nowrap; }
.round-badge { padding: 10rpx 18rpx; color: #5a4fcb; background: #ebe9ff; border-radius: 999rpx; font-size: 22rpx; }
.result-actions { display: flex; align-items: center; gap: 12rpx; }
.copy-all-btn { padding: 10rpx 17rpx; color: #fff; background: #6257e8; border-radius: 999rpx; font-size: 20rpx; }
.name-card { margin-top: 20rpx; padding: 30rpx; background: #fff; border-left: 7rpx solid #7164e9; border-radius: 25rpx; box-shadow: 0 14rpx 38rpx rgba(36, 55, 86, 0.06); }
.name-head { display: flex; align-items: center; justify-content: space-between; gap: 18rpx; }
.name-title-wrap { display: flex; align-items: center; min-width: 0; gap: 18rpx; }
.rank { color: #aaa5dc; font-size: 20rpx; font-weight: 800; letter-spacing: 2rpx; }
.name-text { color: #252052; font-size: 39rpx; font-weight: 850; letter-spacing: 4rpx; }
.copy-name-btn { flex: 0 0 auto; padding: 10rpx 16rpx; color: #5a4fcb; background: #eeecff; border-radius: 999rpx; font-size: 20rpx; }
.info-block { display: flex; gap: 20rpx; margin-top: 22rpx; }
.info-label { flex: 0 0 58rpx; color: #8b95a9; font-size: 22rpx; }
.info-value { flex: 1; color: #4c576c; font-size: 24rpx; line-height: 1.65; }
.domain-row { display: flex; align-items: center; justify-content: space-between; margin-top: 22rpx; padding: 18rpx 20rpx; background: #f4f6fa; border-radius: 16rpx; }
.domain-name { color: #4b43a8; font-size: 23rpx; font-weight: 700; }
.domain-status { font-size: 21rpx; }
.feedback-card { margin-top: 26rpx; background: linear-gradient(145deg, #fff, #f2f0ff); }
.feedback-label { margin-top: 22rpx; color: #455066; font-size: 22rpx; font-weight: 700; }
.feedback-input { margin-top: 10rpx; background: #fff; border: 2rpx solid #e4e6ee; }
.feedback-input:focus { border-color: #9d93f4; }
.feedback-status { margin-top: 10rpx; color: #9aa2b1; font-size: 20rpx; }
.feedback-status.ready { color: #3e9b75; }
</style>
