# 首页内容规划

基于 smoco-gui 的实际能力整理。所有文案以**中文版**为主，ja/en 翻译时根据习惯微调（不是逐字翻译）。

---

## 1. 顶部导航（Header）

```
[Logo] Smoco Desktop           功能  下载  文档  [GitHub]  [Lang ▾]
```

- 高度 64px，毛玻璃背景（scroll 后）
- Logo + 文字「Smoco Desktop」
- 锚点导航：功能 / 下载 / 文档
- GitHub 图标链接（外开）
- 语言切换下拉（中/日/英，默认跟随浏览器）

---

## 2. Hero（首屏）

**布局**：左文字 + 右产品截图（桌面端），移动端上下堆叠。

**中文文案**：

> ### 把任何系统音频，瞬间变成文字
>
> Smoco Desktop 是一款 Windows 桌面应用，实时转录浏览器、会议软件、直播播放器里的任何声音，并立即翻译成你的语言。完全本地化的 Whisper 引擎，无需联网、无需安装 Python。
>
> [下载 Windows · 770MB] [查看 GitHub ←]

**副信息**（Hero 下方）：
- ✅ 完全自包含（含 Whisper 引擎）
- ✅ 中/日/英三语界面
- ✅ Open Source

**Hero 视觉**：
- 背景：紫色渐变 + 光晕（`from-violet-500/20 to-indigo-500/20`）
- 产品截图：圆角 + 投影 + 微微旋转（`rotate-2`）+ 入场动画
- 关键数字：「**实时** / **本地** / **多语种**」三个标签

---

## 3. 痛点 → 解决（Problem/Solution）

三栏卡片，每张：图标 + 标题 + 描述。

### 卡片 1：浏览器/会议软件没字幕
> 看日文直播听不懂？开会用 Teams/Zoom 但同事说英文？Smoco 接管系统音频，**任何**应用的声音都能转录。

### 卡片 2：在线翻译要打字
> 不用复制粘贴。Whisper 实时识别 + LLM 上下文翻译，**说话的下一秒**就能看到母语。

### 卡片 3：云端转录有隐私顾虑
> Local Whisper 基于 OpenVINO-genai 跑在你自己的电脑上，**音频不出本机**，适合保密会议。

---

## 4. 核心功能（Features）

6 个特性卡片（2x3 grid），每个：图标 + 标题 + 一句话 + 「了解更多」链接到 `/docs#feature-x`。

| 特性 | 一句话 |
|---|---|
| 🎙️ **实时转录** | 16kHz mono S16LE 音频流，Whisper API 转写为文字 |
| 🌐 **实时翻译** | LLM 翻译，支持上下文 N 条（默认 5），理解更准 |
| 🧠 **Local Whisper NPU** | 内嵌 OpenVINO-genai，自动检测 GPU/NPU/CPU |
| ⏱️ **VAD 智能断句** | WebRTC VAD 检测静音，自动分块，参数可调 |
| 📚 **历史浏览** | 应用内查看过去会话，分页 + 详情 + 导出 |
| ⌨️ **全键盘操作** | 15+ 快捷键覆盖常用操作，无需鼠标 |

每个卡片配一张小的截图或 GIF。

---

## 5. 使用场景（Use Cases）

时间轴式布局，每个场景一个步骤流。

### 场景 A：日文直播 → 中文字幕
1. 启动 Smoco Desktop
2. 设置 → 本地 Whisper 模型 → 启动服务（首次约 30 秒加载）
3. 主页选择浏览器音频设备
4. 开始转录 → 选「翻译为中文」
5. 实时看到日文原文 + 中文翻译

### 场景 B：英语会议 → 笔记归档
1. 配置远程 Whisper 服务器（或用 Local Whisper）
2. 选择 Teams/Zoom 输出设备
3. 实时转录，自动保存到 `~/.smoco/data/`
4. 结束后从历史页导出为 `.md`

### 场景 C：播客字幕生成
1. 播放播客，Smoco 接管音频
2. 转录过程中翻译（可选）
3. 导出整个会话为 `.txt` 或 `.md`
4. 作为字幕或笔记使用

---

## 6. 截图展示（Gallery）

3-4 张产品截图，等比 + 圆角 + 阴影：
- 主页（设备选择）
- 转录中（带翻译表格）
- 设置对话框（4 tab）
- 历史详情页

---

## 7. 安装使用（Quick Start）

**5 步上手**，每步一个图标 + 一行：

```
1. 下载 zip    2. 解压任意位置    3. 双击 exe    4. 配置 Whisper    5. 开始转录
   ↓               ↓                  ↓              ↓                   ↓
   [下载按钮]      解压到 D:\         SmocoDesktop   设置→本地 Whisper    选设备→F5
                                       .exe          启动服务
```

**系统要求**（小字 footnote）：
- Windows 10/11 64-bit
- 推荐 Intel Arc GPU 或 Intel CPU（NPU 加速）
- ~800MB 磁盘空间

---

## 8. 下载区（Download CTA）

独立 section，紫色渐变背景，强 CTA：

```
┌─────────────────────────────────────────┐
│       准备好试试了吗？                  │
│                                          │
│       [下载 Smoco Desktop v1.0.0]       │
│                                          │
│       Windows 10/11 · 770MB · zip       │
│       Open Source · MIT License         │
└─────────────────────────────────────────┘
```

版本说明（小字）：
- 当前版本：v1.0.0（2026-06-29）
- 完整变更日志：[CHANGELOG](github)
- 旧版本：[GitHub Releases](github)

---

## 9. Roadmap（开发计划）

时间轴式（垂直），按版本：

### v1.x（当前）
- ✅ 核心转录 + 翻译
- ✅ Local Whisper NPU
- ✅ 历史 / 日志 / 快捷键
- 🚧 macOS 支持（Apple Silicon Whisper）
- 🚧 模型市场（多 Whisper 模型切换）

### v2.x
- 📋 实时字幕浮窗（覆盖其他应用）
- 📋 多设备并行转录
- 📋 协作模式（局域网共享转录）

### v3.x
- 📋 字幕导出为 SRT/ASS
- 📋 命令行模式
- 📋 浏览器扩展（接管标签页音频）

完整 roadmap 见 [docs/roadmap.md](roadmap.md)。

---

## 10. Footer

3 列：

| 产品 | 资源 | 开发 |
|---|---|---|
| 下载 | 文档 | GitHub |
| 功能 | 使用指南 | Issues |
| Roadmap | FAQ | 贡献指南 |
| 更新日志 | 联系方式 | License |

底部一行：© 2026 Smoco Desktop · MIT License · Built with React + Tailwind

---

## 11. 多语言策略

- **中文（zh）**：默认，主要市场
- **日文（ja）**：完整翻译（核心场景是日文→中文翻译）
- **英文（en）**：完整翻译（国际用户）

文案优先用中文写（最自然），翻译时**不逐字**，按目标语言习惯调整：
- 日文：用「ですます」体，标题用名词结句
- 英文：用动词开头的标题，主动语态

`src/i18n/{zh,ja,en}.json` 维护，每段文案有 key，方便校对。

---

## 12. SEO / OG

- `<title>`: Smoco Desktop · Windows 实时转录 + 翻译
- `<meta description>`: Windows 系统音频实时转录工具，支持 Whisper 转录 + LLM 翻译，内嵌 OpenVINO-genai Local Whisper，零联网零安装。
- OG 图：1200x630，紫色渐变背景 + 产品截图 + 标题
- Favicon：smoco_logo_circle.png
- 关键词：转录、Whisper、翻译、OpenVINO、Windows、本地 AI

---

## 待确认 / 后续

- ✅ 已确认：内容范围、文案方向
- ⏳ 待定：是否要做"在线体验"（用 WebAssembly 跑 demo？技术难度大，建议跳过）
- ⏳ 待定：是否做博客区（暂不做，先聚焦产品介绍）
- ⏳ 待定：版本号怎么定（建议从 1.0.0 起，因为 smoco-gui 已稳定）
