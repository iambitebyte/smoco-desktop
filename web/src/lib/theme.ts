/**
 * 主题管理：light / dark
 *
 * 用 <html class="dark"> 或 <html class="light"> 切换。
 * 防闪烁：index.html 里 inline 一段脚本，在 React 加载前就设置好 class。
 * 这里仅负责 React 层的状态同步 + 持久化。
 */

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'smoco-theme'

export function getStoredTheme(): Theme | null {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved === 'light' || saved === 'dark') return saved
  return null
}

export function getPreferredTheme(): Theme {
  const stored = getStoredTheme()
  if (stored) return stored
  // 跟随系统
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

export function applyTheme(theme: Theme) {
  const root = document.documentElement
  root.classList.remove('light', 'dark')
  root.classList.add(theme)
  localStorage.setItem(STORAGE_KEY, theme)
}

/** 在应用启动时调用，确保 <html> class 跟持久化偏好一致 */
export function initTheme() {
  applyTheme(getPreferredTheme())
}

/** 切换主题（在 light / dark 之间） */
export function toggleTheme(): Theme {
  const current = document.documentElement.classList.contains('light') ? 'light' : 'dark'
  const next: Theme = current === 'light' ? 'dark' : 'light'
  applyTheme(next)
  return next
}
