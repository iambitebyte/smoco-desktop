import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { Container, Card, Tag } from '../components/ui'
import SEO from '../components/SEO'

export default function Changelog() {
  const { t } = useTranslation()

  // 只读 v1.0.0 这一项（i18n key 限制）
  const versionKey = 'v1.0.0'
  const items = t(`changelogPage.versions.${versionKey}.items`, { returnObjects: true }) as string[]
  const version = t(`changelogPage.versions.${versionKey}.version`)
  const date = t(`changelogPage.versions.${versionKey}.date`)
  const tag = t(`changelogPage.versions.${versionKey}.tag`)

  return (
    <div className="pt-12 pb-24">
      <SEO titleKey="seo.changelog.title" descriptionKey="seo.changelog.description" />
      {/* Hero */}
      <Container className="text-center mb-16">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <div className="text-brand-400 text-xs font-semibold uppercase tracking-[0.2em] mb-4">
            {t('changelogPage.eyebrow')}
          </div>
          <h1 className="text-5xl md:text-6xl font-bold mb-4 tracking-tight">{t('changelogPage.title')}</h1>
          <p className="text-lg text-content-secondary">{t('changelogPage.subtitle')}</p>
        </motion.div>
      </Container>

      <Container size="md">
        {/* Timeline */}
        <div className="relative pl-8">
          {/* 竖线 */}
          <div
            aria-hidden
            className="absolute left-3 top-3 bottom-3 w-px bg-gradient-to-b from-brand-500/40 via-edge to-transparent"
          />

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="relative"
          >
            {/* 时间轴节点 */}
            <div className="absolute -left-[1.40rem] top-1 w-3 h-3 rounded-full bg-brand-500 ring-4 ring-brand-500/20" />

            <Tag color="success" dot className="mb-3">
              Latest
            </Tag>

            <Card className="mb-4">
              <div className="flex flex-wrap items-baseline gap-3 mb-1">
                <h2 className="text-2xl font-bold">{version}</h2>
                <span className="text-sm text-content-muted">· {date}</span>
              </div>
              <p className="text-sm text-brand-300 mb-5">{tag}</p>

              <ul className="space-y-2.5">
                {items.map((item, i) => (
                  <li key={i} className="flex gap-3 text-sm">
                    <span className="flex-shrink-0 mt-1.5 w-1.5 h-1.5 rounded-full bg-brand-400" />
                    <span className="text-content-secondary leading-relaxed">{item}</span>
                  </li>
                ))}
              </ul>
            </Card>
          </motion.div>

          {/* 后续占位 */}
          <div className="relative mt-8 opacity-50">
            <div className="absolute -left-[1.40rem] top-1 w-3 h-3 rounded-full bg-bg-elevated border border-edge" />
            <p className="text-sm text-content-muted pt-1">More versions coming soon...</p>
          </div>
        </div>


      </Container>
    </div>
  )
}
