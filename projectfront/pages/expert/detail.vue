<template>
  <view class="page-shell detail-page">
    <view class="form-hero">
      <view class="eyebrow">EXPERT NAMING BRIEF</view>
      <view class="hero-title">专家起名资料单</view>
      <view class="hero-desc">资料越完整，专家越容易给出贴合家庭期待的名字。</view>
      <view class="step-row"><text class="active">1 填资料</text><text>2 选套餐</text><text>3 创建订单</text></view>
    </view>

    <view class="card">
      <view class="card-title">服务类型</view>
      <view class="chips"><view v-for="item in modes" :key="item.value" class="chip" :class="{active:form.service_mode===item.value}" @click="form.service_mode=item.value">{{ item.label }}</view></view>
      <view class="field"><text class="field-label">起名对象</text><view class="chips"><view v-for="item in types" :key="item.value" class="chip" :class="{active:form.naming_type===item.value}" @click="form.naming_type=item.value">{{ item.label }}</view></view></view>
      <view v-if="form.service_mode==='review'" class="field"><text class="field-label">待分析的名字 *</text><input v-model.trim="form.candidate_name" class="field-input" maxlength="100" placeholder="请输入已经有的名字" /></view>
    </view>

    <view class="card" v-if="form.naming_type==='person'">
      <view class="card-title">出生与五行资料</view>
      <view class="two-fields">
        <view class="field"><text class="field-label">姓氏 *</text><input v-model.trim="form.surname" class="field-input" maxlength="20" placeholder="例如：林" /></view>
        <view class="field"><text class="field-label">性别倾向</text><picker :range="genderLabels" @change="form.gender=genders[$event.detail.value].value"><view class="field-input picker-value">{{ genderText }}</view></picker></view>
      </view>
      <view class="two-fields">
        <view class="field"><text class="field-label">出生日期</text><picker mode="date" :value="birthDate" @change="birthDate=$event.detail.value"><view class="field-input picker-value">{{ birthDate || '请选择' }}</view></picker></view>
        <view class="field"><text class="field-label">出生时辰</text><picker mode="time" :value="birthTime" @change="birthTime=$event.detail.value"><view class="field-input picker-value">{{ birthTime || '请选择' }}</view></picker></view>
      </view>
      <view class="field"><text class="field-label">历法</text><view class="chips"><view class="chip" :class="{active:form.birth_calendar==='solar'}" @click="form.birth_calendar='solar'">阳历</view><view class="chip" :class="{active:form.birth_calendar==='lunar'}" @click="form.birth_calendar='lunar'">农历</view></view></view>
      <view class="field"><text class="field-label">出生地</text><input v-model.trim="form.birthplace" class="field-input" maxlength="200" placeholder="省 / 市 / 区县，用于时区与真太阳时参考" /></view>
      <view class="field"><text class="field-label">已知五行情况</text><input v-model.trim="form.five_elements" class="field-input" maxlength="200" placeholder="例如：五行缺水；不知道可留空，由专家分析" /></view>
      <view class="two-fields"><view class="field"><text class="field-label">辈分字</text><input v-model.trim="form.generation_character" class="field-input" maxlength="20" placeholder="选填" /></view><view class="field"><text class="field-label">避用字</text><input v-model.trim="form.avoid_characters" class="field-input" maxlength="200" placeholder="选填" /></view></view>
    </view>

    <view class="card">
      <view class="card-title">客户提交内容</view>
      <view class="field"><text class="field-label">背景与使用场景 *</text><textarea v-model.trim="form.background" class="field-textarea" maxlength="5000" placeholder="介绍家庭背景、公司行业或宠物特点，至少 10 字" /></view>
      <view class="field"><text class="field-label">重点关注 *</text><input v-model.trim="form.focus" class="field-input" maxlength="500" placeholder="例如：寓意、读音、五行、重名率" /></view>
      <view class="field"><text class="field-label">父母 / 客户期望</text><textarea v-model.trim="form.parent_expectations" class="field-textarea short" maxlength="3000" placeholder="希望名字传达怎样的性格、气质和祝福" /></view>
      <view class="field"><text class="field-label">其他原始内容</text><textarea v-model.trim="form.submitted_content" class="field-textarea short" maxlength="5000" placeholder="把想对专家说的话、备选字、家族要求等完整写在这里" /></view>
      <view class="field"><text class="field-label">补充说明</text><textarea v-model.trim="form.notes" class="field-textarea short" maxlength="3000" placeholder="选填" /></view>
    </view>

    <view class="card">
      <view class="card-title">参考图片（选填，最多 3 张）</view>
      <view class="image-grid">
        <view v-for="(path,index) in images" :key="path" class="image-item"><image :src="path" mode="aspectFill" @click="previewImage(index)"/><view class="remove-image" @click="removeImage(index)">×</view></view>
        <view v-if="images.length<3" class="image-add" @click="chooseImages"><text>＋</text><view>添加图片</view></view>
      </view>
      <view class="privacy-note">图片将保存在后端私有目录，仅订单客户、可接单的同等级专家、最终接单专家和管理员可查看。单张不超过 5MB。</view>
    </view>

    <view class="card">
      <view class="card-title">选择专家套餐 *</view>
      <view v-if="loading" class="state">正在加载套餐…</view>
      <view v-for="item in tiers" :key="item.code" class="tier-option" :class="{active:form.expert_level===item.code}" @click="form.expert_level=item.code">
        <view><view class="tier-name">{{ item.name }}<text>{{ item.delivery_days }}天内交付</text></view><view class="tier-desc">{{ item.description }}</view></view>
        <view class="tier-price">¥{{ item.price }}</view>
      </view>
    </view>

    <view class="pay-note">创建订单后先上传图片，再由你决定是否打开支付宝沙箱付款。付款后订单进入对应等级专家池，24 小时无人接单则进入人工退款处理。</view>
    <button class="primary-btn btn-gap" :loading="submitting" :disabled="submitting" @click="confirmOrder">确认资料并创建 ¥{{ selectedTier ? selectedTier.price : '--' }} 订单</button>
  </view>
</template>

<script>
import { api } from '../../api'
import { requireLogin } from '../../utils/auth'

export default {
  data() {
    return {
      loading: false, submitting: false, tiers: [], images: [], birthDate: '', birthTime: '',
      modes: [{ label: '请专家从零起名', value: 'naming' }, { label: '分析已有名字', value: 'review' }],
      types: [{ label: '人名', value: 'person' }, { label: '企业名', value: 'company' }, { label: '宠物名', value: 'pet' }],
      genders: [{ label: '不限', value: 'unspecified' }, { label: '男', value: 'male' }, { label: '女', value: 'female' }],
      form: { service_mode: 'naming', candidate_name: '', naming_type: 'person', expert_level: 'ordinary', surname: '', gender: 'unspecified', birth_calendar: 'solar', birthplace: '', five_elements: '', generation_character: '', avoid_characters: '', parent_expectations: '', submitted_content: '', background: '', focus: '', notes: '' }
    }
  },
  computed: {
    genderLabels() { return this.genders.map(item => item.label) },
    genderText() { return (this.genders.find(item => item.value === this.form.gender) || this.genders[0]).label },
    selectedTier() { return this.tiers.find(item => item.code === this.form.expert_level) }
  },
  onLoad(options) { if (options.tier) this.form.expert_level = options.tier; this.loadTiers() },
  methods: {
    async loadTiers() { this.loading = true; try { this.tiers = await api.getExpertTiers() } catch (error) { uni.showToast({ title: error.message, icon: 'none' }) } finally { this.loading = false } },
    validate() {
      if (this.form.service_mode === 'review' && !this.form.candidate_name) return '请填写待分析的名字'
      if (this.form.service_mode === 'naming' && this.form.naming_type === 'person' && !this.form.surname) return '请填写姓氏'
      if (this.form.background.length < 10) return '背景与使用场景至少填写 10 字'
      if (this.form.focus.length < 2) return '请填写重点关注内容'
      if (!this.selectedTier) return '请选择专家套餐'
      return ''
    },
    chooseImages() {
      uni.chooseImage({ count: 3 - this.images.length, sizeType: ['compressed'], success: ({ tempFilePaths, tempFiles }) => {
        const valid = tempFilePaths.filter((path, index) => !tempFiles || !tempFiles[index] || tempFiles[index].size <= 5 * 1024 * 1024)
        if (valid.length !== tempFilePaths.length) uni.showToast({ title: '已跳过超过 5MB 的图片', icon: 'none' })
        this.images = this.images.concat(valid).slice(0, 3)
      } })
    },
    removeImage(index) { this.images.splice(index, 1) },
    previewImage(index) { uni.previewImage({ current: this.images[index], urls: this.images }) },
    confirmOrder() {
      if (!requireLogin()) return
      const error = this.validate(); if (error) { uni.showToast({ title: error, icon: 'none' }); return }
      uni.showModal({ title: '确认创建专家起名订单', content: `准确动作：\n1. 保存本次起名资料；\n2. 创建“${this.selectedTier.name}”订单，金额 ¥${this.selectedTier.price}；\n3. 上传 ${this.images.length} 张私有图片；\n4. 创建后再由你决定是否打开支付宝付款。\n\n是否继续？`, confirmText: '创建订单', success: ({ confirm }) => { if (confirm) this.createOrder() } })
    },
    payload() {
      const data = { ...this.form, package_id: null }
      data.birth_datetime = this.birthDate ? `${this.birthDate}T${this.birthTime || '00:00'}:00` : null
      Object.keys(data).forEach(key => { if (data[key] === '') data[key] = null })
      return data
    },
    async createOrder() {
      this.submitting = true
      try {
        const order = await api.createExpertOrder(this.payload())
        let uploaded = 0
        for (const path of this.images) { await api.uploadExpertOrderImage(order.id, path); uploaded += 1 }
        uni.showModal({ title: '订单资料已保存', content: `订单号：${order.order_no}\n套餐：${order.package_name}\n金额：¥${order.amount}\n图片：已上传 ${uploaded} 张\n\n打开支付宝仅进入沙箱支付页，最终付款仍需你在支付宝页面确认。`, confirmText: '打开支付宝', cancelText: '稍后支付', success: ({ confirm }) => { if (confirm) this.openPay(order.pay_url); else uni.redirectTo({ url: '/pages/expert/orders' }) } })
      } catch (error) { uni.showToast({ title: error.message, icon: 'none', duration: 3500 }) }
      finally { this.submitting = false }
    },
    openPay(url) {
      // #ifdef H5
      window.location.href = url
      // #endif
      // #ifndef H5
      uni.setClipboardData({ data: url, success: () => uni.showModal({ title: '支付链接已复制', content: '请在浏览器打开链接完成沙箱支付。', showCancel: false }) })
      // #endif
    }
  }
}
</script>

<style scoped>
.detail-page{background:#f5f7fb}.form-hero{padding:34rpx;color:#fff;background:linear-gradient(145deg,#25244f,#6451d6);border-radius:32rpx}.eyebrow{color:#d8d3ff;font-size:17rpx;font-weight:800;letter-spacing:4rpx}.hero-title{margin-top:12rpx;font-size:40rpx;font-weight:850}.hero-desc{margin-top:9rpx;color:#e1defb;font-size:21rpx}.step-row{display:flex;gap:10rpx;margin-top:25rpx}.step-row text{flex:1;padding:10rpx 4rpx;color:#bfb9e8;background:rgba(255,255,255,.09);border-radius:11rpx;font-size:17rpx;text-align:center}.step-row .active{color:#40378e;background:#fff;font-weight:800}.two-fields{display:grid;grid-template-columns:1fr 1fr;gap:14rpx}.picker-value{line-height:76rpx}.short{min-height:130rpx}.image-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:13rpx;margin-top:18rpx}.image-item,.image-add{position:relative;height:180rpx;border-radius:18rpx;overflow:hidden}.image-item image{width:100%;height:100%}.remove-image{position:absolute;top:8rpx;right:8rpx;width:38rpx;height:38rpx;color:#fff;background:rgba(25,28,39,.72);border-radius:50%;line-height:36rpx;text-align:center}.image-add{display:flex;flex-direction:column;align-items:center;justify-content:center;color:#6b62bb;background:#f1efff;border:2rpx dashed #beb8ec;font-size:19rpx}.image-add text{font-size:43rpx}.privacy-note,.pay-note{margin-top:17rpx;padding:17rpx;color:#75612d;background:#fff6da;border-radius:15rpx;font-size:19rpx;line-height:1.65}.tier-option{display:flex;align-items:center;justify-content:space-between;margin-top:14rpx;padding:20rpx;border:2rpx solid #eceef3;border-radius:18rpx}.tier-option.active{border-color:#7568ef;background:#f4f2ff}.tier-name{font-size:24rpx;font-weight:850}.tier-name text{margin-left:10rpx;color:#847ba9;font-size:17rpx;font-weight:400}.tier-desc{max-width:480rpx;margin-top:6rpx;color:#8b93a3;font-size:18rpx;line-height:1.45}.tier-price{color:#4d42af;font-size:28rpx;font-weight:900}.state{text-align:center;color:#8d95a5}
</style>
