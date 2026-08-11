<template>
  <view class="page-shell apply-page">
    <view class="page-title">专家入驻</view><view class="page-subtitle">审核通过后账号角色将变为专家，可创建服务套餐并接单。</view>
    <view v-if="loading" class="card center">正在读取申请状态…</view>
    <view v-else-if="profile && profile.status !== 'rejected'" class="status-card" :class="profile.status">
      <view class="status-title">{{ statusText(profile.status) }}</view><view class="status-desc">{{ statusDesc(profile.status) }}</view><view v-if="profile.review_note" class="review-note">审核备注：{{ profile.review_note }}</view>
      <button v-if="profile.status==='approved'" class="primary-btn btn-gap" @click="openWorkbench">进入专家工作台</button>
    </view>
    <view v-else class="card">
      <view class="card-title">{{ profile ? '修改后重新提交' : '填写公开专家资料' }}</view>
      <view v-if="profile && profile.review_note" class="reject-note">上次审核意见：{{ profile.review_note }}</view>
      <view class="field"><text class="field-label">专家展示名</text><input v-model.trim="form.display_name" class="field-input" maxlength="50" placeholder="2至50字" /></view>
      <view class="field"><text class="field-label">专业头衔</text><input v-model.trim="form.title" class="field-input" maxlength="100" placeholder="例如：品牌命名顾问" /></view>
      <view class="field"><text class="field-label">擅长领域</text><input v-model.trim="form.specialties" class="field-input" maxlength="500" placeholder="例如：企业名、人名、文化寓意" /></view>
      <view class="field"><text class="field-label">从业年限</text><input v-model.number="form.experience_years" class="field-input" type="number" placeholder="0至80" /></view>
      <view class="field"><text class="field-label">个人介绍</text><textarea v-model.trim="form.bio" class="field-textarea" maxlength="3000" placeholder="介绍经验、方法和代表能力，至少20字" /></view>
      <view class="file-row" @click="chooseCredential"><view><view>能力证明 PDF（选填）</view><text>{{ credentialName || '不超过10MB；请勿上传身份证、银行卡或收款账号' }}</text></view><view>选择文件</view></view>
      <view class="privacy-note">首版不收集身份证、银行卡或支付宝账号。资质附件仅申请人和管理员可下载。</view>
      <button class="primary-btn btn-gap" :loading="submitting" :disabled="submitting" @click="submit">提交专家申请</button>
    </view>
  </view>
</template>

<script>
import { api } from '../../api'
export default {
  data(){return{loading:false,submitting:false,profile:null,credentialPath:'',credentialName:'',form:{display_name:'',title:'',specialties:'',experience_years:0,bio:''}}},
  onShow(){this.load()},
  methods:{
    async load(){this.loading=true;try{this.profile=await api.getExpertApplication();if(this.profile&&this.profile.status==='rejected'){Object.keys(this.form).forEach(key=>{this.form[key]=this.profile[key]??this.form[key]})}}catch(error){uni.showToast({title:error.message,icon:'none'})}finally{this.loading=false}},
    statusText(status){return{pending:'申请审核中',approved:'已成为专家',suspended:'专家资格已停用'}[status]||status},
    statusDesc(status){return{pending:'管理员审核后，重新登录即可获得专家角色。',approved:'你的账号已具有专家角色，可以创建套餐和处理订单。',suspended:'目前不能创建套餐或接新单，请联系管理员。'}[status]||''},
    chooseCredential(){uni.chooseFile({count:1,extension:['.pdf'],success:({tempFiles})=>{const file=tempFiles[0];if(file.size>10*1024*1024){uni.showToast({title:'PDF不能超过10MB',icon:'none'});return}this.credentialPath=file.path;this.credentialName=file.name}})},
    async submit(){if(this.form.display_name.length<2||this.form.title.length<2||this.form.specialties.length<2||this.form.bio.length<20){uni.showToast({title:'请完整填写申请资料',icon:'none'});return}this.submitting=true;try{this.profile=await api.submitExpertApplication(this.form);if(this.credentialPath)this.profile=await api.uploadExpertCredential(this.credentialPath);uni.showToast({title:'申请已提交',icon:'success'})}catch(error){uni.showToast({title:error.message,icon:'none',duration:3000})}finally{this.submitting=false}},
    openWorkbench(){uni.navigateTo({url:'/pages/expert/workbench'})}
  }
}
</script>

<style scoped>
.apply-page{background:radial-gradient(circle at 100% 0,#e9e4ff 0,transparent 25%),#f5f7fb}.center{text-align:center;color:#8b94a5}.status-card{margin-top:28rpx;padding:35rpx;background:#fff;border-radius:29rpx;box-shadow:0 15rpx 42rpx rgba(36,55,86,.07)}.status-card.pending{border-top:8rpx solid #e4a63b}.status-card.approved{border-top:8rpx solid #29a675}.status-card.suspended{border-top:8rpx solid #d65b70}.status-title{font-size:34rpx;font-weight:850}.status-desc{margin-top:12rpx;color:#788297;font-size:23rpx;line-height:1.7}.review-note,.reject-note{margin-top:18rpx;padding:17rpx;color:#8a6330;background:#fff3dc;border-radius:15rpx;font-size:21rpx;line-height:1.6}.privacy-note{margin-top:22rpx;color:#6e7c91;background:#edf5f1;padding:18rpx;border-radius:16rpx;font-size:20rpx;line-height:1.6}
.file-row{display:flex;align-items:center;justify-content:space-between;margin-top:22rpx;padding:20rpx;background:#f3f4f8;border-radius:16rpx;font-size:22rpx}.file-row text{display:block;margin-top:5rpx;color:#939ba9;font-size:18rpx}.file-row>view:last-child{color:#6257e8;font-weight:750}
</style>
