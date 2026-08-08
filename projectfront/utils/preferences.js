const PREFERENCES_KEY = 'ainame_display_preferences'

export function getDisplayPreferences() {
  const value = uni.getStorageSync(PREFERENCES_KEY)
  return {
    fontSize: value && value.fontSize === 'large' ? 'large' : 'standard',
    highContrast: Boolean(value && value.highContrast),
    reduceMotion: Boolean(value && value.reduceMotion)
  }
}

export function saveDisplayPreferences(preferences) {
  uni.setStorageSync(PREFERENCES_KEY, preferences)
  applyDisplayPreferences(preferences)
}

export function applyDisplayPreferences(input) {
  const preferences = input || getDisplayPreferences()
  // #ifdef H5
  document.documentElement.classList.toggle('ainame-large-text', preferences.fontSize === 'large')
  document.documentElement.classList.toggle('ainame-high-contrast', preferences.highContrast)
  document.documentElement.classList.toggle('ainame-reduce-motion', preferences.reduceMotion)
  // #endif
  uni.setTabBarStyle({
    color: preferences.highContrast ? '#4b5563' : '#8a93a6',
    selectedColor: preferences.highContrast ? '#3429a3' : '#6257e8',
    backgroundColor: '#ffffff'
  })
}
