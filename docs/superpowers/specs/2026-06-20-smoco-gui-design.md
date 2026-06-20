# Smoco Desktop GUI 设计文档

## 1. 项目概述

**目标**：为 smoco-desktop 添加图形界面，提供可视化操作和实时转录显示。

**当前 CLI 流程**：
```bash
uv run smoco run --wasapi --whisper-url http://server:port --whisper-lang ja
```

**目标 GUI 流程**：
启动 → 选择 Speaker → 显示声波 → 点击开始 ASR → 选择服务器/语言 → 转录 → 实时显示文本 → 停止返回

---

## 2. 技术栈选择

### 方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **PyQt6/PySide6** | 原生 Python，成熟，跨平台 | 需要安装 Qt 库（大） | ⭐⭐⭐⭐⭐ |
| **Electron + Web** | 界面灵活，HTML/CSS/JS | 打包大，资源占用高 | ⭐⭐⭐ |
| **Dear PyGui** | 轻量，纯 Python，简单 | 功能有限，不够成熟 | ⭐⭐ |
| **Tkinter** | Python 内置，无需安装 | 界面老旧，不现代 | ⭐⭐ |

**推荐：PyQt6 或 PySide6**

### 推荐理由

1. **PyQt6** 是 Qt6 的 Python 绑定，功能强大
2. **跨平台**：Windows、macOS、Linux
3. **成熟稳定**：大量项目使用
4. **丰富组件**：适合复杂界面
5. **Python 原生**：无需 Node.js，可直接调用现有 smoco 代码

---

## 3. 界面设计

### 3.1 主界面布局

```
┌─────────────────────────────────────────────────────────┐
│  Smoco Desktop                                    [─] [□] [×]  │
├─────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  Speaker Selection                               │  │
│  │                                                       │  │
│  │  [○] LG ULTRAFINE (Display Audio)                   │  │
│  │  [○] スピーカー (Realtek Audio) ✓                 │  │
│  │                                                       │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  Audio Level Meter                                │  │
│  │                                                       │  │
│  │  [████████████████░░░░░░░░░░░░░░] RMS: 0.125        │  │
│  │                                                       │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                                 │
│              [  Start ASR  ]                              │
│                                                                 │
└─────────────────────────────────────────────────────────┘
```

### 3.2 ASR 设置界面

```
┌─────────────────────────────────────────────────────────┐
│  ASR Configuration                            [←] [×]      │
├─────────────────────────────────────────────────────────┤
│                                                                 │
│  Server Selection:                                        │
│  ○ Remote Server                                          │
│    URL: [http://43.82.132.240:10060      ]               │
│                                                         │
│  ○ Local API (http://127.0.0.1:8000)                      │
│                                                         │
│  Language:                                                │
│  ● Japanese (ja)                                           │
│  ○ Chinese (zh)                                            │
│  ○ English (en)                                            │
│                                                         │
│              [  Start  ]  [  Cancel  ]                    │
│                                                                 │
└─────────────────────────────────────────────────────────┘
```

### 3.3 转录界面

```
┌─────────────────────────────────────────────────────────┐
│  Live Transcription                            [●] [Stop] │
├─────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────┐  │
│  │  [10:30:45] 今日の天気は晴れです。              │  │
│  │  [10:30:52] 明日も晴れるでしょう。              │  │
│  │  [10:31:05] 週末は雨が降る予報です。            │  │
│  │  [10:31:20] 気温は25度前後になる見込みです。      │  │
│  │  [10:31:35]                                        │  │
│  │  [10:31:42> 台風の影響で海沿いは風が強くなります  │  │
│  │  [10:31:42>  本州側は比較的穏やかな天気となる    │  │
│  │  [10:31:42> でしょう。                          │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                           ↑
│                                                      自动滚动
│                                                                 │
│              Status: Transcribing...                   │
│                                                                 │
└─────────────────────────────────────────────────────────┘
```

### 3.4 设置界面

```
┌─────────────────────────────────────────────────────────┐
│  Settings                                        [×]      │
├─────────────────────────────────────────────────────────┤
│                                                                 │
│  Server Configuration                                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Remote Servers:                                │   │
│  │  ┌───────────────────────────────────────────┐ │   │
│  │  │ [1] http://43.82.132.240:10060         [×]│ │   │
│  │  │ [2] http://127.0.0.1:8000               [×]│ │   │
│  │  │ [+ Add Server...]                          │ │   │
│  │  └───────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         [Add]
│                                                                 │
│              [  Save  ]  [  Cancel  ]                  │
│                                                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 4. 技术设计

### 4.1 架构

```
PyQt6 GUI (主线程)
    ├── Speaker Selection (QWidget)
    ├── Audio Meter (QProgressBar + Timer)
    ├── ASR Controller (QThread)
    │   ├── WASAPI Audio Capture (smoco.pipeline)
    │   └── HTTP Client (aiohttp)
    └── Transcript Display (QTextEdit + Auto-scroll)
```

### 4.2 核心组件

| 组件 | 功能 | Qt 类 |
|------|------|-------|
| **SpeakerSelector** | 列出并选择音频设备 | `QListWidget` |
| **AudioMeter** | 显示实时音量条 | `QProgressBar` + `QTimer` |
| **ASRController** | 控制 ASR 流程 | `QObject` + `QThread` |
| **TranscriptWindow** | 显示转录文本 | `QTextEdit` |
| **SettingsWindow** | 管理服务器列表 | `QDialog` |

### 4.3 数据流

```
GUI 主线程
  ├─ 用户选择 Speaker
  ├─ 启动 Audio Meter (Timer 更新)
  ├─ 用户点击 "Start ASR"
  │   ├─ 显示 ASR 配置对话框
  │   ├─ 用户选择服务器/语言
  │   ├─ 启动 ASRController (后台线程)
  │   │   ├─ 初始化 smoco.pipeline
  │   │   ├─ 开始音频采集
  │   │   ├─ 实时发送到 Whisper API
  │   │   └─ 接收转录结果
  │   └─ 信号 → 更新 TranscriptDisplay
  └─ 用户点击 "Stop"
      └─ 停止 ASRController → 清理资源
```

### 4.4 配置存储

使用 `QSettings` 存储配置：
```python
settings = QSettings("iambitebyte", "SmocoDesktop")
settings.setValue("last_server", "http://43.82.132.240:10060")
settings.setValue("last_language", "ja")
settings.setValue("servers", ["http://...", "http://..."])
```

---

## 5. 开发过程

### 5.1 Phase 1: 基础框架（第 1 周）

**目标**：创建基础 GUI 框架

**任务**：
1. 创建 `smoco-gui/` 目录
2. 添加 `pyproject.toml`（PyQt6 依赖）
3. 创建主窗口 `MainWindow`（Speaker Selection + Audio Meter）
4. 集成 `smoco.source.wasapi.list_devices()`
5. 实现 Audio Meter 可视化

**验收**：
- 能显示设备列表
- 能选择设备
- 能看到音量条

### 5.2 Phase 2: ASR 控制（第 2 周）

**目标**：实现 ASR 流程控制

**任务**：
1. 创建 ASR 配置对话框（服务器/语言选择）
2. 实现 ASRController（后台线程）
3. 集成 `smoco.pipeline` 和 `smoco.transcriber.whisper_remote`
4. 实现开始/停止控制

**验收**：
- 能配置服务器和语言
- 点击 Start 开始转录
- 点击 Stop 停止转录

### 5.3 Phase 3: 转录显示（第 3 周）

**目标**：实现实时转录文本显示

**任务**：
1. 创建转录窗口（TranscriptWindow）
2. 实现实时文本更新（Signal/Slot）
3. 实现自动滚动
4. 添加时间戳显示

**验收**：
- 能看到转录文本实时显示
- 文本自动滚动
- 有时间戳

### 5.4 Phase 4: 设置功能（第 4 周）

**目标**：实现设置和服务器管理

**任务**：
1. 创建设置对话框
2. 实现服务器列表（增删改）
3. 使用 QSettings 持久化配置
4. 添加默认服务器快速选择

**验收**：
- 能添加/删除服务器
- 配置能保存和加载
- 重启后配置保持

### 5.5 Phase 5: 打包和测试（第 5 周）

**目标**：打包成可执行文件

**任务**：
1. 使用 PyInstaller 或 Nuitka 打包
2. 测试安装包
3. 编写用户文档
4. 性能优化

**验收**：
- 能独立运行（无需 Python）
- 界面响应流畅
- 转录准确

---

## 6. 目录结构

```
smoco-desktop/
├── smoco-gui/                    # 新增：GUI 目录
│   ├── __init__.py
│   ├── main.py                   # 主入口
│   ├── main_window.py            # 主窗口
│   ├── widgets/                  # UI 组件
│   │   ├── speaker_selector.py   # 设备选择
│   │   ├── audio_meter.py        # 音量条
│   │   ├── asr_dialog.py         # ASR 配置
│   │   ├── transcript_window.py  # 转录窗口
│   │   └── settings.py           # 设置
│   ├── controllers/              # 控制器
│   │   └── asr_controller.py     # ASR 流程控制
│   ├── config/                   # 配置管理
│   │   └── settings.py           # QSettings
│   ├── styles/                    # 样式表
│   │   └── style.qss             # QSS 样式
│   ├── resources/                 # 资源文件
│   │   └── icons/                # 图标
│   ├── pyproject.toml             # GUI 依赖
│   └── README.md                  # GUI 说明
│
├── smoco/                        # 现有：核心代码
│   ├── source/
│   ├── transcriber/
│   └── ...
│
├── whisper-local/                 # 现有：本地 Whisper
├── whisper-server/                # 现有：远程 Whisper 服务器
└── start.bat                      # 现有：启动脚本
```

---

## 7. 依赖

### smoco-gui/pyproject.toml

```toml
[project]
name = "smoco-gui"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "PyQt6>=6.6.0",
    "aiohttp>=3.9.0",
]
```

### 安装命令

```bash
# 开发模式
cd smoco-gui
pip install -e .

# 或者使用 uv
uv sync
```

---

## 8. 开发顺序

### 迭代 1: 最小可行产品（MVP）

**功能**：
- [ ] 主窗口 + 设备选择
- [ ] 音量条显示
- [ ] 开始 ASR 按钮
- [ ] 固定服务器 + 日语转录
- [ ] 转录文本显示

**不包含**：
- [ ] 服务器选择
- [ ] 设置功能
- [ ] 语言选择（固定日语）

### 迭代 2: 完整功能

**功能**：
- [ ] 服务器选择（远程/本地）
- [ ] 语言选择（日语/中文/英语）
- [ ] 设置界面
- [ ] 服务器列表管理

---

## 9. 风险和注意事项

### 9.1 技术风险

1. **PyQt6 学习曲线**：需要熟悉 Qt 信号/槽机制
2. **线程管理**：GUI 主线程与 ASR 后台线程通信
3. **资源占用**：PyQt6 应用相对较大

### 9.2 解决方案

1. **学习曲线**：参考 PyQt6 官方示例
2. **线程通信**：使用 Qt Signal/Slot，避免直接操作 UI
3. **资源占用**：优化依赖，延迟加载

---

## 10. 总结

**关键决策**：
- ✅ 使用 PyQt6（成熟、跨平台）
- ✅ 分阶段开发（5 周，5 个迭代）
- ✅ 先做 MVP，后加功能
- ✅ GUI 与现有 smoco 代码解耦

**预期结果**：
- 友好的图形界面
- 实时转录显示
- 配置持久化
- 独立可执行文件

---

## 确认事项

请确认以下设计决策是否 OK：

1. ✅ **技术栈**：PyQt6
2. ✅ **界面布局**：主窗口 + ASR 对话框 + 转录窗口 + 设置
3. ✅ **开发顺序**：5 周分 5 个阶段，先做 MVP
4. ✅ **目录结构**：smoco-gui/ 独立目录
5. ✅ **依赖**：PyQt6 + aiohttp

如有调整需求，请告知。

**确认后开始开发？**
