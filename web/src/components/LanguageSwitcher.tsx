import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Globe, ChevronDown, Check } from 'lucide-react'

const LANGUAGES = [
  { code: 'zh', label: '简体中文' },
  { code: 'ja', label: '日本語' },
  { code: 'en', label: 'English' },
] as const

export default function LanguageSwitcher() {
  const { i18n, t } = useTranslation()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const current = LANGUAGES.find((l) => l.code === i18n.language) ?? LANGUAGES[0]

  // 点击外部关闭
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  // Esc 关闭
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-edge-subtle bg-bg-card text-content-secondary hover:text-content-primary hover:border-brand-500/50 transition-colors text-sm"
        aria-label={t('lang.switch')}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <Globe className="w-4 h-4" />
        <span>{current.label}</span>
        <ChevronDown
          className={`w-3 h-3 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div
          role="listbox"
          className="absolute right-0 mt-2 min-w-[9rem] rounded-md border border-edge-subtle bg-bg-card shadow-card overflow-hidden animate-fade-in"
        >
          {LANGUAGES.map((lang) => {
            const active = lang.code === current.code
            return (
              <button
                key={lang.code}
                role="option"
                aria-selected={active}
                onClick={() => {
                  i18n.changeLanguage(lang.code)
                  setOpen(false)
                }}
                className={`flex items-center justify-between w-full px-3 py-2 text-sm transition-colors ${
                  active
                    ? 'text-brand-400 bg-brand-500/5'
                    : 'text-content-secondary hover:text-content-primary hover:bg-bg-elevated'
                }`}
              >
                <span>{lang.label}</span>
                {active && <Check className="w-3.5 h-3.5" />}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
