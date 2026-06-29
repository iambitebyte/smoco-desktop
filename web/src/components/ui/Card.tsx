import type { ReactNode } from 'react'
import clsx from 'clsx'

interface CardProps {
  children: ReactNode
  className?: string
  /** 是否有 hover 高亮效果（默认 true） */
  interactive?: boolean
}

export default function Card({ children, className, interactive = true }: CardProps) {
  return (
    <div
      className={clsx(
        'rounded-lg border border-edge-subtle bg-bg-card p-6 transition-colors duration-200',
        interactive && 'hover:border-brand-500/50',
        className,
      )}
    >
      {children}
    </div>
  )
}
