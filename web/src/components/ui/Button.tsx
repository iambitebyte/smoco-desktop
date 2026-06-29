import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'

type Variant = 'primary' | 'secondary' | 'ghost'
type Size = 'sm' | 'md' | 'lg'

const variantClass: Record<Variant, string> = {
  primary:
    'bg-brand-gradient text-white shadow-glow hover:scale-[1.02] hover:shadow-glow active:scale-100',
  secondary:
    'bg-bg-card text-content-primary border border-edge hover:border-brand-500/60 hover:text-brand-300',
  ghost: 'text-content-secondary hover:text-content-primary hover:bg-bg-card',
}

const sizeClass: Record<Size, string> = {
  sm: 'px-4 py-1.5 text-sm',
  md: 'px-6 py-2.5 text-sm',
  lg: 'px-8 py-4 text-base',
}

interface CommonProps {
  variant?: Variant
  size?: Size
  children: ReactNode
  className?: string
}

interface ButtonAsButton
  extends CommonProps,
    Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className' | 'children'> {
  as?: 'button'
}

interface ButtonAsAnchor extends CommonProps {
  as: 'a'
  href: string
  target?: string
  rel?: string
}

interface ButtonAsLink extends CommonProps {
  as: 'link'
  to: string
}

type ButtonProps = ButtonAsButton | ButtonAsAnchor | ButtonAsLink

export default function Button(props: ButtonProps) {
  const { variant = 'primary', size = 'md', children, className } = props
  const classes = clsx(
    'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-200 cursor-pointer',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400/60 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-primary',
    'disabled:cursor-not-allowed disabled:opacity-50',
    variantClass[variant],
    sizeClass[size],
    className,
  )

  if (props.as === 'a') {
    const { href, target, rel } = props
    return (
      <a className={classes} href={href} target={target} rel={rel}>
        {children}
      </a>
    )
  }

  if (props.as === 'link') {
    const { to } = props
    return (
      <Link className={classes} to={to}>
        {children}
      </Link>
    )
  }

  const { as: _as, variant: _v, size: _s, className: _c, children: _ch, ...rest } = props
  void _as
  void _v
  void _s
  void _c
  void _ch
  return (
    <button className={classes} {...rest}>
      {children}
    </button>
  )
}
