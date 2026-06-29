import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { Check, Clock, Sparkles } from 'lucide-react'
import { Container, SectionHeader, Tag } from '../ui'

const VERSIONS = [
  { key: 'current', status: 'done', tagColor: 'success' as const, Icon: Check },
  { key: 'next', status: 'next', tagColor: 'brand' as const, Icon: Clock },
  { key: 'future', status: 'future', tagColor: 'neutral' as const, Icon: Sparkles },
]

export default function RoadmapSection() {
  const { t } = useTranslation()

  return (
    <section id="roadmap" className="py-24 scroll-mt-16">
      <Container>
        <SectionHeader
          eyebrow={t('roadmap.eyebrow')}
          title={t('roadmap.title')}
          description={t('roadmap.description')}
        />

        <div className="grid md:grid-cols-3 gap-6">
          {VERSIONS.map((v, idx) => {
            const Icon = v.Icon
            const items = t(`roadmap.versions.${v.key}.items`, {
              returnObjects: true,
            }) as string[]

            return (
              <motion.div
                key={v.key}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-80px' }}
                transition={{ duration: 0.4, delay: idx * 0.1 }}
                className={`relative rounded-lg border p-6 ${
                  v.key === 'next'
                    ? 'border-brand-500/40 bg-brand-500/[0.03] shadow-glow'
                    : 'border-edge-subtle bg-bg-card'
                }`}
              >
                {v.key === 'next' && (
                  <div className="absolute -top-3 left-6">
                    <Tag color="brand" dot>
                                      Next up
                    </Tag>
                  </div>
                )}

                <div className="flex items-center gap-3 mb-4">
                  <div
                    className={`w-9 h-9 rounded-md flex items-center justify-center ${
                      v.key === 'next'
                        ? 'bg-brand-gradient-subtle border border-brand-500/40'
                        : 'bg-bg-elevated border border-edge'
                    }`}
                  >
                    <Icon
                      className={`w-4 h-4 ${
                        v.key === 'current'
                          ? 'text-emerald-400'
                          : v.key === 'next'
                            ? 'text-brand-300'
                            : 'text-content-muted'
                      }`}
                    />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold">{t(`roadmap.versions.${v.key}.title`)}</h3>
                    <p className="text-xs text-content-muted">{t(`roadmap.versions.${v.key}.status`)}</p>
                  </div>
                </div>

                <ul className="space-y-2.5 mt-5">
                  {items.map((item, i) => (
                    <li key={i} className="flex gap-2 text-sm">
                      <span
                        className={`flex-shrink-0 mt-1.5 w-1 h-1 rounded-full ${
                          v.key === 'current'
                            ? 'bg-emerald-400'
                            : v.key === 'next'
                              ? 'bg-brand-400'
                              : 'bg-content-muted'
                        }`}
                        aria-hidden
                      />
                      <span className="text-content-secondary leading-relaxed">{item}</span>
                    </li>
                  ))}
                </ul>
              </motion.div>
            )
          })}
        </div>
      </Container>
    </section>
  )
}
