import type { ReactNode } from 'react'
import clsx from 'clsx'

interface ContainerProps {
  children: ReactNode
  className?: string
  /** 最大宽度档位，默认 7xl（1280px） */
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

const sizeClass: Record<NonNullable<ContainerProps['size']>, string> = {
  sm: 'max-w-3xl',
  md: 'max-w-5xl',
  lg: 'max-w-6xl',
  xl: 'max-w-7xl',
}

export default function Container({ children, className, size = 'xl' }: ContainerProps) {
  return (
    <div className={clsx('mx-auto w-full px-6', sizeClass[size], className)}>{children}</div>
  )
}
