import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { Download } from 'lucide-react'
import { Container, Button, Tag } from '../ui'

export default function Hero() {
  const { t } = useTranslation()

  return (
    <section className="relative overflow-hidden">
      {/* 紫色光晕背景 */}
      <div
        aria-hidden
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(circle at 30% 20%, rgba(139, 92, 246, 0.25), transparent 60%), radial-gradient(circle at 70% 60%, rgba(99, 102, 241, 0.20), transparent 50%)',
        }}
      />

      <Container className="relative pt-24 pb-20 md:pt-32 md:pb-28 text-center">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="inline-flex mb-8"
        >
          <Tag dot>{t('hero.badge')}</Tag>
        </motion.div>

        {/* Title */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="text-5xl md:text-7xl font-bold tracking-tight mb-6 leading-[1.1]"
        >
          <span className="text-gradient">{t('hero.title')}</span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-lg md:text-xl text-content-secondary max-w-2xl mx-auto mb-10 leading-relaxed"
        >
          {t('hero.subtitle')}
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="flex flex-wrap items-center justify-center gap-4 mb-10"
        >
          <Button as="a" href="#download" size="lg">
            <Download className="w-4 h-4" />
            {t('hero.ctaPrimary')}
          </Button>
        </motion.div>

        {/* Tags */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="flex flex-wrap items-center justify-center gap-3 mb-16"
        >
          <Tag color="success" dot>
            {t('hero.tag1')}
          </Tag>
          <Tag color="brand" dot>
            {t('hero.tag2')}
          </Tag>
        </motion.div>

        {/* Screenshot */}
        <motion.div
          initial={{ opacity: 0, y: 40, rotate: 2 }}
          animate={{ opacity: 1, y: 0, rotate: 0 }}
          transition={{ duration: 0.7, delay: 0.5 }}
          className="relative mx-auto max-w-5xl"
        >
          <div
            aria-hidden
            className="absolute -inset-4 bg-brand-gradient-subtle rounded-2xl blur-2xl opacity-50"
          />
          <img
            src="/images/subscription.png"
            alt={t('hero.screenshotAlt')}
            className="relative rounded-xl border border-edge shadow-2xl w-full"
            loading="eager"
          />
        </motion.div>
      </Container>
    </section>
  )
}
