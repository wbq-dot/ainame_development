<template>
  <view class="package-form-page">
    <view class="form-hero">
      <view class="hero-mark">{{ isEditing ? '编' : '新' }}</view>
      <view class="hero-copy">
        <view class="hero-eyebrow">PACKAGE OPERATION</view>
        <view class="hero-title">{{ isEditing ? '编辑平台套餐' : '新建平台套餐' }}</view>
        <view class="hero-desc">{{ isEditing ? '修改仅影响保存后创建的新订单，历史订单继续使用原始快照。' : '新套餐保存后默认下架，复核内容后再返回列表手动上架。' }}</view>
      </view>
    </view>

    <view v-if="loading" class="state-card">正在加载套餐信息…</view>

    <view v-else class="form-card">
      <view class="form-heading">
        <view><b>套餐基本信息</b><text>名称不可重复，价格精确到分，次数必须为正整数。</text></view>
        <view class="status-tag">{{ isEditing ? '已下架 · 可编辑' : '保存为下架' }}</view>
      </view>

      <view class="field first-field">
        <text class="field-label">套餐名称 *</text>
        <input v-model="form.name" class="field-input" type="text" maxlength="100" placeholder="例如：起名体验包" />
        <view class="field-hint">1–100 个字符，系统会自动去除首尾空格。</view>
      </view>

      <view class="field">
        <text class="field-label">权益类型 *</text>
        <view class="type-options">
          <view class="type-option" :class="{ active: form.credit_type === 'name' }" @click="form.credit_type = 'name'">
            <view class="type-icon name">名</view>
            <view><b>智能起名</b><text>到账起名次数</text></view>
          </view>
          <view class="type-option" :class="{ active: form.credit_type === 'logo' }" @click="form.credit_type = 'logo'">
            <view class="type-icon logo">标</view>
            <view><b>Logo 生成</b><text>到账 Logo 次数</text></view>
          </view>
        </view>
      </view>

      <view class="field-grid">
        <view class="field">
          <text class="field-label">销售价格 *</text>
          <view class="input-affix"><text>¥</text><input v-model.trim="form.price" type="text" maxlength="11" placeholder="0.00" /></view>
          <view class="field-hint">必须大于 0，最多两位小数。</view>
        </view>
        <view class="field">
          <text class="field-label">包含次数 *</text>
          <view class="input-affix"><input v-model.trim="form.credit_count" type="number" maxlength="10" placeholder="1" /><text>次</text></view>
          <view class="field-hint">正整数，最高 2147483647。</view>
        </view>
      </view>

      <view class="effect-note">
        <view class="effect-icon">影</view>
        <view><b>生效范围</b><text>{{ isEditing ? '保存后，新订单使用新的名称、类型、价格和次数；已有订单不受影响。' : '保存不会立即向用户展示；只有返回套餐列表并手动上架后，用户才能创建订单。' }}</text></view>
      </view>

      <view class="form-actions">
        <button class="cancel-btn" :disabled="submitting" @click="cancel">取消</button>
        <button class="save-btn" :loading="submitting" :disabled="!canSubmit || submitting" @click="confirmSubmit">{{ isEditing ? '保存修改' : '创建套餐' }}</button>
      </view>
    </view>
  </view>
</template>

<script>
import { api } from '../../api'
import { handleAdminAuthError, requireAdminSession } from '../../utils/auth'

export default {
  data() {
    return {
      packageId: null,
      loading: false,
      submitting: false,
      original: null,
      form: { name: '', credit_type: 'name', price: '', credit_count: '' }
    }
  },
  computed: {
    isEditing() {
      return Number.isInteger(this.packageId) && this.packageId > 0
    },
    normalizedName() {
      return String(this.form.name || '').trim()
    },
    priceValid() {
      const value = String(this.form.price || '').trim()
      return /^(?:0|[1-9]\d{0,7})(?:\.\d{1,2})?$/.test(value) && Number(value) > 0
    },
    creditCountValue() {
      const value = String(this.form.credit_count || '').trim()
      if (!/^[1-9]\d{0,9}$/.test(value)) return null
      const parsed = Number(value)
      return Number.isSafeInteger(parsed) && parsed <= 2147483647 ? parsed : null
    },
    isChanged() {
      if (!this.isEditing || !this.original) return true
      return this.normalizedName !== this.original.name
        || this.form.credit_type !== this.original.credit_type
        || Number(this.form.price) !== Number(this.original.price)
        || this.creditCountValue !== Number(this.original.credit_count)
    },
    hasUnsavedChanges() {
      if (this.isEditing) return this.isChanged
      return Boolean(this.normalizedName || String(this.form.price || '').trim() || String(this.form.credit_count || '').trim() || this.form.credit_type !== 'name')
    },
    canSubmit() {
      return this.normalizedName.length >= 1
        && this.normalizedName.length <= 100
        && ['name', 'logo'].includes(this.form.credit_type)
        && this.priceValid
        && this.creditCountValue !== null
        && this.isChanged
    }
  },
  onLoad(options) {
    if (!requireAdminSession()) return
    const rawId = options && options.id
    if (!rawId) {
      uni.setNavigationBarTitle({ title: '新建套餐' })
      return
    }
    const packageId = Number(rawId)
    if (!Number.isInteger(packageId) || packageId <= 0) {
      uni.showModal({ title: '套餐参数无效', content: '无法识别要编辑的套餐，请从平台套餐管理重新进入。', showCancel: false, success: () => this.backToList() })
      return
    }
    this.packageId = packageId
    uni.setNavigationBarTitle({ title: '编辑套餐' })
    this.loadPackage()
  },
  methods: {
    async loadPackage() {
      this.loading = true
      try {
        const item = await api.getAdminPackage(this.packageId)
        if (item.is_active) {
          uni.showModal({ title: '请先下架套餐', content: '已上架套餐不能编辑。请返回列表下架后再进入编辑页面。', showCancel: false, success: () => this.backToList() })
          return
        }
        this.original = { ...item }
        this.form = {
          name: item.name,
          credit_type: item.credit_type,
          price: String(item.price),
          credit_count: String(item.credit_count)
        }
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 3000 })
        if (!handleAdminAuthError(error)) setTimeout(() => this.backToList(), 500)
      } finally {
        this.loading = false
      }
    },
    payload() {
      return {
        name: this.normalizedName,
        credit_type: this.form.credit_type,
        price: String(this.form.price).trim(),
        credit_count: this.creditCountValue
      }
    },
    typeLabel(value) {
      return value === 'logo' ? 'Logo 生成' : '智能起名'
    },
    changeSummary() {
      if (!this.original) return ''
      const lines = []
      if (this.normalizedName !== this.original.name) lines.push(`名称：${this.original.name} → ${this.normalizedName}`)
      if (this.form.credit_type !== this.original.credit_type) lines.push(`类型：${this.typeLabel(this.original.credit_type)} → ${this.typeLabel(this.form.credit_type)}`)
      if (Number(this.form.price) !== Number(this.original.price)) lines.push(`价格：¥${this.original.price} → ¥${this.form.price}`)
      if (this.creditCountValue !== Number(this.original.credit_count)) lines.push(`次数：${this.original.credit_count} → ${this.creditCountValue}`)
      return lines.join('\n')
    },
    confirmSubmit() {
      if (!this.canSubmit || this.submitting) return
      const data = this.payload()
      const details = this.isEditing
        ? `${this.changeSummary()}\n\n修改仅影响之后创建的新订单，历史订单不受影响。`
        : `名称：${data.name}\n类型：${this.typeLabel(data.credit_type)}\n价格：¥${data.price}\n次数：${data.credit_count}\n\n创建后默认为下架状态，不会立即展示给用户。`
      uni.showModal({
        title: this.isEditing ? '确认保存套餐修改' : '确认新建套餐',
        content: details,
        confirmText: this.isEditing ? '确认保存' : '确认创建',
        confirmColor: '#6257e8',
        success: ({ confirm }) => {
          if (confirm) this.submit()
        }
      })
    },
    async submit() {
      this.submitting = true
      try {
        const result = this.isEditing
          ? await api.updateAdminPackage(this.packageId, this.payload())
          : await api.createAdminPackage(this.payload())
        uni.showToast({ title: result.message, icon: 'success' })
        setTimeout(() => uni.redirectTo({ url: '/pages/admin/packages' }), 450)
      } catch (error) {
        uni.showToast({ title: error.message, icon: 'none', duration: 3000 })
        handleAdminAuthError(error)
      } finally {
        this.submitting = false
      }
    },
    cancel() {
      if (!this.hasUnsavedChanges) {
        this.backToList()
        return
      }
      uni.showModal({
        title: '放弃未保存内容',
        content: '当前填写内容尚未保存，确认返回平台套餐管理吗？',
        confirmText: '放弃并返回',
        confirmColor: '#d94a64',
        success: ({ confirm }) => {
          if (confirm) this.backToList()
        }
      })
    },
    backToList() {
      uni.redirectTo({ url: '/pages/admin/packages' })
    }
  }
}
</script>

<style scoped>
.package-form-page { min-height: 100vh; padding: 28rpx 28rpx 70rpx; background: radial-gradient(circle at 100% 0,#e9e5ff 0,transparent 24%),#f3f5f9; }
.form-hero { display: flex; align-items: center; gap: 22rpx; padding: 32rpx; color: #fff; background: linear-gradient(135deg,#171d2d,#3e445f); border-radius: 29rpx; box-shadow: 0 18rpx 42rpx rgba(23,29,45,.18); }
.hero-mark { display: flex; flex: 0 0 82rpx; align-items: center; justify-content: center; width: 82rpx; height: 82rpx; color: #292d42; background: linear-gradient(135deg,#f4da90,#ddb957); border-radius: 23rpx; font-size: 31rpx; font-weight: 900; }
.hero-copy { flex: 1; min-width: 0; }
.hero-eyebrow { color: #f2d586; font-size: 16rpx; font-weight: 800; letter-spacing: 4rpx; }
.hero-title { margin-top: 8rpx; font-size: 37rpx; font-weight: 850; }
.hero-desc { margin-top: 8rpx; color: #c8cedb; font-size: 20rpx; line-height: 1.5; }
.state-card,.form-card { margin-top: 20rpx; padding: 28rpx; background: #fff; border-radius: 25rpx; box-shadow: 0 11rpx 32rpx rgba(36,55,86,.055); }
.state-card { padding: 60rpx 20rpx; color: #929aaa; text-align: center; }
.form-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 18rpx; padding-bottom: 22rpx; border-bottom: 1rpx solid #eceef3; }
.form-heading b { display: block; font-size: 28rpx; }
.form-heading text { display: block; margin-top: 7rpx; color: #8b94a5; font-size: 19rpx; line-height: 1.5; }
.status-tag { flex: 0 0 auto; padding: 8rpx 13rpx; color: #93621d; background: #fff2d8; border-radius: 999rpx; font-size: 17rpx; }
.first-field { margin-top: 24rpx; }
.field-hint { margin-top: 8rpx; color: #9aa2b1; font-size: 18rpx; }
.type-options { display: grid; grid-template-columns: 1fr 1fr; gap: 13rpx; }
.type-option { display: flex; align-items: center; gap: 14rpx; padding: 20rpx; color: #737d90; background: #f4f5f8; border: 2rpx solid transparent; border-radius: 19rpx; }
.type-option.active { color: #40369b; background: #f0eeff; border-color: #8579ec; }
.type-icon { display: flex; flex: 0 0 54rpx; align-items: center; justify-content: center; width: 54rpx; height: 54rpx; color: #fff; background: #6257e8; border-radius: 16rpx; font-size: 20rpx; font-weight: 850; }
.type-icon.logo { background: #368b78; }
.type-option b,.type-option text { display: block; }
.type-option b { font-size: 21rpx; }
.type-option text { margin-top: 4rpx; font-size: 17rpx; }
.field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16rpx; }
.input-affix { display: flex; align-items: center; height: 92rpx; padding: 0 22rpx; color: #687286; background: #f4f6fa; border: 2rpx solid transparent; border-radius: 20rpx; }
.input-affix input { flex: 1; min-width: 0; height: 88rpx; color: #182238; font-size: 28rpx; }
.input-affix > text:first-child { margin-right: 9rpx; }
.input-affix > text:last-child { margin-left: 9rpx; }
.effect-note { display: flex; align-items: flex-start; gap: 15rpx; margin-top: 28rpx; padding: 20rpx; color: #626d81; background: #edf0f5; border-radius: 18rpx; }
.effect-icon { display: flex; flex: 0 0 48rpx; align-items: center; justify-content: center; width: 48rpx; height: 48rpx; color: #fff; background: #6257e8; border-radius: 14rpx; font-size: 17rpx; font-weight: 850; }
.effect-note b,.effect-note text { display: block; }
.effect-note b { color: #374054; font-size: 20rpx; }
.effect-note text { margin-top: 5rpx; font-size: 18rpx; line-height: 1.55; }
.form-actions { display: flex; gap: 14rpx; margin-top: 28rpx; }
.form-actions button { flex: 1; height: 76rpx; margin: 0; border-radius: 19rpx; font-size: 23rpx; line-height: 76rpx; }
.cancel-btn { color: #657086; background: #eef0f4; }
.save-btn { color: #fff; background: linear-gradient(135deg,#6257e8,#8a6df1); box-shadow: 0 12rpx 25rpx rgba(98,87,232,.2); }

@media (min-width: 1000px) {
  .package-form-page { max-width: 900px; margin: 0 auto; padding: 34px; }
  .form-card { padding: 34px; }
}
</style>
