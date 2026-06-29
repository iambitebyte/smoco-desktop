# 路线图

分**产品路线图**（smoco-gui 本体）和**网站路线图**（web/）两条线。
产品路线图驱动网站内容更新，网站路线图是 web 自身的迭代。

---

## 产品路线图（smoco-gui）

### v1.0.0（当前，2026-06）

**核心稳定版**：实时转录 + 翻译能力齐备，Windows 单平台。

#### ✅ 已完成

- **实时转录**
  - WASAPI 系统音频 loopback
  - 远程 Whisper API 支持
  - Local Whisper NPU（OpenVINO-genai，Intel GPU/CPU/NPU 自动检测）
- **实时翻译**
  - LLM 异步翻译（OpenAI 兼容 API）
  - 上下文 N 条（默认 5）
  - 中/英翻译目标
- **数据管理**
  - 转录会话自动保存（`~/.smoco/data/`）
  - 历史浏览（session/entry 两级）
  - 应用日志查看（`~/.smoco/logs/`）
  - 导出会话为 `.txt` / `.md`
- **UI/UX**
  - 多语言界面（中/日/英），切换即时刷新
  - 快捷键覆盖（15+ 操作）
  - 辅助功能（accessibleName）
  - Toast 通知
  - 全局 QSS 样式系统
- **打包分发**
  - 完全自包含的 zip（~770MB）
  - PyInstaller 二次打包 whisper-npu-api.exe
  - 跨机器零依赖

#### 🚧 进行中

无（v1.0.0 即将 release）

---

### v1.1.x（计划 2026-07）

**打磨版**：基于 v1.0 用户反馈的小改进。

- 📋 **音频设备热切换** —— 不重启应用切换输入设备
- 📋 **转录搜索** —— 历史页全文搜索（已搁置，用户呼声高的优先做）
- 📋 **导出 SRT 字幕** —— 除 txt/md 外支持 SRT 格式
- 📋 **快捷键自定义** —— 设置里改键位
- 📋 **浅色主题切换** —— 已有 QSS 基建，加 light 主题
- 📋 **Auto-updater** —— 应用内检测新版本（不强制自动更新，提示即可）

---

### v2.0（计划 2026 Q4）

**跨平台版**：核心能力扩展到 macOS / Linux。

- 📋 **macOS 支持**
  - Apple Silicon Whisper（MLX 或 Core ML）
  - 系统音频捕获（需要 BlackHole 等虚拟设备或 ScreenCaptureKit）
  - pkg 打包格式
- 📋 **Linux 支持**
  - PulseAudio / PipeWire 捕获
  - AppImage 分发
- 📋 **模型市场**
  - 多 Whisper 模型切换（tiny / base / small / medium / large）
  - 自动从 HuggingFace 下载
  - Local 模型管理 UI
- 📋 **更精细的 VAD 配置**
  - 自定义静音阈值
  - 多语言混合识别（自动切换 Whisper 语言）

---

### v2.x（计划 2027 H1）

- 📋 **字幕浮窗**
  - 转录结果作为悬浮窗覆盖其他应用
  - 半透明、可拖动、可调字号
  - 适合看直播时跟读
- 📋 **多设备并行**
  - 同时转录多个音频源
  - 每个源独立 tab
- 📋 **协作模式**
  - 局域网共享实时转录
  - 二维码加入（手机也能看）
- 📋 **翻译引擎扩展**
  - DeepL API 选项
  - 本地翻译模型（NLLB-200 等）

---

### v3.x（远期，2027 H2+）

- 📋 **浏览器扩展**
  - Chrome / Firefox 扩展，直接接管标签页音频
  - 与桌面应用联动
- 📋 **命令行模式**
  - `smoco transcribe --input file.wav --lang ja`
  - 适合批处理、集成到工作流
- 📋 **插件系统**
  - 第三方接入自定义 ASR/翻译引擎
  - 类似 OBS 的扩展生态
- 📋 **云端同步**
  - 可选的会话云备份（端到端加密）

---

## 网站路线图（web/）

### Phase 1（当前，~2 周）

**MVP 单页面上线**

- [ ] 项目脚手架（Vite + React + TS + Tailwind）
- [ ] 路由结构（Home 单页 + 锚点）
- [ ] i18n 接入（中/日/英）
- [ ] Header / Footer 布局
- [ ] Hero section（含 CTA + 截图）
- [ ] Features 6 卡片
- [ ] Use Cases 3 场景
- [ ] Quick Start 5 步
- [ ] Download CTA + 版本号
- [ ] Roadmap section
- [ ] OG 图 + Favicon
- [ ] 部署到 Vercel
- [ ] 接入下载链接（手动上传 zip 到对象存储）

**完成标准**：访客 30 秒内理解产品 + 找到下载按钮。

---

### Phase 2（~1 个月）

**多页面 + SEO**

- [ ] 独立 `/download` 页面（多版本、校验和、镜像链接）
- [ ] `/docs` 文档区（嵌入 smoco-gui/README.md 或独立编写）
- [ ] `/changelog` 更新日志（从 Git 自动生成）
- [ ] 浅色主题切换
- [ ] 移动端体验优化（断点细化）
- [ ] SEO 优化（结构化数据 JSON-LD）
- [ ] 站点搜索（搜文档）

---

### Phase 3（远期）

**社区 + 互动**

- [ ] 用户反馈区（嵌入式 GitHub Issues）
- [ ] FAQ 页面
- [ ] 视频教程（嵌入 YouTube / B 站）
- [ ] 多语言扩展（韩语、法语等）
- [ ] 实时下载统计（隐私友好，不追踪用户）
- [ ] 在线配置生成器（设置参数 → 导出 settings.json）

---

## 版本号约定

- **产品**：`MAJOR.MINOR.PATCH`（semver）
  - MAJOR：破坏性变更（如 v2 跨平台重构）
  - MINOR：新功能（如 v1.1 加搜索）
  - PATCH：bug 修复
- **网站**：跟产品解耦，部署时用 git commit hash 标记

## 发布节奏

| 类型 | 频率 | 触发 |
|---|---|---|
| Patch | 按需 | 紧急 bug |
| Minor | 每月 | 路线图 v1.1.x 项 |
| Major | 每年 | v2 / v3 大版本 |

每个 release 走 GitHub Releases，自动触发网站下载链接更新。

---

## 待确认

- ⏳ **版本号起点**：smoco-gui 还没用正式版本号，建议 v1.0.0 起步
- ⏳ **下载托管**：用 GitHub Releases（免费但慢）/ 对象存储（Cloudflare R2 / S3）/ CDN？
- ⏳ **域名**：是否要买独立域名（如 smoco.app）？
- ⏳ **分析工具**：是否接入 Plausible / Umami（隐私友好的访问统计）？
