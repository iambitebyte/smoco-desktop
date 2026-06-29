# 设计规范

面向 AI 桌面产品的现代审美：**暗色优先、紫色渐变、大留白、克制动效**。

## 设计原则

1. **暗色优先** —— 开发者审美，搭配紫色渐变最出彩（Phase 2 加浅色切换）
2. **大留白** —— 内容不挤，section 间距 96-128px
3. **克制动效** —— 入场动画 300ms 内，hover 反馈 150ms，不用炫技动效
4. **极简图标** —— Lucide line 系，1.5px stroke
5. **文字优先** —— 不要让装饰盖过内容，每个 section 必须能纯文字读
6. **代码可信感** —— 等宽字体 + 圆角 + 细边框，营造工程感

---

## 颜色系统

### 主色（Brand）

紫色到靛蓝的渐变，AI 产品典型配色：

```css
--brand-50:  #f5f3ff;
--brand-100: #ede9fe;
--brand-200: #ddd6fe;
--brand-300: #c4b5fd;
--brand-400: #a78bfa;
--brand-500: #8b5cf6;   /* 主色 violet-500 */
--brand-600: #7c3aed;   /* 深色主色 violet-600 */
--brand-700: #6d28d9;
--brand-800: #5b21b6;
--brand-900: #4c1d95;
```

辅助渐变：
- `brand-gradient`: `linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%)`
- `brand-gradient-subtle`: `linear-gradient(135deg, rgba(139, 92, 246, 0.2) 0%, rgba(99, 102, 241, 0.2) 100%)`

### 中性色（暗色优先）

```css
/* 暗色（默认） */
--bg-primary:    #0a0a0f;   /* 最深背景 */
--bg-secondary:  #13131a;   /* section 背景 */
--bg-card:       #1a1a24;   /* 卡片背景 */
--bg-elevated:   #22222e;   /* 悬浮元素 */

--border-subtle: #2a2a36;
--border-default: #3a3a48;

--text-primary:   #f5f5fa;
--text-secondary: #a8a8b8;
--text-muted:     #6c6c7e;

/* 浅色（Phase 2） */
--bg-primary-light:    #ffffff;
--bg-secondary-light:  #f8f8fb;
--bg-card-light:       #ffffff;
--text-primary-light:  #1a1a24;
--text-secondary-light:#4a4a58;
```

### 功能色

```css
--success: #10b981;   /* 绿（成功、已激活） */
--warning: #f59e0b;   /* 橙（警告） */
--error:   #ef4444;   /* 红（错误、危险按钮） */
--info:    #3b82f6;   /* 蓝（信息） */
```

### 渐变光晕（Hero 用）

```css
.hero-glow-1: radial-gradient(circle at 30% 20%, rgba(139, 92, 246, 0.25), transparent 60%);
.hero-glow-2: radial-gradient(circle at 70% 60%, rgba(99, 102, 241, 0.20), transparent 50%);
```

---

## 字体

### 字体族

```css
--font-sans: 'Inter', 'Noto Sans SC', 'Noto Sans JP', system-ui, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
```

加载方式：
- Inter 从 Google Fonts 或 fontsource 加载（含 400/500/600/700/800）
- Noto Sans SC / JP 按需子集（避免首屏过大）

### 字号阶梯（type scale）

| Token | Tailwind | px | 用途 |
|---|---|---|---|
| display | text-7xl/text-8xl | 72-96 | Hero 主标题 |
| h1 | text-5xl | 48 | section 主标题 |
| h2 | text-3xl | 30 | 卡片组标题 |
| h3 | text-xl | 20 | 卡片标题 |
| body-lg | text-lg | 18 | Hero 描述 |
| body | text-base | 16 | 默认正文 |
| body-sm | text-sm | 14 | 次要文字 |
| caption | text-xs | 12 | 标签、footnote |

### 字重

- Regular 400：正文
- Medium 500：导航、按钮、卡片标题
- Semibold 600：section 标题
- Bold 700+：Hero 主标题

### 行高

- 紧凑（leading-tight 1.2）：标题
- 默认（leading-normal 1.5）：正文
- 宽松（leading-relaxed 1.7）：长描述

---

## 间距系统

8px 基准（Tailwind 默认）：

| Token | 值 | 用途 |
|---|---|---|
| space-xs | 8 | 图标与文字内联 |
| space-sm | 12-16 | 卡片内边距 |
| space-md | 24 | 卡片间距 |
| space-lg | 32-48 | 子 section 间距 |
| space-xl | 64-96 | section 之间 |
| space-2xl | 128+ | 大节奏 |

容器最大宽度：`max-w-7xl`（1280px）+ 两侧 24px padding。

---

## 圆角

```css
--radius-sm: 6px;    /* 按钮、tag */
--radius-md: 8px;    /* 卡片 */
--radius-lg: 12px;   /* 大卡片、Hero 截图 */
--radius-xl: 16px;   /* 模态框 */
--radius-full: 9999px; /* 圆形按钮、pill */
```

---

## 阴影

暗色模式下阴影要带紫色 tint，避免灰蒙蒙：

```css
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
--shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
--shadow-lg: 0 12px 32px rgba(0, 0, 0, 0.5);
--shadow-glow: 0 0 32px rgba(139, 92, 246, 0.3);   /* CTA 按钮 */
--shadow-card: 0 8px 24px rgba(0, 0, 0, 0.4), 0 0 1px rgba(139, 92, 246, 0.2);
```

---

## 组件规范

### Button

三种 variants：

| Variant | 用途 | 样式 |
|---|---|---|
| `primary` | 主 CTA | `bg-brand-gradient text-white shadow-glow hover:scale-[1.02]` |
| `secondary` | 次要操作 | `bg-bg-card text-primary border border-border-default hover:border-brand-500` |
| `ghost` | 文字按钮 | `text-secondary hover:text-primary hover:bg-bg-card` |

尺寸：
- `lg`：`px-8 py-4 text-base`（Hero CTA）
- `md`：`px-6 py-2.5 text-sm`（默认）
- `sm`：`px-4 py-1.5 text-sm`（导航）

圆角统一 `rounded-lg`，过渡 `transition-all 200ms`。

### Card

```jsx
<div className="bg-bg-card border border-border-subtle rounded-lg p-6 
                hover:border-brand-500/50 transition-colors duration-200">
  <Icon className="text-brand-400 w-6 h-6 mb-4" />
  <h3 className="text-xl font-semibold mb-2">{title}</h3>
  <p className="text-secondary">{description}</p>
</div>
```

### Tag / Badge

```jsx
<span className="inline-flex items-center gap-1 px-3 py-1 rounded-full 
                 bg-brand-500/10 text-brand-300 border border-brand-500/30 
                 text-xs font-medium">
  <CheckIcon className="w-3 h-3" />
  New
</span>
```

### Section Header（统一节奏）

```jsx
<section className="py-24">
  <div className="max-w-7xl mx-auto px-6">
    <div className="text-center mb-16">
      <span className="text-brand-400 text-sm font-medium uppercase tracking-wider">
        Features
      </span>
      <h2 className="text-5xl font-bold mt-4 mb-4">核心功能</h2>
      <p className="text-secondary text-lg max-w-2xl mx-auto">
        描述文字
      </p>
    </div>
    {/* 内容 */}
  </div>
</section>
```

### Code Block

```jsx
<pre className="bg-bg-elevated border border-border-subtle rounded-md p-4 
                font-mono text-sm text-text-primary overflow-x-auto">
  <code>{code}</code>
</pre>
```

行内代码：`px-1.5 py-0.5 bg-bg-elevated rounded font-mono text-sm text-brand-300`

---

## 动效规范

### 入场动画（Framer Motion）

```jsx
<motion.div
  initial={{ opacity: 0, y: 20 }}
  whileInView={{ opacity: 1, y: 0 }}
  viewport={{ once: true, margin: "-100px" }}
  transition={{ duration: 0.4, ease: "easeOut" }}
>
```

- **duration**：0.3-0.5s
- **ease**：`easeOut` 标准曲线
- **触发**：进入视口（`whileInView`，once）
- **错位**：列表项 stagger 0.08s

### Hover

| 元素 | 反馈 |
|---|---|
| Button | `scale-[1.02]` 200ms |
| Card | 边框颜色变紫 200ms |
| Icon | 微微放大 `scale-110` 150ms |
| Link | 颜色变 brand-400 150ms |

### 不要做

- ❌ 旋转动画
- ❌ 弹跳（spring stiffness 高）
- ❌ 闪烁/脉冲（除非状态指示）
- ❌ 自动播放的视频/音频
- ❌ Parallax 滚动（性能差，对 SEO 无益）

---

## 图标

**库**：`lucide-react`（统一线性 1.5px stroke）

选用规范：
- 功能图标：使用 lucide 现成的（如 `Mic`, `Languages`, `Cpu`）
- 装饰图标：用简单的几何 SVG
- 不用 emoji（截图里可以用，UI 上不用）

尺寸：
- `w-4 h-4`：行内
- `w-5 h-5`：按钮内
- `w-6 h-6`：卡片标题前
- `w-8 h-8`：feature 大图标

颜色：跟文字色一致或用 `text-brand-400` 强调。

---

## 图片规范

### 产品截图

- 格式：WebP（兼容性好）+ AVIF（更小，现代浏览器）
- 尺寸：1440x900（16:10）
- 压缩：`sharp` 或 `squoosh`，质量 80
- 圆角：`rounded-lg`
- 阴影：`shadow-lg`
- 周围加紫色光晕（`shadow-glow` opacity 50%）

### OG 图

- 1200x630
- 紫色渐变背景
- 居中产品名 + slogan + 产品截图（缩小）

### Favicon

- 32x32 / 16x16
- 用 smoco_logo_circle.png 转换

---

## 响应式断点

Tailwind 默认：

| 断点 | 宽度 | 布局 |
|---|---|---|
| `sm` | 640 | 大手机，竖屏 |
| `md` | 768 | 平板 |
| `lg` | 1024 | 小笔记本 |
| `xl` | 1280 | 桌面 |
| `2xl` | 1536 | 大屏 |

**优先级**：mobile-first（默认 mobile，逐步增强到 desktop）。

布局变化：
- Hero：mobile 上下堆叠，desktop 左右
- FeatureGrid：mobile 1 列，sm 2 列，lg 3 列
- Header：mobile 隐藏导航文字，只显示 Logo + 下载按钮（汉堡菜单展开）

---

## 无障碍

- 所有图片有 `alt`
- 按钮文字可读（不用纯图标按钮）
- 颜色对比度：正文 ≥ 4.5:1，大文字 ≥ 3:1
- 焦点可见（`:focus-visible` 用 brand-400 outline）
- 支持键盘导航（Tab 顺序合理）
- `prefers-reduced-motion`：禁用动效

---

## 设计 Don'ts

- ❌ 多种渐变混用（一个页面最多 2 种渐变）
- ❌ 用蓝色作为主色（太普通，跟 Linear、Stripe 撞）
- ❌ 卡片用玻璃拟态大面积（性能差、可读性差）
- ❌ 字号小于 14（移动端最小 16）
- ❌ 按钮多于 3 个 variants
- ❌ 在 hero 加视频背景（首屏性能差）

---

## 设计参考

可参考的 AI 产品网站（学习结构，不抄设计）：

- **Linear**（linear.app）：极致克制，动效精致
- **Vercel**（vercel.com）：暗色 + 渐变 + 大字号
- **Anthropic**（anthropic.com）：温柔但专业
- **Modal**（modal.com）：技术感强，代码块设计好
- **Replicate**（replicate.com）：模型展示方式

不要参考：
- ❌ 早期 SaaS 网站（蓝色 + 圆形按钮 + 笑脸图）
- ❌ 模板网站（Hero 已经被滥用）
