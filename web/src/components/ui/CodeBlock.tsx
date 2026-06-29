import clsx from 'clsx'

interface CodeBlockProps {
  code: string
  /** 语言标签（如 "bash"），显示在右上角 */
  language?: string
  className?: string
}

export default function CodeBlock({ code, language, className }: CodeBlockProps) {
  return (
    <div
      className={clsx(
        'relative rounded-md border border-edge-subtle bg-bg-elevated overflow-hidden',
        className,
      )}
    >
      {language && (
        <div className="absolute top-2 right-3 text-[10px] uppercase tracking-wider text-content-muted font-mono">
          {language}
        </div>
      )}
      <pre className="p-4 overflow-x-auto text-sm leading-relaxed">
        <code className="font-mono text-content-primary">{code}</code>
      </pre>
    </div>
  )
}
