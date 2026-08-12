<template>
  <view class="page-shell knowledge-page">
    <view class="knowledge-hero">
      <view class="hero-copy">
        <view class="hero-tag">PRIVATE KNOWLEDGE</view>
        <view class="hero-title">专属知识库</view>
        <view class="hero-desc">沉淀你的命名规则、家族文化、品牌偏好与宠物故事。</view>
      </view>
      <view class="books-art"><view class="book book-a"></view><view class="book book-b"></view><view class="book book-c"></view><view class="leaf leaf-a"></view><view class="leaf leaf-b"></view></view>
    </view>

    <view v-if="!loggedIn" class="card login-callout">
      <view class="login-icon">钥</view>
      <view class="card-title">登录后建立私人知识库</view>
      <view class="card-note">每个账号的数据独立保存，不会混入其他用户的检索结果。</view>
      <button class="primary-btn btn-gap" @click="goLogin">登录 / 注册</button>
    </view>

    <template v-else>
      <view class="coverage-card">
        <view class="coverage-title">分类存放，检索时只使用相关资料</view>
        <view class="coverage-grid">
          <view><text>通</text><view>通用</view></view>
          <view><text>人</text><view>人名</view></view>
          <view><text>企</text><view>企业名</view></view>
          <view><text>宠</text><view>宠物名</view></view>
        </view>
      </view>

      <view class="card upload-card">
        <view class="section-label">01 / 选择资料用途</view>
        <view class="type-grid">
          <view v-for="item in knowledgeTypes" :key="item.value" class="type-card" :class="{ active: knowledgeType === item.value }" @click="knowledgeType = item.value">
            <view class="type-icon">{{ item.icon }}</view>
            <view class="type-copy"><view>{{ item.label }}</view><text>{{ item.desc }}</text></view>
            <view class="type-check">{{ knowledgeType === item.value ? '✓' : '' }}</view>
          </view>
        </view>

        <view class="section-label file-section">02 / 选择资料文件</view>
        <view class="upload-zone" @click="chooseFile">
          <view class="upload-illustration"><view class="paper"></view><view class="upload-arrow">↑</view></view>
          <view v-if="selectedFile" class="selected-name">{{ selectedFile.name }}</view>
          <view v-else class="upload-title">点击选择 PDF 或 TXT</view>
          <view class="upload-note">单个文件最大 10MB，建议内容结构清晰</view>
        </view>

        <view class="tips-title">适合上传的内容</view>
        <view class="tip-chips"><text>命名规则</text><text>品牌手册</text><text>家族字辈</text><text>偏好与禁忌</text></view>
        <view class="notice"><text class="notice-mark">i</text><text>上传后由后台切分并建立检索索引；完成时间取决于文件大小。</text></view>
        <button class="primary-btn btn-gap" :loading="uploading" :disabled="uploading || !selectedFile" @click="confirmUpload">上传并构建知识库</button>
        <view v-if="uploadResult" class="success-panel">{{ uploadResult }}</view>
        <view v-if="taskId" class="task-panel"><text>任务 {{ taskId }}</text><b>{{ taskStatusText }}</b><button :loading="checkingTask" @click="checkTask">刷新进度</button><view v-if="taskError">{{ taskError }}</view></view>
      </view>
    </template>
  </view>
</template>

<script>
import { api } from '../../api'
import { getAccessToken, requireLogin } from '../../utils/auth'

export default {
  data() {
    return {
      loggedIn: false,
      selectedFile: null,
      uploading: false,
      uploadResult: '',
      taskId: '',
      taskStatus: '',
      taskError: '',
      checkingTask: false,
      knowledgeType: 'general',
      knowledgeTypes: [
        { value: 'general', label: '通用资料', icon: '通', desc: '三类起名都可使用' },
        { value: 'human', label: '人名资料', icon: '人', desc: '字辈、五行与避讳' },
        { value: 'company', label: '企业资料', icon: '企', desc: '品牌与行业规则' },
        { value: 'pet', label: '宠物资料', icon: '宠', desc: '宠物故事与偏好' }
      ]
    }
  },
  onShow() { this.loggedIn = Boolean(getAccessToken()) },
  methods: {
    goLogin() { uni.navigateTo({ url: '/pages/auth/login' }) },
    chooseFile() {
      // #ifdef H5
      uni.chooseFile({ count: 1, extension: ['.pdf', '.txt'], success: (res) => this.acceptFile(res.tempFiles[0], res.tempFilePaths[0]) })
      // #endif
      // #ifdef MP-WEIXIN
      uni.chooseMessageFile({ count: 1, type: 'file', extension: ['pdf', 'txt'], success: (res) => this.acceptFile(res.tempFiles[0], res.tempFiles[0].path) })
      // #endif
      // #ifdef APP-PLUS
      uni.showModal({ title: '当前测试方式不支持', content: '请先在 HBuilderX 的 H5 浏览器中测试文件上传。', showCancel: false })
      // #endif
    },
    acceptFile(file, path) {
      const name = file.name || path.split('/').pop()
      if (!/\.(pdf|txt)$/i.test(name)) { uni.showToast({ title: '只能选择 PDF 或 TXT 文件', icon: 'none' }); return }
      this.selectedFile = { name, path: file.path || path }
      this.uploadResult = ''
    },
    confirmUpload() {
      if (!requireLogin() || !this.selectedFile) return
      const type = this.knowledgeTypes.find((item) => item.value === this.knowledgeType)
      uni.showModal({
        title: '确认上传文件',
        content: `准确动作：\n1. 上传“${this.selectedFile.name}”到你的账号目录；\n2. 标记为“${type.label}”；\n3. 后台切分文本并建立私人知识库索引。\n\n是否继续？`,
        confirmText: '确认上传',
        success: ({ confirm }) => { if (confirm) this.uploadKnowledge() }
      })
    },
    async uploadKnowledge() {
      this.uploading = true
      try {
        const data = await api.uploadKnowledge(this.selectedFile.path, this.knowledgeType)
        this.uploadResult = data.message || '上传成功，后台正在处理。'
        this.taskId = data.task_id || ''
        this.taskStatus = data.status || ''
        uni.showToast({ title: '上传成功', icon: 'success' })
      } catch (error) { uni.showToast({ title: error.message, icon: 'none', duration: 3200 }) }
      finally { this.uploading = false }
    },
    async checkTask() {
      if (!this.taskId) return
      this.checkingTask = true
      try {
        const data = await api.getKnowledgeTask(this.taskId)
        this.taskStatus = data.status
        this.taskError = data.last_error || ''
        if (data.status === 'succeeded') this.uploadResult = '知识库索引已构建完成。'
      } catch (error) { uni.showToast({ title: error.message, icon: 'none' }) }
      finally { this.checkingTask = false }
    }
  },
  computed: {
    taskStatusText() { return { queued: '排队中', running: '处理中', succeeded: '已完成', failed: '失败', publish_failed: '等待后台重试' }[this.taskStatus] || this.taskStatus }
  }
}
</script>

<style scoped>
.knowledge-page { background: radial-gradient(circle at 5% 5%, #dff6ec 0, transparent 26%), #f5f7fb; }
.knowledge-hero { position: relative; min-height: 250rpx; padding: 36rpx; overflow: hidden; color: #163f38; background: linear-gradient(135deg, #dff7ed, #bfead9); border-radius: 34rpx; }
.hero-copy { position: relative; z-index: 2; width: 63%; }
.hero-tag { color: #3f8f77; font-size: 17rpx; font-weight: 850; letter-spacing: 3rpx; }
.hero-title { margin-top: 18rpx; font-size: 43rpx; font-weight: 900; }
.hero-desc { margin-top: 14rpx; color: #52786e; font-size: 22rpx; line-height: 1.65; }
.books-art { position: absolute; right: 18rpx; bottom: 10rpx; width: 240rpx; height: 220rpx; }
.book { position: absolute; right: 18rpx; width: 150rpx; height: 45rpx; border-radius: 8rpx 18rpx 18rpx 8rpx; box-shadow: 0 10rpx 20rpx rgba(37,113,90,.14); }
.book::after { position: absolute; top: 10rpx; right: 12rpx; bottom: 10rpx; left: 15rpx; content: ''; background: rgba(255,255,255,.72); border-radius: 4rpx 12rpx 12rpx 4rpx; }
.book-a { bottom: 31rpx; background: #3fa987; transform: rotate(-3deg); }
.book-b { right: 34rpx; bottom: 78rpx; background: #f2b968; transform: rotate(5deg); }
.book-c { right: 16rpx; bottom: 125rpx; background: #7770d6; transform: rotate(-4deg); }
.leaf { position: absolute; width: 50rpx; height: 25rpx; background: #4cab87; border-radius: 50% 0 50% 0; }
.leaf-a { top: 10rpx; right: 85rpx; transform: rotate(28deg); }
.leaf-b { top: 35rpx; right: 42rpx; transform: rotate(100deg); }
.login-callout { padding: 50rpx 34rpx; text-align: center; }
.login-icon { display: flex; align-items: center; justify-content: center; width: 86rpx; height: 86rpx; margin: 0 auto 22rpx; color: #287b63; background: #e1f7ef; border-radius: 25rpx; font-weight: 850; }
.coverage-card { margin-top: 23rpx; padding: 25rpx; color: #fff; background: linear-gradient(135deg, #225f51, #378d74); border-radius: 27rpx; }
.coverage-title { font-size: 24rpx; font-weight: 780; }
.coverage-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 12rpx; margin-top: 20rpx; }
.coverage-grid > view { display: flex; align-items: center; gap: 12rpx; color: #d9f6ec; font-size: 20rpx; }
.coverage-grid text { display: flex; align-items: center; justify-content: center; width: 47rpx; height: 47rpx; color: #225f51; background: #fff; border-radius: 14rpx; font-weight: 850; }
.upload-card { padding: 31rpx; }
.section-label { color: #4b9a82; font-size: 18rpx; font-weight: 850; letter-spacing: 2rpx; }
.file-section { margin-top: 29rpx; }
.type-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14rpx; margin-top: 19rpx; }
.type-card { position: relative; display: flex; align-items: center; min-height: 100rpx; padding: 18rpx; background: #f5f7f8; border: 2rpx solid transparent; border-radius: 20rpx; }
.type-card.active { background: #edfaf5; border-color: #69ba9f; box-shadow: 0 8rpx 22rpx rgba(65,151,121,.09); }
.type-icon { display: flex; align-items: center; justify-content: center; width: 53rpx; height: 53rpx; color: #347b65; background: #fff; border-radius: 15rpx; font-size: 20rpx; font-weight: 900; }
.type-copy { flex: 1; margin-left: 13rpx; color: #344d46; font-size: 22rpx; font-weight: 760; }
.type-copy text { display: block; margin-top: 4rpx; color: #8a9a95; font-size: 16rpx; font-weight: 400; }
.type-check { position: absolute; top: 9rpx; right: 11rpx; color: #3d9a7b; font-size: 20rpx; font-weight: 900; }
.upload-zone { margin-top: 20rpx; padding: 44rpx 22rpx; background: #f8fcfa; border: 3rpx dashed #9ad2bf; border-radius: 25rpx; text-align: center; }
.upload-illustration { position: relative; width: 85rpx; height: 82rpx; margin: 0 auto 16rpx; }
.paper { position: absolute; right: 0; bottom: 0; width: 61rpx; height: 75rpx; background: #fff; border: 4rpx solid #66b89d; border-radius: 8rpx; box-shadow: 0 9rpx 18rpx rgba(64,148,119,.13); }
.paper::after { position: absolute; top: 17rpx; left: 12rpx; width: 32rpx; height: 5rpx; content: ''; background: #a9d9c9; box-shadow: 0 14rpx 0 #a9d9c9, 0 28rpx 0 #a9d9c9; }
.upload-arrow { position: absolute; top: 0; left: 0; display: flex; align-items: center; justify-content: center; width: 48rpx; height: 48rpx; color: #fff; background: #5aaa8f; border-radius: 15rpx; font-size: 28rpx; font-weight: 900; }
.upload-title,.selected-name { color: #285d4f; font-size: 27rpx; font-weight: 800; }
.selected-name { word-break: break-all; }
.upload-note { margin-top: 9rpx; color: #8b9f98; font-size: 20rpx; }
.tips-title { margin-top: 25rpx; color: #526b64; font-size: 22rpx; font-weight: 750; }
.tip-chips { display: flex; flex-wrap: wrap; gap: 12rpx; margin-top: 14rpx; }
.tip-chips text { padding: 11rpx 17rpx; color: #477a6b; background: #eaf7f2; border-radius: 999rpx; font-size: 20rpx; }
.notice { display: flex; gap: 13rpx; margin-top: 22rpx; padding: 18rpx; color: #547064; background: #eef8f4; border-radius: 17rpx; font-size: 21rpx; line-height: 1.55; }
.notice-mark { font-weight: 900; }
.success-panel { margin-top: 20rpx; padding: 20rpx; color: #19734b; background: #eaf8f1; border-radius: 17rpx; font-size: 23rpx; line-height: 1.6; }
.task-panel { margin-top: 15rpx; padding: 18rpx; color: #315d53; background: #f0f7f5; border-radius: 16rpx; font-size: 20rpx; }
.task-panel text,.task-panel b { display: block; word-break: break-all; }
.task-panel b { margin-top: 8rpx; }
.task-panel button { margin-top: 12rpx; color: #276c5c; background: #dff2ec; font-size: 20rpx; }
</style>
