import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { Container, SectionHeader } from '../ui'

interface Shot {
  src: string
  captionKey: string
}

const SHOTS: Shot[] = [
  { src: '/images/main.png', captionKey: 'gallery.captions.home' },
  { src: '/images/subscription.png', captionKey: 'gallery.captions.startup' },
  { src: '/images/transcription-history.png', captionKey: 'gallery.captions.history' },
  { src: '/images/setting-local-whisper.png', captionKey: 'gallery.captions.settings' },
]

export default function Gallery() {
  const { t } = useTranslation()

  return (
    <section className="py-24">
      <Container>
        <SectionHeader
          eyebrow={t('gallery.eyebrow')}
          title={t('gallery.title')}
          description={t('gallery.description')}
        />

        <div className="grid md:grid-cols-2 gap-6">
          {SHOTS.map((shot, idx) => (
            <motion.figure
              key={shot.src}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-80px' }}
              transition={{ duration: 0.4, delay: (idx % 2) * 0.1 }}
              className="group relative"
            >
              <div className="relative overflow-hidden rounded-lg border border-edge-subtle bg-bg-card">
                <div className="aspect-[4/3] overflow-hidden">
                  <img
                    src={shot.src}
                    alt={t(shot.captionKey, { defaultValue: shot.src })}
                    loading="lazy"
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-[1.02]"
                  />
                </div>
              </div>
              <figcaption className="mt-3 text-center text-xs text-content-muted">
                {t(shot.captionKey, { defaultValue: '' })}
              </figcaption>
            </motion.figure>
          ))}
        </div>
      </Container>
    </section>
  )
}
