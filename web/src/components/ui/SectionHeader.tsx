import type { ReactNode } from 'react'
import clsx from 'clsx'

interface SectionHeaderProps {
  /** 上方小标签（如 "Features"），可选 */
  eyebrow?: string
  title: ReactNode
  description?: ReactNode
  align?: 'left' | 'center'
  className?: string
}

export default function SectionHeader({
  eyebrow,
  title,
  description,
  align = 'center',
  className,
}: SectionHeaderProps) {
  return (
    <div
      className={clsx(
        'mb-16',
        align === 'center' ? 'text-center mx-auto max-w-2xl' : 'text-left',
        className,
      )}
    >
      {eyebrow && (
        <div
          className={clsx(
            'text-brand-400 text-xs font-semibold uppercase tracking-[0.2em] mb-4',
          )}
        >
          {eyebrow}
        </div>
      )}
      <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">{title}</h2>
      {description && (
        <p className="text-lg text-content-secondary leading-relaxed">{description}</p>
      )}
    </div>
  )
}
