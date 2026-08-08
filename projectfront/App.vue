<script>
import { applyDisplayPreferences } from './utils/preferences'

export default {
  onLaunch() {
    console.log('知名台前端已启动')
    applyDisplayPreferences()
  },
  onShow() {
    applyDisplayPreferences()
  }
}
</script>

<style>
page {
  min-height: 100%;
  color: #172033;
  background: #f5f7fb;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

view,
text,
input,
textarea,
button {
  box-sizing: border-box;
}

button::after {
  border: none;
}

.page-shell {
  min-height: 100vh;
  padding: 32rpx 28rpx 64rpx;
}

.page-title {
  margin: 8rpx 0 10rpx;
  font-size: 48rpx;
  font-weight: 800;
  letter-spacing: -1rpx;
}

.page-subtitle {
  color: #718096;
  font-size: 26rpx;
  line-height: 1.65;
}

.card {
  margin-top: 24rpx;
  padding: 30rpx;
  background: rgba(255, 255, 255, 0.96);
  border: 1rpx solid rgba(31, 55, 90, 0.06);
  border-radius: 28rpx;
  box-shadow: 0 16rpx 50rpx rgba(36, 55, 86, 0.07);
}

.card-title {
  font-size: 31rpx;
  font-weight: 750;
}

.card-note {
  margin-top: 8rpx;
  color: #8792a7;
  font-size: 24rpx;
  line-height: 1.6;
}

.field {
  margin-top: 26rpx;
}

.field-label {
  display: block;
  margin-bottom: 12rpx;
  color: #4c5870;
  font-size: 25rpx;
  font-weight: 650;
}

.field-input,
.field-textarea {
  width: 100%;
  padding: 0 24rpx;
  color: #182238;
  background: #f4f6fa;
  border: 2rpx solid transparent;
  border-radius: 20rpx;
  font-size: 28rpx;
}

.field-input {
  height: 92rpx;
}

.field-textarea {
  min-height: 190rpx;
  padding-top: 22rpx;
  line-height: 1.6;
}

.field-input:focus,
.field-textarea:focus {
  background: #fff;
  border-color: #7c6df2;
}

.primary-btn,
.secondary-btn,
.ghost-btn,
.danger-btn {
  height: 88rpx;
  border-radius: 22rpx;
  font-size: 28rpx;
  font-weight: 700;
  line-height: 88rpx;
}

.primary-btn {
  color: #fff;
  background: linear-gradient(135deg, #6257e8, #8a6df1);
  box-shadow: 0 14rpx 28rpx rgba(98, 87, 232, 0.22);
}

.secondary-btn {
  color: #4338ca;
  background: #ebe9ff;
}

.ghost-btn {
  color: #536079;
  background: #f2f4f8;
}

.danger-btn {
  color: #c2415b;
  background: #fff0f3;
}

.btn-gap {
  margin-top: 28rpx;
}

.button[disabled],
button[disabled] {
  opacity: 0.58;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
}

.chip {
  padding: 15rpx 24rpx;
  color: #667085;
  background: #f2f4f8;
  border-radius: 999rpx;
  font-size: 25rpx;
}

.chip.active {
  color: #fff;
  background: linear-gradient(135deg, #6257e8, #8a6df1);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 38rpx;
}

.section-title {
  font-size: 32rpx;
  font-weight: 760;
}

.muted {
  color: #8792a7;
}

.status-dot {
  width: 14rpx;
  height: 14rpx;
  border-radius: 50%;
}

.safe-bottom {
  height: env(safe-area-inset-bottom);
}

/* #ifdef H5 */
html.ainame-large-text {
  font-size: 18px;
}

html.ainame-high-contrast page {
  color: #0b1020;
}

html.ainame-reduce-motion *,
html.ainame-reduce-motion *::before,
html.ainame-reduce-motion *::after {
  scroll-behavior: auto !important;
  transition-duration: 0.01ms !important;
  animation-duration: 0.01ms !important;
}
/* #endif */
</style>
