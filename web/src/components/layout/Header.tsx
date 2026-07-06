import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Container } from '../ui'
import LanguageSwitcher from '../LanguageSwitcher'
import { Menu, X } from 'lucide-react'
import clsx from 'clsx'
import { useTranslation } from 'react-i18next'
import ThemeToggle from '../ThemeToggle'

export default function Header() {
  const { t } = useTranslation()
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // 切路由时关移动菜单
  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  const NAV_ITEMS = [
    { label: t('nav.features'), href: '/#features' },
    { label: t('nav.useCases'), href: '/#use-cases' },
    { label: t('nav.download'), to: '/download' },
    { label: t('nav.docs'), to: '/docs' },
    { label: t('nav.changelog'), to: '/changelog' },
  ]

  return (
    <header
      className={clsx(
        'sticky top-0 z-50 transition-all duration-300',
        scrolled || mobileOpen
          ? 'bg-bg-primary/80 backdrop-blur-lg border-b border-edge-subtle'
          : 'bg-transparent border-b border-transparent',
      )}
    >
      <Container className="flex items-center justify-between h-16">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 font-semibold">
          <img
            src="/images/smoco_logo.png"
            alt="Smoco Desktop"
            className="w-7 h-7 rounded-full"
          />
          <span className="hidden sm:inline">Smoco Desktop</span>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-7">
          {NAV_ITEMS.map((item) =>
            item.to ? (
              <Link
                key={item.to}
                to={item.to}
                className={clsx(
                  'text-sm transition-colors',
                  location.pathname === item.to
                    ? 'text-content-primary'
                    : 'text-content-secondary hover:text-content-primary',
                )}
              >
                {item.label}
              </Link>
            ) : (
              <a
                key={item.href}
                href={item.href}
                className="text-sm text-content-secondary hover:text-content-primary transition-colors"
              >
                {item.label}
              </a>
            ),
          )}
        </nav>

        {/* Right actions */}
        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          <ThemeToggle />
          <button
            onClick={() => setMobileOpen((v) => !v)}
            className="md:hidden flex items-center justify-center w-8 h-8 rounded-md text-content-secondary hover:text-content-primary"
            aria-label="Menu"
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </Container>

      {/* Mobile nav */}
      {mobileOpen && (
        <div className="md:hidden border-t border-edge-subtle bg-bg-primary/95 backdrop-blur-lg">
          <Container className="py-4 flex flex-col gap-1">
            {NAV_ITEMS.map((item) =>
              item.to ? (
                <Link
                  key={item.to}
                  to={item.to}
                  className="text-content-secondary hover:text-content-primary py-2 text-sm"
                >
                  {item.label}
                </Link>
              ) : (
                <a
                  key={item.href}
                  href={item.href}
                  className="text-content-secondary hover:text-content-primary py-2 text-sm"
                >
                  {item.label}
                </a>
              ),
            )}
          </Container>
        </div>
      )}
    </header>
  )
}
