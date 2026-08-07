<template>
  <view class="page-shell create-page">
    <view class="page-title">创作工具</view>
    <view class="page-subtitle">上传你的品牌规则，或为企业生成一枚专属 Logo。</view>

    <view v-if="!loggedIn" class="card login-callout">
      <view class="login-icon">钥</view>
      <view class="card-title">登录后使用创作工具</view>
      <view class="card-note">专属知识库与 Logo 生成都会使用你的登录身份，请先登录或注册。</view>
      <button class="primary-btn btn-gap" @click="goLogin">登录 / 注册</button>
    </view>

    <template v-else>
      <view class="mode-switch">
        <view class="mode-item" :class="{ active: mode === 'knowledge' }" @click="mode = 'knowledge'">知识库</view>
        <view class="mode-item" :class="{ active: mode === 'logo' }" @click="mode = 'logo'">Logo 生成</view>
      </view>

    <view v-if="mode === 'knowledge'" class="card tool-card">
      <view class="tool-visual knowledge-visual">
        <view class="visual-icon">文</view>
        <view>
          <view class="card-title">专属知识库</view>
          <view class="card-note">文件将由后端异步切分并存入你的私人向量库。</view>
        </view>
      </view>

      <view class="upload-zone" @click="chooseFile">
        <view class="upload-plus">＋</view>
        <view v-if="selectedFile" class="selected-name">{{ selectedFile.name }}</view>
        <view v-else class="upload-title">点击选择 PDF 或 TXT</view>
        <view class="upload-note">支持 PDF/TXT，单个文件最大 10MB</view>
      </view>

      <view class="notice">
        <text class="notice-mark">i</text>
        <text>上传成功只表示任务已进入 RabbitMQ；向量化是否完成需查看后端 worker 日志。</text>
      </view>
      <button class="primary-btn btn-gap" :loading="uploading" :disabled="uploading || !selectedFile" @click="confirmUpload">
        上传并构建知识库
      </button>
      <view v-if="uploadResult" class="success-panel">{{ uploadResult }}</view>
    </view>

    <view v-else class="card tool-card">
      <view class="tool-visual logo-visual">
        <view class="visual-icon">图</view>
        <view>
          <view class="card-title">企业 Logo 生成</view>
          <view class="card-note">调用后端已配置的通义万相模型，并保存到静态目录。</view>
        </view>
      </view>

      <view class="field">
        <text class="field-label">企业名称</text>
        <input v-model.trim="logoForm.company_name" class="field-input" maxlength="50" placeholder="例如：青衍科技" />
      </view>
      <view class="field">
        <text class="field-label">风格要求（选填）</text>
        <textarea v-model.trim="logoForm.style_feedback" class="field-textarea" maxlength="300" placeholder="例如：蓝紫渐变、科技感、图形简洁，不要文字" />
      </view>
      <view class="notice warning">
        <text class="notice-mark">!</text>
        <text>此操作会调用付费或计量的外部模型。点击下方按钮后会先让你确认。</text>
      </view>
      <button class="primary-btn btn-gap" :loading="logoLoading" :disabled="logoLoading || !logoForm.company_name" @click="confirmGenerateLogo">
        生成 Logo
      </button>

      <view v-if="logoResult" class="logo-result">
        <image v-if="logoResult.logo_url" class="logo-image" :src="logoResult.logo_url" mode="aspectFit" @click="previewLogo" />
        <view v-else class="logo-empty">没有返回图片</view>
        <view class="logo-status">{{ logoResult.logo_status }}</view>
        <view class="prompt-box">
          <view class="prompt-title">实际生成提示词</view>
          <view class="prompt-content">{{ logoResult.logo_prompt }}</view>
        </view>
      </view>
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
      mode: 'knowledge',
      selectedFile: null,
      uploading: false,
      uploadResult: '',
      logoLoading: false,
      logoForm: { company_name: '', style_feedback: '' },
      logoResult: null
    }
  },
  onShow() {
    this.loggedIn = Boolean(getAccessToken())
    const defaultMode = uni.getStorageSync('create_default_mode')
    if (defaultMode === 'knowledge' || defaultMode === 'logo') this.mode = defaultMode
    uni.removeStorageSync('create_default_mode')
  },
  methods: {
    goLogin() {
      uni.navigateTo({ url: '/pages/auth/login' })
    },
    chooseFile() {
      // #ifdef H5
      uni.chooseFile({
        count: 1,
        extension: ['.pdf', '.txt'],
        success: (res) => this.acceptFile(res.tempFiles[0], res.tempFilePaths[0])
      })
      // #endif

      // #ifdef MP-WEIXIN
      uni.chooseMessageFile({
        count: 1,
        type: 'file',
        extension: ['pdf', 'txt'],
        success: (res) => this.acceptFile(res.tempFiles[0], res.tempFiles[0].path)
      })
      // #endif

      // #ifdef APP-PLUS
      uni.showModal({
        title: '当前测试方式不支持',
        content: '本次最小版本请先在 HBuilderX 的 H5 浏览器运行中测试文件上传。',
        showCancel: false
      })
      // #endif
    },
    acceptFile(file, path) {
      const name = file.name || path.split('/').pop()
      if (!/\.(pdf|txt)$/i.test(name)) {
        uni.showToast({ title: '只能选择 PDF 或 TXT 文件', icon: 'none' })
        return
      }
      this.selectedFile = { name, path: file.path || path }
      this.uploadResult = ''
    },
    confirmUpload() {
      if (!requireLogin()) return
      uni.showModal({
        title: '确认上传文件',
        content: `将上传“${this.selectedFile.name}”到后端，并把任务发送到 RabbitMQ 构建你的私人知识库。是否继续？`,
        confirmText: '确认上传',
        success: ({ confirm }) => {
          if (confirm) this.uploadKnowledge()
        }
      })
    },
    async uploadKnowledge() {
      this.uploading = true
      try {
        const data = await api.uploadKnowledge(this.selectedFile.path)
        this.uploadResult = data.message || '上传成功，后台正在处理。'
        uni.showToast({ title: '上传成功', icon: 'success' })
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 3200 })
      } finally {
        this.uploading = false
      }
    },
    confirmGenerateLogo() {
      if (!requireLogin()) return
      uni.showModal({
        title: '确认调用图片模型',
        content: `将使用企业名称“${this.logoForm.company_name}”调用后端图片模型，可能产生外部模型用量。是否继续？`,
        confirmText: '确认生成',
        success: ({ confirm }) => {
          if (confirm) this.generateLogo()
        }
      })
    },
    async generateLogo() {
      this.logoLoading = true
      this.logoResult = null
      try {
        this.logoResult = await api.generateLogo(this.logoForm)
        uni.showToast({ title: this.logoResult.logo_status, icon: this.logoResult.logo_url ? 'success' : 'none' })
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 3200 })
      } finally {
        this.logoLoading = false
      }
    },
    previewLogo() {
      uni.previewImage({ urls: [this.logoResult.logo_url], current: this.logoResult.logo_url })
    }
  }
}
</script>

<style scoped>
.create-page { background: radial-gradient(circle at 0 0, #e7f4ff 0, transparent 24%), #f5f7fb; }
.login-callout { margin-top: 34rpx; padding: 52rpx 34rpx; text-align: center; }
.login-icon { display: flex; align-items: center; justify-content: center; width: 90rpx; height: 90rpx; margin: 0 auto 24rpx; color: #6257e8; background: #ebe9ff; border-radius: 26rpx; font-size: 36rpx; font-weight: 800; }
.mode-switch { display: grid; grid-template-columns: 1fr 1fr; gap: 8rpx; margin-top: 30rpx; padding: 8rpx; background: #e9ecf2; border-radius: 23rpx; }
.mode-item { height: 76rpx; color: #778196; border-radius: 17rpx; font-size: 26rpx; font-weight: 700; line-height: 76rpx; text-align: center; }
.mode-item.active { color: #4439b0; background: #fff; box-shadow: 0 8rpx 24rpx rgba(36, 55, 86, 0.08); }
.tool-card { padding: 32rpx; }
.tool-visual { display: flex; align-items: center; gap: 22rpx; padding: 23rpx; border-radius: 23rpx; }
.knowledge-visual { background: linear-gradient(135deg, #e5f6ef, #effaf6); }
.logo-visual { background: linear-gradient(135deg, #fff0df, #fff7ec); }
.visual-icon { display: flex; align-items: center; justify-content: center; width: 75rpx; height: 75rpx; color: #4439a8; background: rgba(255, 255, 255, 0.86); border-radius: 20rpx; font-size: 29rpx; font-weight: 850; }
.upload-zone { margin-top: 28rpx; padding: 52rpx 24rpx; background: #fafbfc; border: 3rpx dashed #cbd2df; border-radius: 24rpx; text-align: center; }
.upload-plus { width: 72rpx; height: 72rpx; margin: 0 auto 18rpx; color: #6257e8; background: #ebe9ff; border-radius: 50%; font-size: 43rpx; line-height: 68rpx; }
.upload-title, .selected-name { font-size: 27rpx; font-weight: 700; }
.selected-name { color: #5046bd; word-break: break-all; }
.upload-note { margin-top: 10rpx; color: #98a1b1; font-size: 21rpx; }
.notice { display: flex; gap: 14rpx; margin-top: 24rpx; padding: 18rpx 20rpx; color: #547064; background: #eef8f4; border-radius: 17rpx; font-size: 22rpx; line-height: 1.55; }
.notice.warning { color: #795c2f; background: #fff7e9; }
.notice-mark { flex: 0 0 30rpx; font-weight: 850; }
.success-panel { margin-top: 20rpx; padding: 20rpx; color: #19734b; background: #eaf8f1; border-radius: 17rpx; font-size: 23rpx; line-height: 1.6; }
.logo-result { margin-top: 28rpx; }
.logo-image, .logo-empty { width: 100%; height: 560rpx; background: #f4f5f8; border-radius: 25rpx; }
.logo-empty { display: flex; align-items: center; justify-content: center; color: #9aa2b1; }
.logo-status { margin-top: 16rpx; color: #5248ba; font-size: 25rpx; font-weight: 700; text-align: center; }
.prompt-box { margin-top: 22rpx; padding: 22rpx; background: #f4f6fa; border-radius: 18rpx; }
.prompt-title { font-size: 23rpx; font-weight: 700; }
.prompt-content { margin-top: 10rpx; color: #6f788b; font-size: 21rpx; line-height: 1.65; white-space: pre-wrap; }
</style>
