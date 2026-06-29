import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'

interface SEOProps {
  /** i18n key for <title> */
  titleKey: string
  /** i18n key for meta description */
  descriptionKey: string
}

function setMeta(selector: string, attr: string, value: string, create: boolean = false) {
  let el = document.head.querySelector<HTMLMetaElement>(selector)
  if (!el && create) {
    el = document.createElement('meta')
    const [, key] = selector.match(/\[(.+?)="(.+?)"\]/) ?? []
    if (key) {
      const name = selector.startsWith('[name') ? 'name' : 'property'
      el.setAttribute(name, key.replace(/['"]/g, ''))
      document.head.appendChild(el)
    }
  }
  if (el) el.setAttribute(attr, value)
}

/**
 * 每个页面顶部声明 SEO 信息。
 * title 跟随当前语言刷新，OG 同步更新。
 */
export default function SEO({ titleKey, descriptionKey }: SEOProps) {
  const { t, i18n } = useTranslation()

  useEffect(() => {
    const title = t(titleKey)
    const description = t(descriptionKey)

    document.title = title

    setMeta('meta[name="description"]', 'content', description)
    setMeta('meta[property="og:title"]', 'content', title)
    setMeta('meta[property="og:description"]', 'content', description)
    setMeta('meta[name="twitter:title"]', 'content', title)
    setMeta('meta[name="twitter:description"]', 'content', description)
  }, [titleKey, descriptionKey, t, i18n.language])

  return null
}
