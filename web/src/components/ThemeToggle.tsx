import { useEffect, useState } from 'react'
import { Sun, Moon } from 'lucide-react'
import { toggleTheme, type Theme } from '../lib/theme'
import { useTranslation } from 'react-i18next'

export default function ThemeToggle() {
  const { t } = useTranslation()
  const [theme, setTheme] = useState<Theme>('dark')

  // 从 <html> class 同步初始状态
  useEffect(() => {
    setTheme(document.documentElement.classList.contains('light') ? 'light' : 'dark')
  }, [])

  const handleToggle = () => {
    const next = toggleTheme()
    setTheme(next)
  }

  const isLight = theme === 'light'

  return (
    <button
      onClick={handleToggle}
      className="flex items-center justify-center w-8 h-8 rounded-md text-content-secondary hover:text-content-primary hover:bg-bg-card transition-colors"
      aria-label={t('theme.toggle', { defaultValue: 'Toggle theme' })}
      title={t('theme.toggle', { defaultValue: 'Toggle theme' })}
    >
      {isLight ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
    </button>
  )
}
