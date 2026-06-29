import type { ReactNode } from 'react'
import clsx from 'clsx'

type Color = 'brand' | 'success' | 'warning' | 'neutral'

interface TagProps {
  children: ReactNode
  color?: Color
  /** 是否带圆点指示器 */
  dot?: boolean
  className?: string
}

const colorClass: Record<Color, string> = {
  brand:
    'bg-brand-500/10 text-brand-300 border-brand-500/30 [&_.tag-dot]:bg-brand-400',
  success:
    'bg-emerald-500/10 text-emerald-300 border-emerald-500/30 [&_.tag-dot]:bg-emerald-400',
  warning:
    'bg-amber-500/10 text-amber-300 border-amber-500/30 [&_.tag-dot]:bg-amber-400',
  neutral:
    'bg-bg-elevated text-content-secondary border-edge [&_.tag-dot]:bg-content-muted',
}

export default function Tag({ children, color = 'brand', dot = false, className }: TagProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-medium',
        colorClass[color],
        className,
      )}
    >
      {dot && <span className={clsx('tag-dot w-1.5 h-1.5 rounded-full')} aria-hidden />}
      {children}
    </span>
  )
}
