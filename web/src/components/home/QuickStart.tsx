import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { Download, FolderArchive, MousePointerClick, Settings2, Play } from 'lucide-react'
import { Container, SectionHeader } from '../ui'

const STEPS = [
  { key: 'download', icon: Download },
  { key: 'extract', icon: FolderArchive },
  { key: 'run', icon: MousePointerClick },
  { key: 'whisper', icon: Settings2 },
  { key: 'transcribe', icon: Play },
] as const

export default function QuickStart() {
  const { t } = useTranslation()

  return (
    <section className="py-24">
      <Container size="lg">
        <SectionHeader
          eyebrow={t('quickStart.eyebrow')}
          title={t('quickStart.title')}
          description={t('quickStart.description')}
        />

        <div className="relative">
          {/* 连接线（桌面端横线） */}
          <div
            aria-hidden
            className="hidden md:block absolute top-7 left-[10%] right-[10%] h-px bg-gradient-to-r from-transparent via-edge to-transparent"
          />

          <div className="grid grid-cols-2 md:grid-cols-5 gap-6 md:gap-3">
            {STEPS.map((step, idx) => {
              const Icon = step.icon
              return (
                <motion.div
                  key={step.key}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-60px' }}
                  transition={{ duration: 0.4, delay: idx * 0.08 }}
                  className="relative flex flex-col items-center text-center"
                >
                  {/* 步骤序号 */}
                  <div className="text-[10px] font-mono text-brand-400 mb-2">STEP {idx + 1}</div>

                  {/* 图标圆 */}
                  <div className="relative mb-4">
                    <div className="w-14 h-14 rounded-full bg-bg-card border border-edge flex items-center justify-center shadow-card">
                      <Icon className="w-5 h-5 text-brand-300" />
                    </div>
                  </div>

                  <h3 className="text-sm font-semibold mb-1">{t(`quickStart.steps.${step.key}.title`)}</h3>
                  <p className="text-xs text-content-muted leading-relaxed max-w-[12ch]">
                    {t(`quickStart.steps.${step.key}.desc`)}
                  </p>
                </motion.div>
              )
            })}
          </div>
        </div>

        <p className="mt-12 text-center text-xs text-content-muted">{t('quickStart.footnote')}</p>
      </Container>
    </section>
  )
}
