# Smoco Desktop 官网

Smoco Desktop 的产品官网 —— React + Vite + Tailwind CSS 构建。

## 项目目标

一个**纯静态**站点，做三件事：

1. **介绍产品** —— 让访客 30 秒内理解 Smoco Desktop 是什么、解决什么问题
2. **引导下载** —— 一键下载 Windows zip 包，附带版本说明
3. **展示演进** —— 通过 roadmap 让用户知道后续会做什么

不做的：
- 用户系统、登录、评论
- 在线试用（桌面应用必须下载）
- 复杂 CMS（所有内容是开发者维护的 Markdown / TSX）

## 技术栈

| 层 | 选型 | 理由 |
|---|---|---|
| 构建 | Vite 5 + React 18 + TypeScript | 现代默认，HMR 快 |
| 样式 | Tailwind CSS 3 | 原子化、无样式冲突、设计 token 易沉淀 |
| 动效 | Framer Motion | React 生态最成熟的动效库，做入场/hover 动效 |
| 图标 | lucide-react | 极简线性图标，符合 AI 产品审美 |
| 国际化 | react-i18next | 项目本身支持中/日/英三语 |
| 字体 | Inter（拉丁）+ Noto Sans JP / SC（CJK） | 开源、跨平台一致 |

**不用的**：
- Next.js（不需要 SSR/SEO 深度优化，纯静态够用）
- styled-components / emotion（Tailwind 足够，避免双系统）
- UI 库（shadcn/ui 可以参考但不用整套，保持极简）

## 目录结构

```
web/
├── README.md                # 本文件（开发者必读）
├── docs/                    # 设计与内容文档
│   ├── content.md           # 首页文案内容（中/日/英草稿）
│   ├── design.md            # 设计规范（颜色/字体/组件/动效）
│   └── roadmap.md           # 产品 + 网站路线图
├── public/                  # 静态资源（构建时复制）
│   ├── downloads/           # 打包好的 zip（gitignored，部署时上传）
│   └── images/              # 截图、OG 图
├── src/
│   ├── main.tsx             # 应用入口
│   ├── App.tsx              # 路由根
│   ├── pages/               # 每个页面一个文件
│   │   ├── Home.tsx
│   │   ├── Download.tsx
│   │   └── Docs.tsx
│   ├── components/          # 可复用组件
│   │   ├── layout/          # Header / Footer / Container
│   │   ├── home/            # Hero / FeatureGrid / RoadmapSection 等
│   │   └── ui/              # Button / Tag / Card 等基础组件
│   ├── i18n/                # 三语资源
│   │   ├── zh.json
│   │   ├── ja.json
│   │   └── en.json
│   ├── styles/              # 全局样式
│   │   └── globals.css      # Tailwind 入口 + 设计 token
│   └── lib/                 # 工具
│       ├── download.ts      # 下载链接逻辑（版本号拼接）
│       └── analytics.ts     # 访问统计（可选）
├── tailwind.config.ts       # Tailwind 配置 + 设计 token 扩展
├── vite.config.ts
├── tsconfig.json
└── package.json
```

## 开发命令

```bash
# 安装依赖
pnpm install    # 或 npm install

# 开发（默认 http://localhost:5173）
pnpm dev

# 生产构建（输出到 dist/）
pnpm build

# 预览生产构建
pnpm preview

# 类型检查
pnpm typecheck

# lint
pnpm lint
```

## 部署

纯静态站，可部署到任何静态托管：

| 平台 | 配置 |
|---|---|
| Vercel | Framework: Vite，Build: `pnpm build`，Output: `dist` |
| Netlify | Build: `pnpm build`，Publish: `dist` |
| Cloudflare Pages | Framework: Vite，Output: `dist` |
| GitHub Pages | `pnpm build` 后推送 `dist/` 到 gh-pages 分支 |

**下载文件**：`public/downloads/SmocoDesktop-x.y.z.zip` 不提交到 git（大文件），部署前手动上传到对象存储或 CDN，构建时通过 env 指定下载链接 base URL。

## 与 smoco-gui 的关系

- **smoco-gui**：桌面应用本体（Python / PyQt6）
- **web**：官网（React / TS）
- 两者**独立部署、独立版本**。web 通过 `smoco-gui/VERSION` 文件读取最新版本号（开发时手动同步，后续可加 CI 自动化）。

## 性能预算

| 指标 | 目标 |
|---|---|
| LCP | < 2.0s（4G） |
| CLS | < 0.1 |
| 首屏 JS gzip | < 100KB |
| 首屏 CSS gzip | < 30KB |
| 总图片体积（首屏） | < 200KB |

不达标时优先：
1. 检查未用的依赖（`pnpm exec vite-bundle-visualizer`）
2. 拆分路由级 chunk（React.lazy）
3. 图片转 WebP / AVIF

## 浏览器支持

- 现代浏览器最新 2 个版本（Chrome / Edge / Firefox / Safari）
- 不支持 IE
- 移动端能看但**不优化**（桌面下载产品，移动端只是预览）

## 贡献流程

1. 改文案/样式：直接 PR
2. 改下载链接/版本号：跟 smoco-gui release 同步
3. 加新页面：先更新 `docs/content.md` 描述，再实施

详细内容规划见 [`docs/content.md`](docs/content.md)，设计规范见 [`docs/design.md`](docs/design.md)，路线图见 [`docs/roadmap.md`](docs/roadmap.md)。
