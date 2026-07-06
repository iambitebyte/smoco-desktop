import { Container } from '../ui'

interface FooterColumn {
  title: string
  links: { label: string; href: string; external?: boolean }[]
}

const FOOTER_COLS: FooterColumn[] = [
  {
    title: '产品',
    links: [
      { label: '下载', href: '#download' },
      { label: '功能', href: '#features' },
      { label: '路线图', href: '#roadmap' },
    ],
  },
  {
    title: '资源',
    links: [
      { label: '文档（未开放）', href: '#' },
      { label: '使用指南（未开放）', href: '#' },
      { label: 'FAQ（未开放）', href: '#' },
    ],
  },
]

export default function Footer() {
  return (
    <footer className="border-t border-edge-subtle mt-32">
      <Container className="py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
          {/* Logo + tagline */}
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2 mb-3">
              <img src="/images/smoco_logo.png" alt="Smoco Desktop" className="w-7 h-7 rounded-full" />
              <span className="font-semibold">Smoco Desktop</span>
            </div>
            <p className="text-sm text-content-muted">Windows 实时转录 + 翻译</p>
          </div>

          {/* Link columns */}
          {FOOTER_COLS.map((col) => (
            <div key={col.title}>
              <h4 className="text-sm font-semibold text-content-primary mb-3">{col.title}</h4>
              <ul className="space-y-2">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      target={link.external ? '_blank' : undefined}
                      rel={link.external ? 'noopener noreferrer' : undefined}
                      className="text-sm text-content-muted hover:text-content-primary transition-colors"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom */}
        <div className="pt-8 border-t border-edge-subtle flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-content-muted">
          <div>© 2026 Smoco Desktop</div>
          <div>Built with React + Tailwind CSS</div>
        </div>
      </Container>
    </footer>
  )
}
