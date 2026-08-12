<template>
  <view class="console">
    <view class="top"><view><text>DEVELOPER CONSOLE</text><view>{{ developer ? developer.name : '开放平台' }}</view><small>{{ developer ? developer.email : '' }}</small></view><button @click="logout">退出</button></view>
    <scroll-view scroll-x class="nav"><view v-for="item in nav" :key="item.key" :class="{ active: section===item.key }" @click="change(item.key)">{{ item.label }}</view></scroll-view>

    <template v-if="section==='overview'">
      <view class="metric-grid"><view><small>可用次数</small><b>{{ wallet.available || 0 }}</b><text>预占 {{ wallet.reserved || 0 }}</text></view><view><small>推广余额</small><b>¥{{ wallet.promotion_balance || 0 }}</b><text>仅抵扣 API 套餐</text></view><view><small>近7日调用</small><b>{{ stats.total || 0 }}</b><text>成功率 {{ stats.success_rate || 0 }}%</text></view></view>
      <view class="panel"><view class="panel-title">快速开始</view><view class="code">curl -X POST /openapi/v1/names/generate<br/>-H "X-API-Key: YOUR_KEY"<br/>-H "Idempotency-Key: unique-request-id"</view><view class="note">Key 明文只在创建或重新生成时显示一次；收费请求必须使用唯一幂等键。</view></view>
    </template>

    <template v-if="section==='keys'">
      <view class="panel"><view class="panel-head"><view class="panel-title">API Key</view><button @click="createKey">创建 Key</button></view><view v-if="!keys.length" class="empty">暂无 API Key</view><view v-for="key in keys" :key="key.id" class="row"><view><b>{{ key.name }}</b><small>{{ key.key_prefix }}•••• · {{ key.status }}</small><small>最后调用 {{ format(key.last_used_at) }}</small></view><view><button @click="renameKey(key)">改名</button><button class="danger" @click="revokeKey(key)">吊销</button><button @click="regenerateKey(key)">重新生成</button></view></view></view>
    </template>

    <template v-if="section==='debug'">
      <view class="panel"><view class="panel-title">在线调试</view><input v-model.trim="debug.apiKey" password placeholder="粘贴 API Key（不会保存）" /><picker :range="categories" @change="debug.category=categories[$event.detail.value]"><view class="picker">类别：{{ debug.category }}</view></picker><input v-model.trim="debug.surname" placeholder="姓氏（人名必填）" /><textarea v-model.trim="debug.other" placeholder="命名要求" /><button class="primary" :loading="loading" @click="runDebug">发送一次命名请求</button><view v-if="debugResult" class="result">{{ debugResult }}</view></view>
    </template>

    <template v-if="section==='batch'">
      <view class="panel"><view class="panel-title">批量命名（最多100条）</view><input v-model.trim="batchApiKey" password placeholder="粘贴 API Key（不会保存）" /><textarea v-model="batchText" placeholder="每行一条要求，例如：张|女|温柔大方" /><button class="primary" :loading="loading" @click="createBatch">创建批量任务</button><view class="note">格式：姓氏|性别|其它要求。任务按成功条目扣费，失败条目自动退回。</view></view>
    </template>

    <template v-if="section==='tasks'">
      <view class="panel"><view class="panel-head"><view class="panel-title">任务中心</view><button @click="loadTasks">刷新</button></view><view v-if="!tasks.length" class="empty">暂无任务</view><view v-for="task in tasks" :key="task.task_no" class="row" @click="showTask(task)"><view><b>{{ task.task_type }}</b><small>{{ task.task_no }}</small></view><view><text class="badge">{{ task.status }}</text><small>{{ task.success_count }}/{{ task.total_count }} 成功</small></view></view></view>
    </template>

    <template v-if="section==='billing'">
      <view class="panel"><view class="panel-title">API 套餐</view><view v-if="!packages.length" class="empty">暂无已上架套餐</view><view v-for="item in packages" :key="item.id" class="row"><view><b>{{ item.name }}</b><small>{{ item.credit_count }} 次 · ¥{{ item.price }}</small></view><button @click="buy(item)">购买</button></view></view>
      <view class="panel"><view class="panel-title">订单与退款</view><view v-for="order in orders" :key="order.order_no" class="row"><view><b>{{ order.package_name }}</b><small>{{ order.order_no }}</small><small>现金 ¥{{ order.cash_amount }} / 抵扣 ¥{{ order.promotion_amount }}</small></view><view><text class="badge">{{ order.status }}</text><button v-if="order.status==='pending'" @click="refreshOrder(order)">查单</button><button v-if="order.status==='paid'" @click="refund(order)">申请退款</button></view></view></view>
    </template>

    <template v-if="section==='growth'">
      <view class="metric-grid"><view><small>推广码</small><b class="code-value">{{ growth.referral_code || '—' }}</b><button @click="copyCode">复制</button></view><view><small>已邀请</small><b>{{ growth.invited_count || 0 }}</b><text>位开发者</text></view><view><small>待结算 / 已结算</small><b>{{ growth.pending_count || 0 }} / {{ growth.settled_count || 0 }}</b><text>退款期后到账</text></view></view><view class="panel"><view class="panel-title">佣金流水</view><view v-if="!(growth.logs||[]).length" class="empty">暂无佣金记录</view><view v-for="log in growth.logs" :key="log.id" class="row"><view><b>{{ log.type }}</b><small>{{ format(log.created_at) }}</small></view><b>¥{{ log.amount }}</b></view></view>
    </template>

    <template v-if="section==='settings'">
      <view class="panel"><view class="panel-title">修改密码</view><input v-model="password.current_password" password placeholder="当前密码"/><input v-model="password.new_password" password placeholder="新密码（至少8位）"/><button class="primary" @click="changePassword">修改并退出所有开发者登录</button></view>
    </template>
  </view>
</template>
<script>
import { developerApi } from '../../api/developer'
import { clearDeveloperLogin, getDeveloperAccess, getDeveloper, setDeveloper } from '../../utils/developer-auth'
export default {
  data() { return { section:'overview', developer:null, loading:false, wallet:{},stats:{},keys:[],tasks:[],packages:[],orders:[],growth:{},categories:['人名','企业名','宠物名'],debug:{apiKey:'',category:'人名',surname:'',other:''},debugResult:'',batchApiKey:'',batchText:'',password:{current_password:'',new_password:''},nav:[{key:'overview',label:'概览'},{key:'keys',label:'API Key'},{key:'debug',label:'在线调试'},{key:'batch',label:'批量命名'},{key:'tasks',label:'任务中心'},{key:'billing',label:'套餐订单'},{key:'growth',label:'邀请推广'},{key:'settings',label:'设置'}] } },
  onLoad(options){if(options&&options.section)this.section=options.section},
  onShow(){ if(!getDeveloperAccess()){uni.reLaunch({url:'/pages/developer/login'});return} this.developer=getDeveloper();this.loadOverview();if(this.section==='billing')this.loadBilling() },
  methods:{
    async loadOverview(){try{this.developer=await developerApi.me();setDeveloper(this.developer);[this.wallet,this.stats]=await Promise.all([developerApi.wallet(),developerApi.stats(7)])}catch(e){this.fail(e)}},
    change(key){this.section=key;if(key==='keys')this.loadKeys();if(key==='tasks')this.loadTasks();if(key==='billing')this.loadBilling();if(key==='growth')this.loadGrowth()},
    async loadKeys(){try{this.keys=await developerApi.keys()}catch(e){this.fail(e)}},async loadTasks(){try{this.tasks=(await developerApi.tasks()).items}catch(e){this.fail(e)}},
    async loadBilling(){try{[this.packages,this.orders]=await Promise.all([developerApi.packages(),developerApi.orders()])}catch(e){this.fail(e)}},async loadGrowth(){try{this.growth=await developerApi.growth()}catch(e){this.fail(e)}},
    createKey(){uni.showModal({title:'创建 API Key',editable:true,placeholderText:'Key 名称',success:async({confirm,content})=>{if(confirm&&content){try{this.showSecret(await developerApi.createKey(content))}catch(e){this.fail(e)}}}})},
    renameKey(key){uni.showModal({title:'重命名 Key',editable:true,content:key.name,success:async({confirm,content})=>{if(confirm&&content){await developerApi.renameKey(key.id,content);this.loadKeys()}}})},
    revokeKey(key){uni.showModal({title:'确认吊销 API Key',content:`准确动作：立即停用 ${key.key_prefix}，现有调用将失败且不可恢复。`,success:async({confirm})=>{if(confirm){await developerApi.revokeKey(key.id);this.loadKeys()}}})},
    regenerateKey(key){uni.showModal({title:'确认重新生成',content:'准确动作：吊销旧 Key，并创建一个只显示一次的新 Key。',success:async({confirm})=>{if(confirm)this.showSecret(await developerApi.regenerateKey(key.id))}})},
    showSecret(data){uni.showModal({title:'请立即保存 API Key',content:`${data.api_key}\n\n关闭后无法再次查看。`,confirmText:'复制',success:({confirm})=>{if(confirm)uni.setClipboardData({data:data.api_key})}});this.loadKeys()},
    async runDebug(){this.loading=true;try{const data=await developerApi.debugName({category:this.debug.category,surname:this.debug.surname,gender:'不限',length:'不限',other:this.debug.other,exclude:[]},this.debug.apiKey,`debug-${Date.now()}`);this.debugResult=JSON.stringify(data,null,2);this.loadOverview()}catch(e){this.fail(e)}finally{this.loading=false}},
    async createBatch(){const lines=this.batchText.split(/\r?\n/).map(v=>v.trim()).filter(Boolean);if(!lines.length)return this.fail(new Error('请至少输入一条'));const items=lines.map(line=>{const [surname='',gender='不限',other='']=line.split('|');return{category:'人名',surname,gender:['男','女'].includes(gender)?gender:'不限',length:'不限',other,exclude:[]}});this.loading=true;try{const data=await developerApi.batch(items,this.batchApiKey,`batch-${Date.now()}`);uni.showModal({title:'任务已创建',content:`任务编号：${data.task_id}\n状态：${data.status}`,showCancel:false});this.section='tasks';this.loadTasks()}catch(e){this.fail(e)}finally{this.loading=false}},
    showTask(task){developerApi.task(task.task_no).then(data=>uni.showModal({title:`任务 ${data.status}`,content:`成功 ${data.success_count}，失败 ${data.failure_count}\n${data.last_error||'暂无错误'}`,showCancel:false})).catch(this.fail)},
    buy(item){uni.showModal({title:'确认创建订单',content:`准确动作：购买 ${item.credit_count} 次 API 调用，价格 ¥${item.price}；默认使用推广余额抵扣，现金部分进入支付宝。`,success:async({confirm})=>{if(confirm){try{const order=await developerApi.createOrder({package_id:item.id,use_promotion_balance:true});if(order.pay_url)uni.showModal({title:'订单已创建',content:`现金支付 ¥${order.cash_amount}`,confirmText:'打开支付宝',success:({confirm})=>{if(confirm)this.openPay(order.pay_url)}});else uni.showToast({title:'余额抵扣成功',icon:'success'});this.loadBilling()}catch(e){this.fail(e)}}}})},
    openPay(url){
      // #ifdef H5
      window.location.href=url
      // #endif
      // #ifndef H5
      uni.setClipboardData({data:url,success:()=>uni.showModal({title:'支付链接已复制',content:'请在浏览器打开链接完成支付，返回后点击订单“查单”。',showCancel:false})})
      // #endif
    },
    refund(order){uni.showModal({title:'申请整单退款',editable:true,placeholderText:'退款原因',content:'将回收本套餐全部未使用次数；现金原路退回，推广余额恢复。',success:async({confirm,content})=>{if(confirm&&content){try{await developerApi.refund(order.order_no,content);uni.showToast({title:'申请已提交',icon:'success'});this.loadBilling()}catch(e){this.fail(e)}}}})},
    async refreshOrder(order){try{await developerApi.refreshOrder(order.order_no);this.loadBilling()}catch(e){this.fail(e)}},
    copyCode(){uni.setClipboardData({data:this.growth.referral_code||''})},async changePassword(){try{await developerApi.password(this.password);this.logout()}catch(e){this.fail(e)}},
    logout(){clearDeveloperLogin();uni.reLaunch({url:'/pages/developer/login'})},format(v){return v?String(v).replace('T',' ').slice(0,16):'从未'},fail(e){uni.showToast({title:e.message||String(e),icon:'none',duration:3000})}
  }
}
</script>
<style scoped>
.console{min-height:100vh;padding:28rpx;background:#f1f5f7}.top{display:flex;justify-content:space-between;padding:34rpx;color:#fff;background:linear-gradient(135deg,#092d42,#0d6b70);border-radius:28rpx}.top text{color:#62ddd0;font-size:16rpx;letter-spacing:4rpx}.top view view{margin-top:12rpx;font-size:36rpx;font-weight:900}.top small{display:block;margin-top:7rpx;color:#b5d2d6}.top button{height:65rpx;color:#d8f4f2;background:#ffffff18;font-size:21rpx;line-height:65rpx}.nav{margin:20rpx 0;white-space:nowrap}.nav view{display:inline-block;margin-right:10rpx;padding:17rpx 25rpx;color:#657481;background:#fff;border-radius:15rpx}.nav .active{color:#fff;background:#0a5967;font-weight:800}.metric-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:15rpx}.metric-grid>view{padding:25rpx;background:#fff;border-radius:22rpx}.metric-grid small,.metric-grid text,.row small{display:block;color:#86929d;font-size:19rpx}.metric-grid b{display:block;margin:11rpx 0;font-size:34rpx}.metric-grid button{font-size:20rpx}.panel{margin-top:18rpx;padding:27rpx;background:#fff;border-radius:24rpx}.panel-title{font-size:29rpx;font-weight:850}.panel-head,.row{display:flex;align-items:center;justify-content:space-between}.panel-head button,.row button{margin-left:10rpx;color:#0a5967;background:#e3f4f2;font-size:20rpx}.row{padding:22rpx 0;border-bottom:1rpx solid #edf0f2}.row:last-child{border-bottom:0}.row b{font-size:23rpx}.row small{margin-top:6rpx}.row .danger{color:#b74359;background:#fff0f3}.empty,.note{padding:30rpx 0;color:#86929d;text-align:center;font-size:22rpx}.code,.result{margin-top:20rpx;padding:22rpx;overflow:auto;color:#ccebe7;background:#102d38;border-radius:16rpx;font-family:monospace;font-size:20rpx;white-space:pre-wrap}.result{max-height:500rpx;text-align:left}input,.picker,textarea{width:100%;margin-top:18rpx;padding:21rpx;background:#f1f5f6;border-radius:15rpx;font-size:23rpx}.picker{height:78rpx}textarea{height:180rpx}.primary{margin-top:20rpx;color:#fff;background:#0a5967}.badge{display:block;padding:7rpx 12rpx;color:#0a5967;background:#e2f4f1;border-radius:99rpx;font-size:18rpx}.code-value{font-size:23rpx!important}@media(max-width:600px){.metric-grid{grid-template-columns:1fr}.top{align-items:flex-start}.row{gap:15rpx}}
</style>
