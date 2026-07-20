import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { Download as DownloadIcon } from 'lucide-react'
import { Container, Card, Button, Tag, CodeBlock } from '../components/ui'
import SEO from '../components/SEO'

type VariantInfo = {
  badge: string
  version: string
  date: string
  platform: string
  size: string
  desc: string
  button: string
}

// v1.2.0 起提供完整版与 Lite 版
const VARIANTS = [
  { key: 'full', href: '/download/smoco-desktop-1.2.0.zip' },
  { key: 'lite', href: '/download/smoco-desktop-lite-1.2.0.zip' },
]

const ARCHIVES = [
  { version: 'v1.1.0', date: '2026-07-15', size: '~1.4 GB', href: '/download/smoco-desktop-1.1.0.zip' },
  { version: 'v1.0.1', date: '2026-07-06', size: '~1.45 GB', href: '/download/smoco-desktop-1.0.1.zip' },
  { version: 'v1.0.0', date: '2026-06-29', size: '~438 MB', href: '/download/smoco-desktop-1.0.0.zip' },
]

export default function Download() {
  const { t } = useTranslation()

  const installSteps = t('downloadPage.install.steps', { returnObjects: true }) as string[]

  const requirements = [
    { label: t('downloadPage.requirements.os'), value: t('downloadPage.requirements.osValue') },
    { label: t('downloadPage.requirements.cpu'), value: t('downloadPage.requirements.cpuValue') },
    { label: t('downloadPage.requirements.ram'), value: t('downloadPage.requirements.ramValue') },
    { label: t('downloadPage.requirements.disk'), value: t('downloadPage.requirements.diskValue') },
  ]

  return (
    <div className="pt-12 pb-24">
      <SEO titleKey="seo.download.title" descriptionKey="seo.download.description" />
      {/* Hero */}
      <Container className="text-center mb-16">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <div className="text-brand-400 text-xs font-semibold uppercase tracking-[0.2em] mb-4">
            {t('downloadPage.eyebrow')}
          </div>
          <h1 className="text-5xl md:text-6xl font-bold mb-4 tracking-tight">{t('downloadPage.title')}</h1>
          <p className="text-lg text-content-secondary">{t('downloadPage.subtitle')}</p>
        </motion.div>
      </Container>

      {/* 完整版 + Lite 版双卡 */}
      <Container size="lg" className="mb-16">
        <div className="grid gap-6 md:grid-cols-2">
          {VARIANTS.map((v, idx) => {
            const info = t(`downloadPage.variants.${v.key}`, { returnObjects: true }) as VariantInfo
            return (
              <motion.div
                key={v.key}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.1 * idx }}
              >
                <Card className="relative overflow-hidden p-8 md:p-10 h-full">
                  <div
                    aria-hidden
                    className="absolute inset-0 bg-brand-gradient-subtle opacity-50 pointer-events-none"
                  />
                  <div className="relative flex flex-col h-full">
                    <div className="flex items-center gap-3 mb-6">
                      <Tag color="success" dot>
                        {info.badge}
                      </Tag>
                      <span className="text-sm text-content-muted">{info.version} · {info.date}</span>
                    </div>

                    <h2 className="text-2xl font-bold mb-2">Smoco Desktop {info.version}</h2>
                    <p className="text-sm text-content-muted mb-4">{info.platform}</p>
                    <p className="text-content-secondary mb-8 flex-1">{info.desc}</p>

                    <Button as="a" href={v.href} size="lg" className="w-full sm:w-auto">
                      <DownloadIcon className="w-4 h-4" />
                      {info.button} · {info.size}
                    </Button>
                  </div>
                </Card>
              </motion.div>
            )
          })}
        </div>
      </Container>

      {/* 历史版本 */}
      <Container size="md" className="mb-16">
        <h3 className="text-xl font-semibold mb-6">{t('downloadPage.archives.title')}</h3>
        <Card>
          <ul className="divide-y divide-edge-subtle">
            {ARCHIVES.map((a) => (
              <li key={a.version} className="flex items-center justify-between py-4 first:pt-0 last:pb-0 gap-4">
                <div className="min-w-0">
                  <div className="font-medium">Smoco Desktop {a.version}</div>
                  <div className="text-xs text-content-muted">{a.date} · {a.size}</div>
                </div>
                <a href={a.href} className="flex-shrink-0 flex items-center gap-1.5 text-sm text-brand-300 hover:underline">
                  <DownloadIcon className="w-3.5 h-3.5" />
                  {t('downloadPage.archives.download')}
                </a>
              </li>
            ))}
          </ul>
        </Card>
        <p className="text-xs text-content-muted mt-3">{t('downloadPage.archives.note')}</p>
      </Container>

      {/* 系统要求 */}
      <Container size="md" className="mb-16">
        <h3 className="text-xl font-semibold mb-6">{t('downloadPage.requirements.title')}</h3>
        <Card>
          <dl className="divide-y divide-edge-subtle">
            {requirements.map((req) => (
              <div key={req.label} className="flex items-center justify-between py-3 first:pt-0 last:pb-0 gap-4">
                <dt className="text-sm text-content-muted">{req.label}</dt>
                <dd className="text-sm text-content-primary font-medium text-right">{req.value}</dd>
              </div>
            ))}
          </dl>
        </Card>
      </Container>

      {/* 安装步骤 */}
      <Container size="md" className="mb-16">
        <h3 className="text-xl font-semibold mb-6">{t('downloadPage.install.title')}</h3>
        <Card>
          <ol className="space-y-4">
            {installSteps.map((step, i) => (
              <li key={i} className="flex gap-4">
                <span className="flex-shrink-0 w-7 h-7 rounded-full bg-brand-gradient-subtle border border-brand-500/40 text-brand-300 flex items-center justify-center text-xs font-mono font-semibold">
                  {i + 1}
                </span>
                <span className="text-sm text-content-secondary leading-relaxed pt-0.5">{step}</span>
              </li>
            ))}
          </ol>
        </Card>
      </Container>

      {/* 校验 */}
      <Container size="md" className="mb-16">
        <h3 className="text-xl font-semibold mb-3">{t('downloadPage.verify.title')}</h3>
        <p className="text-sm text-content-secondary mb-4">{t('downloadPage.verify.desc')}</p>
        <CodeBlock language="powershell" code={t('downloadPage.verify.command')} />
      </Container>


    </div>
  )
}
