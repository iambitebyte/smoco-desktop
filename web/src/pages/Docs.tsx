import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import {
  BookOpen,
  Sparkles,
  Keyboard,
  Database,
  Package,
  type LucideIcon,
} from 'lucide-react'
import { Container, Card } from '../components/ui'
import SEO from '../components/SEO'
import clsx from 'clsx'

type SectionKey = 'overview' | 'features' | 'shortcuts' | 'data' | 'build'

const SECTIONS: { key: SectionKey; icon: LucideIcon }[] = [
  { key: 'overview', icon: BookOpen },
  { key: 'features', icon: Sparkles },
  { key: 'shortcuts', icon: Keyboard },
  { key: 'data', icon: Database },
  { key: 'build', icon: Package },
]

export default function Docs() {
  const { t } = useTranslation()
  const [active, setActive] = useState<SectionKey>('overview')

  const featureItems = t('docsPage.sections.features.items', { returnObjects: true }) as string[]
  const dataItems = t('docsPage.sections.data.items', { returnObjects: true }) as string[]
  const shortcutTable = t('docsPage.sections.shortcuts.table', {
    returnObjects: true,
  }) as { page: string; key: string; action: string }[]

  return (
    <div className="pt-12 pb-24">
      <SEO titleKey="seo.docs.title" descriptionKey="seo.docs.description" />
      {/* Hero */}
      <Container className="text-center mb-16">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <div className="text-brand-400 text-xs font-semibold uppercase tracking-[0.2em] mb-4">
            {t('docsPage.eyebrow')}
          </div>
          <h1 className="text-5xl md:text-6xl font-bold mb-4 tracking-tight">{t('docsPage.title')}</h1>
          <p className="text-lg text-content-secondary">{t('docsPage.subtitle')}</p>
        </motion.div>
      </Container>

      <Container size="lg">
        <div className="grid md:grid-cols-[200px_1fr] gap-8">
          {/* 侧边栏 */}
          <aside>
            <nav className="md:sticky md:top-24 space-y-1">
              {SECTIONS.map((section) => {
                const Icon = section.icon
                const isActive = active === section.key
                return (
                  <button
                    key={section.key}
                    onClick={() => setActive(section.key)}
                    className={clsx(
                      'w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors',
                      isActive
                        ? 'bg-brand-500/10 text-brand-300 border border-brand-500/30'
                        : 'text-content-secondary hover:text-content-primary hover:bg-bg-card border border-transparent',
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    {t(`docsPage.sections.${section.key}.title`)}
                  </button>
                )
              })}
            </nav>
          </aside>

          {/* 内容区 */}
          <div className="min-w-0">
            {/* Overview */}
            {active === 'overview' && (
              <article>
                <h2 className="text-2xl font-bold mb-4">{t('docsPage.sections.overview.title')}</h2>
                <p className="text-content-secondary leading-relaxed">{t('docsPage.sections.overview.content')}</p>
              </article>
            )}

            {/* Features */}
            {active === 'features' && (
              <article>
                <h2 className="text-2xl font-bold mb-6">{t('docsPage.sections.features.title')}</h2>
                <ul className="space-y-3">
                  {featureItems.map((item, i) => (
                    <li key={i} className="flex gap-3">
                      <span className="flex-shrink-0 mt-1.5 w-1.5 h-1.5 rounded-full bg-brand-400" />
                      <span className="text-content-secondary leading-relaxed">{item}</span>
                    </li>
                  ))}
                </ul>
              </article>
            )}

            {/* Shortcuts */}
            {active === 'shortcuts' && (
              <article>
                <h2 className="text-2xl font-bold mb-6">{t('docsPage.sections.shortcuts.title')}</h2>
                <Card className="overflow-hidden p-0">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-edge-subtle bg-bg-elevated/50">
                        <th className="text-left px-4 py-3 font-semibold text-content-muted text-xs uppercase tracking-wider">
                          Page
                        </th>
                        <th className="text-left px-4 py-3 font-semibold text-content-muted text-xs uppercase tracking-wider">
                          Key
                        </th>
                        <th className="text-left px-4 py-3 font-semibold text-content-muted text-xs uppercase tracking-wider">
                          Action
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {shortcutTable.map((row, i) => (
                        <tr key={i} className="border-b border-edge-subtle last:border-b-0">
                          <td className="px-4 py-3 text-content-secondary">{row.page}</td>
                          <td className="px-4 py-3">
                            <kbd className="font-mono text-xs px-2 py-1 rounded bg-bg-elevated border border-edge text-brand-300">
                              {row.key}
                            </kbd>
                          </td>
                          <td className="px-4 py-3 text-content-secondary">{row.action}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Card>
              </article>
            )}

            {/* Data */}
            {active === 'data' && (
              <article>
                <h2 className="text-2xl font-bold mb-4">{t('docsPage.sections.data.title')}</h2>
                <p className="text-content-secondary mb-4 leading-relaxed">
                  {t('docsPage.sections.data.content')}
                </p>
                <ul className="space-y-3">
                  {dataItems.map((item, i) => (
                    <li key={i} className="flex gap-3">
                      <span className="flex-shrink-0 mt-1.5 w-1.5 h-1.5 rounded-full bg-brand-400" />
                      <code className="font-mono text-sm text-content-primary">{item}</code>
                    </li>
                  ))}
                </ul>
              </article>
            )}

            {/* Build */}
            {active === 'build' && (
              <article>
                <h2 className="text-2xl font-bold mb-4">{t('docsPage.sections.build.title')}</h2>
                <p className="text-content-secondary leading-relaxed">
                  {t('docsPage.sections.build.content')}
                </p>
              </article>
            )}
          </div>
        </div>
      </Container>
    </div>
  )
}
