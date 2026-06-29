import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { MonitorSmartphone, Keyboard, ShieldCheck, type LucideIcon } from 'lucide-react'
import { Container, SectionHeader, Card } from '../ui'

const ITEMS: { key: string; icon: LucideIcon }[] = [
  { key: 'browser', icon: MonitorSmartphone },
  { key: 'typing', icon: Keyboard },
  { key: 'privacy', icon: ShieldCheck },
]

export default function ProblemSolution() {
  const { t } = useTranslation()

  return (
    <section className="py-24">
      <Container>
        <SectionHeader
          eyebrow={t('problemSolution.eyebrow')}
          title={t('problemSolution.title')}
          description={t('problemSolution.description')}
        />

        <div className="grid md:grid-cols-3 gap-6">
          {ITEMS.map((item, idx) => {
            const Icon = item.icon
            return (
              <motion.div
                key={item.key}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-80px' }}
                transition={{ duration: 0.4, delay: idx * 0.08 }}
              >
                <Card className="h-full">
                  <div className="w-10 h-10 rounded-md bg-brand-gradient-subtle border border-brand-500/30 flex items-center justify-center mb-5">
                    <Icon className="w-5 h-5 text-brand-300" />
                  </div>
                  <h3 className="text-lg font-semibold mb-3">
                    {t(`problemSolution.items.${item.key}.title`)}
                  </h3>
                  <p className="text-sm text-content-secondary leading-relaxed">
                    {t(`problemSolution.items.${item.key}.desc`)}
                  </p>
                </Card>
              </motion.div>
            )
          })}
        </div>
      </Container>
    </section>
  )
}
