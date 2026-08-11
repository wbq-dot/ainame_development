import App from './App'
import { createSSRApp } from 'vue'
import { enforceAdminConsoleRoute } from './utils/auth'

export function createApp() {
  const app = createSSRApp(App)
  app.mixin({
    onShow() {
      enforceAdminConsoleRoute()
    }
  })
  return { app }
}
