import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import {
  Mic,
  Languages,
  Cpu,
  AudioLines,
  History,
  Keyboard,
  type LucideIcon,
} from 'lucide-react'
import { Container, SectionHeader, Card } from '../ui'

const ITEMS: { key: string; icon: LucideIcon }[] = [
  { key: 'transcription', icon: Mic },
  { key: 'translation', icon: Languages },
  { key: 'local', icon: Cpu },
  { key: 'vad', icon: AudioLines },
  { key: 'history', icon: History },
  { key: 'shortcuts', icon: Keyboard },
]

export default function Features() {
  const { t } = useTranslation()

  return (
    <section id="features" className="py-24 scroll-mt-16">
      <Container>
        <SectionHeader
          eyebrow={t('features.eyebrow')}
          title={t('features.title')}
          description={t('features.description')}
        />

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {ITEMS.map((item, idx) => {
            const Icon = item.icon
            return (
              <motion.div
                key={item.key}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-80px' }}
                transition={{ duration: 0.4, delay: (idx % 3) * 0.08 }}
              >
                <Card className="h-full group">
                  <div className="w-10 h-10 rounded-md bg-brand-gradient-subtle border border-brand-500/30 flex items-center justify-center mb-5 transition-colors group-hover:border-brand-500/60">
                    <Icon className="w-5 h-5 text-brand-300" />
                  </div>
                  <h3 className="text-lg font-semibold mb-2">{t(`features.items.${item.key}.title`)}</h3>
                  <p className="text-sm text-content-secondary leading-relaxed">
                    {t(`features.items.${item.key}.desc`)}
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
