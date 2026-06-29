import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import zh from './zh.json'
import ja from './ja.json'
import en from './en.json'

const STORAGE_KEY = 'smoco-lang'
const SUPPORTED = ['zh', 'ja', 'en'] as const
type Lang = (typeof SUPPORTED)[number]

const detectLanguage = (): Lang => {
  // 优先 localStorage
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved && (SUPPORTED as readonly string[]).includes(saved)) {
    return saved as Lang
  }
  // 其次浏览器语言
  const browser = navigator.language.toLowerCase()
  if (browser.startsWith('ja')) return 'ja'
  if (browser.startsWith('en')) return 'en'
  return 'zh'
}

i18n.use(initReactI18next).init({
  resources: {
    zh: { translation: zh },
    ja: { translation: ja },
    en: { translation: en },
  },
  lng: detectLanguage(),
  fallbackLng: 'zh',
  interpolation: {
    escapeValue: false, // React 已经防 XSS
  },
})

// 持久化语言切换 + 同步 <html lang="">
i18n.on('languageChanged', (lng: string) => {
  localStorage.setItem(STORAGE_KEY, lng)
  document.documentElement.lang = lng === 'zh' ? 'zh-CN' : lng
})

// 初始化时也同步一次
document.documentElement.lang = i18n.language === 'zh' ? 'zh-CN' : i18n.language

export default i18n
