import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { Download } from 'lucide-react'
import { Container, Button } from '../ui'

export default function DownloadCTA() {
  const { t } = useTranslation()

  return (
    <section id="download" className="py-24 scroll-mt-16">
      <Container>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.5 }}
          className="relative overflow-hidden rounded-2xl px-6 py-16 md:py-20 text-center"
        >
          {/* 紫色渐变背景 */}
          <div
            aria-hidden
            className="absolute inset-0 bg-brand-gradient opacity-90"
          />
          <div
            aria-hidden
            className="absolute inset-0"
            style={{
              background:
                'radial-gradient(circle at 20% 30%, rgba(255,255,255,0.15), transparent 50%), radial-gradient(circle at 80% 70%, rgba(255,255,255,0.10), transparent 50%)',
            }}
          />

          <div className="relative">
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-white/70 mb-4">
              {t('download.eyebrow')}
            </div>
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-4 tracking-tight">
              {t('download.title')}
            </h2>
            <p className="text-lg text-white/80 max-w-2xl mx-auto mb-10 leading-relaxed">
              {t('download.description')}
            </p>

            <div className="flex flex-wrap items-center justify-center gap-4 mb-8">
              <Button
                as="a"
                href="/download/smoco-desktop-1.1.0.zip"
                size="lg"
                className="bg-white text-brand-700 hover:bg-white/90 hover:scale-[1.02] shadow-2xl"
              >
                <Download className="w-4 h-4" />
                {t('download.ctaPrimary')}
              </Button>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-white/70">
              <span>{t('download.meta')}</span>
            </div>
          </div>
        </motion.div>
      </Container>
    </section>
  )
}
