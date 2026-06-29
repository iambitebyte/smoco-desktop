import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { Radio, Users, Podcast, type LucideIcon } from 'lucide-react'
import { Container, SectionHeader, Card } from '../ui'

const CASES: { key: string; icon: LucideIcon }[] = [
  { key: 'live', icon: Radio },
  { key: 'meeting', icon: Users },
  { key: 'podcast', icon: Podcast },
]

export default function UseCases() {
  const { t } = useTranslation()

  return (
    <section id="use-cases" className="py-24 scroll-mt-16">
      <Container>
        <SectionHeader
          eyebrow={t('useCases.eyebrow')}
          title={t('useCases.title')}
          description={t('useCases.description')}
        />

        <div className="grid md:grid-cols-3 gap-6">
          {CASES.map((c, idx) => {
            const Icon = c.icon
            // 取出步骤列表（i18next 不直接返回数组，用 t retourObjects）
            const steps = t(`useCases.cases.${c.key}.steps`, { returnObjects: true }) as string[]
            return (
              <motion.div
                key={c.key}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-80px' }}
                transition={{ duration: 0.4, delay: idx * 0.08 }}
              >
                <Card className="h-full">
                  <div className="flex items-center gap-3 mb-5">
                    <div className="w-9 h-9 rounded-md bg-brand-gradient-subtle border border-brand-500/30 flex items-center justify-center">
                      <Icon className="w-4 h-4 text-brand-300" />
                    </div>
                    <h3 className="text-base font-semibold">{t(`useCases.cases.${c.key}.title`)}</h3>
                  </div>

                  <ol className="space-y-3">
                    {steps.map((step, i) => (
                      <li key={i} className="flex gap-3 text-sm">
                        <span className="flex-shrink-0 w-5 h-5 rounded-full bg-bg-elevated border border-edge text-brand-300 flex items-center justify-center text-[10px] font-mono font-semibold">
                          {i + 1}
                        </span>
                        <span className="text-content-secondary leading-relaxed">{step}</span>
                      </li>
                    ))}
                  </ol>
                </Card>
              </motion.div>
            )
          })}
        </div>
      </Container>
    </section>
  )
}
