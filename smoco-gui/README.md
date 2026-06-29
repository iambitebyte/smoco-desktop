# Smoco Desktop GUI

Smoco Desktop 的图形界面版本 - Windows 系统音频实时转录工具。

## 功能特性

- ✅ **品牌展示** - Logo 图标显示（界面 + 任务栏）
- ✅ **多语言界面** - 支持简体中文、日本語、English，切换后所有 UI 即时刷新
- ✅ **服务器管理** - 可配置多个 Whisper 服务器，支持健康检查
- ✅ **设备选择** - 可视化 WASAPI 音频设备列表
- ✅ **实时音量条** - 转录页面紧凑型音频电平显示
- ✅ **VAD 断句** - 智能语音活动检测，按停顿自动分句（可配置）
- ✅ **实时转录** - Whisper API 实时语音转文本
- ✅ **实时翻译** - LLM 异步翻译，支持上下文理解
- ✅ **时间戳显示** - 每行转录文本显示 00:00:00 格式时间戳
- ✅ **异步处理** - 多线程音频采集和 HTTP 请求，UI 不卡顿
- ✅ **转录交互** - 右键复制文本（含/不含时间戳）
- ✅ **数据日志** - 自动保存转录数据和翻译结果到用户目录（JSON 格式）
- ✅ **转录历史** - 应用内查看历史会话与单条详情，支持分页/导出/复制
- ✅ **应用日志查看** - 应用内查看 `~/.smoco/logs/`，无需翻文件系统
- ✅ **快捷键** - 开始/停止/翻页/复制/打开历史/日志/设置 全键盘操作
- ✅ **辅助功能** - 主要控件含 `accessibleName`，兼容读屏软件
- ✅ **Toast 通知** - 操作即时反馈（复制成功、导出完成）
- ✅ **全局 QSS 样式** - 抽出 `styles.qss`，控件按 objectName 统一样式
- ✅ **Local Whisper NPU** - 自带 whisper-npu-api.exe，零安装零联网

## 安装

```bash
cd smoco-gui

# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -e .
```

## 运行

```bash
uv run python main.py
```

## 使用说明

### 1. 设备选择页面
- 从列表中选择要采集的扬声器设备
- 右上角按钮（从左到右）：📋 历史 / 📜 日志 / ⚙ 设置
- 语言选择器切换界面语言（切换后所有 UI 即时刷新）
- 点击「开始转录」进入启动确认页面

> 如果既没有外部 Whisper 服务器也没启动 Local Whisper，会提示后自动打开设置对话框并定位到「本地 Whisper 模型」选项卡。

### 2. 启动确认对话框
点击「开始转录」后显示：
- **服务器选择** - 从已配置的服务器列表中选择
  - 自动选中上次使用的服务器
  - 可切换到其他服务器
- **服务状态** - 自动调用选中服务器的 `/health` 端点
  - ✓ 绿色：服务正常，可继续
  - ✗ 红色：服务异常，需选择其他服务器
- **语言选择** - 选择本次转录的语言：
  - 日语
  - 英语
- **翻译语言选择** - 选择是否启用翻译：
  - 中文翻译（需要 LLM 配置正确）
  - 无翻译
  - LLM 验证失败时自动禁用翻译选项
- 健康检查通过后「开始转录」按钮才可点击

### 3. 设置对话框
点击⚙按钮可配置（4 个选项卡）：
- **Whisper 服务器列表**
  - 添加/删除服务器
  - 设置默认服务器（✓ 标记）
  - 可为服务器命名
- **VAD 参数**：
  - Silence Duration: 静音多久后断句（默认 600ms）
  - Max Chunk Duration: 最大块时长（默认 15000ms）
  - Min Chunk Duration: 最小块时长（默认 500ms）
  - Padding Duration: 断句后保留的尾部静音（默认 100ms）
- **本地 Whisper 模型**（GPU/CPU）：
  - 启动/停止内嵌 whisper-npu-api.exe 子进程
  - 端口配置（默认 8000）
  - 运行设备：自动检测（优先 GPU）/ GPU / CPU
  - 状态指示：已停止 / 启动中 / 运行中
- **LLM 配置**（用于翻译功能）：
  - Base URL: LLM API 地址（OpenAI 兼容）
  - API Key: API 密钥
  - Model ID: 模型标识（如 gpt-4o）
  - 翻译上下文条数：前 N 条转录作为上下文（默认 5）
  - 验证按钮：测试配置是否正确

设置对话框支持指定初始选项卡（如 `_show_settings(initial_tab=SettingsDialog.TAB_LOCAL_WHISPER)`）。
设置自动保存到 `~/.smoco/settings.json`。

### 4. 转录页面
- 顶部显示紧凑型音量条，实时显示音频电平
- 转录文本以表格形式显示，包含三列：
  - **时间戳**：00:00:00 格式
  - **转录文本**：Whisper 识别结果
  - **翻译文本**：LLM 翻译结果（如果启用）
- 表格单元格支持自动换行，行高根据内容自适应
- 时间戳表示该段音频从录制开始的时间偏移
- 点击「← 返回」或「停止」结束录制

### 5. 转录历史页面
点击主页顶部 📋 按钮进入：
- **会话列表**：按时间倒序，分页（每页 20 条），双击或 Enter 进入详情
- **会话详情**：单会话的所有转录条目表格（时间/原文/译文预览），分页（每页 50 条）
- **单条详情**：双击条目弹窗，显示完整原文 + 译文，支持「复制原文/复制译文」按钮
- **导出**：将会话导出为 `.txt` 或 `.md`（含原文 + 译文）
- 数据来自 `~/.smoco/data/YYYYMMDD_HHMMSS/`，译文按最新版本显示

### 6. 日志查看页面
点击主页顶部 📜 按钮进入：
- 文件下拉：列出 `~/.smoco/logs/` 下的 `gui_*.log` / `error_*.log`（按日期倒序）
- 「仅错误日志」切换
- 显示文件**尾部 5000 行**（最新内容），自动滚到底
- 异步加载，不卡 UI
- 「打开日志目录」调系统文件管理器
- 状态栏：`显示最近 N / M 行 · 文件大小 X KB`

## 快捷键

| 页面 | 快捷键 | 动作 |
|---|---|---|
| 主页 | `F5` | 开始转录 |
| 主页 | `Ctrl+R` | 刷新设备列表 |
| 主页 | `Ctrl+,` | 打开设置 |
| 主页 | `Ctrl+H` | 打开转录历史 |
| 主页 | `Ctrl+L` | 打开日志 |
| 转录页 | `Esc` | 停止录制 |
| 历史列表 | `Esc` | 返回主页 |
| 历史列表 | `←` / `→` | 翻页 |
| 历史列表 | `Enter` | 进入选中会话 |
| 历史详情 | `Esc` | 返回列表 |
| 历史详情 | `←` / `→` | 翻页 |
| 历史详情 | `Ctrl+E` | 导出当前会话 |
| 历史详情 | `Enter` | 弹出选中条目详情 |
| 详情弹窗 | `Ctrl+1` | 复制原文 |
| 详情弹窗 | `Ctrl+2` | 复制译文 |

## 界面预览

```
┌─────────────────────────────────────────┐
│ 选择音频设备              [语言: 简体中文▼]│
│ 选择要采集的扬声器设备：                 │
│ ┌─────────────────────────────────────┐│
│ │ LG ULTRAFINE (Display Audio)        ││
│ │ スピーカー (Realtek Audio) ✓       ││
│ └─────────────────────────────────────┘│
│                  [开始转录]             │
└─────────────────────────────────────────┘

           ↓ 点击开始转录 ↓

┌─────────────────────────────────────────┐
│           启动转录                      │
├─────────────────────────────────────────┤
│ 选择 Whisper 服务器:                    │
│ ┌─────────────────────────────────────┐│
│ │ GPU 服务器 - http://server1:10060  ▼│
│ │ 本地服务器 - http://localhost:8888  ││
│ └─────────────────────────────────────┘│
│ 当前服务器:                             │
│ ┌─────────────────────────────────────┐│
│ │ http://server1:10060                ││
│ └─────────────────────────────────────┘│
│ 服务状态: ✓ 服务正常                    │
│                                         │
│ 选择转录语言:                           │
│ ○ 日语              ○ 英语              │
│                                         │
│ 选择翻译语言:                           │
│ ○ 中文翻译          ○ 无翻译            │
│                                         │
│          [开始转录]        [取消]        │
└─────────────────────────────────────────┘

           ↓ 健康检查通过后 ↓

┌─────────────────────────────────────────┐
│ [Logo]  实时转录              [停止]    │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │ ← 音量条
│ ┌─────────────────────────────────────┐│
│ │ 时间   转录文本        翻译          ││
│ ├─────────────────────────────────────┤│
│ │00:00:03 こんにちは、... 你好，今天...││
│ │00:00:15 ありがとう... 谢谢          ││ ← 右键可复制
│ │00:00:28 それでは... 那么            ││
│ └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

### 运行说明

**Windows 下运行：**
```bash
cd smoco-gui
uv run python main.py
```

**注意：**
- 窗口图标已设置为 Smoco Logo
- 任务栏图标：直接运行 Python 脚本时可能仍显示 Python 图标（Windows 限制）
- 打包为 exe 后任务栏图标将正确显示
- 窗口左上角图标始终正确显示 ```

### 转录文本交互

在转录显示区，可以：
- **右键菜单**：
  - `复制转录文本` - 只复制文本内容（不含时间戳）
  - `复制带时间戳` - 复制完整行（含时间戳）
- **选择复制**：选中任意文本后可通过右键菜单复制

## 技术架构

- **GUI 框架**: PyQt6
- **音频采集**: WASAPI Loopback (pyaudiowpatch)
- **VAD 分块**: WebRTC Voice Activity Detection
- **ASR 引擎**: Whisper API（远程）或内嵌 whisper-npu-api.exe（OpenVINO-genai）
- **翻译引擎**: LLM API（OpenAI 兼容，支持上下文理解）
- **HTTP 客户端**: requests + 线程池异步处理
- **音频格式**: 16kHz mono S16LE
- **全局样式**: `styles.qss` 通过 objectName 分类，`QApplication.setStyleSheet` 加载
- **测试**: pytest + monkeypatch + tmp_path（`tests/test_history_reader.py`）

## 配置

### 首次使用

首次使用需要配置：
1. **Whisper 服务器**（必需）：
   - 点击右上角 ⚙ 按钮打开设置
   - 在服务器列表中添加 Whisper API 服务器
   - 可选：为服务器命名（如 "GPU 服务器"、"本地服务器"）
   - 可添加多个服务器，选择其中一个设为默认
   - 点击保存

2. **LLM 翻译配置**（可选，用于翻译功能）：
   - 在设置对话框的 LLM 配置选项卡中填写：
     - Base URL: LLM API 地址（如 https://api.openai.com/v1）
     - API Key: API 密钥
     - Model ID: 模型标识（如 gpt-4o）
   - 点击「验证配置」按钮测试连接
   - 验证成功后点击保存

### 设置文件位置

- **设置文件**: `~/.smoco/settings.json`
  - Windows: `C:\Users\YourUsername\.smoco\settings.json`
  - Linux/Mac: `~/.smoco/settings.json`

### ASR 数据日志

每次转录会话自动保存到 `~/.smoco/data/`，目录结构如下：

```
~/.smoco/data/
├── 20250620_143022/           # 会话开始时间 (YYYYMMDD_HHMMSS)
│   ├── metadata.json           # 会话元数据
│   ├── entry_0001.json         # 第1次转录记录
│   ├── entry_0002.json         # 第2次转录记录
│   ├── translate_0001.json     # 第1次翻译记录（如果启用）
│   ├── translate_0002.json     # 第2次翻译记录（如果启用）
│   └── ...
└── 20250620_151030/
    ├── metadata.json
    └── ...
```

#### metadata.json 格式

```json
{
  "start_time": "2025-06-20T14:30:22.123456",
  "last_update": "2025-06-20T14:35:10.789012",
  "total_entries": 15,
  "translate_lang": "zh",
  "entries": [
    {
      "id": 1,
      "timestamp": "2025-06-20T14:30:25.123456",
      "text": "こんにちは、今日は...",
      "translation": "你好，今天..."
    },
    {
      "id": 2,
      "timestamp": "2025-06-20T14:30:40.789012",
      "text": "ありがとうございます",
      "translation": "谢谢"
    }
  ]
}
```

**字段说明：**
- `start_time`: 会话开始时间 (ISO 8601)
- `last_update`: 最后一次转录时间 (ISO 8601)
- `total_entries`: 总转录次数
- `translate_lang`: 翻译语言代码（zh/en/等，未启用翻译时为 null）
- `entries`: 转录摘要列表（只包含 ID、时间戳、文本和翻译预览）

#### entry_XXXX.json 格式

每次 Whisper API 调用生成一个独立文件：

```json
{
  "id": 1,
  "timestamp": "2025-06-20T14:30:25.123456",
  "chunk_size_bytes": 48000,
  "api_url": "http://server1:10060",
  "language": "ja",
  "processing_time_seconds": 1.234,
  "response_text": "こんにちは、今日は..."
}
```

**字段说明：**
- `id`: 本次转录序号（从1开始递增）
- `timestamp`: 转录发生时间 (ISO 8601)
- `chunk_size_bytes`: 音频块大小（字节）
- `api_url`: 使用的 Whisper API 地址
- `language`: 转录语言代码（ja/en/zh）
- `processing_time_seconds`: API 处理时长（秒，保留3位小数）
- `response_text`: Whisper 返回的完整转录文本

#### translate_XXXX.json 格式

每次 LLM 翻译生成一个独立文件：

```json
[
  {
    "id": 1,
    "translation": "你好，今天..."
  },
  {
    "id": 2,
    "translation": "谢谢"
  }
]
```

**字段说明：**
- `id`: 转录条目序号（对应 entry_XXXX.json 中的 id）
- `translation`: 翻译后的文本

**注意事项：**
- 文件名格式 `entry_0001.json`，序号固定4位，前面补零
- 所有 JSON 文件使用 UTF-8 编码
- 时间戳均为本地时区
- 每次启动"开始转录"创建新会话目录
- 点击"停止"会话结束，metadata.json 更新最终状态

**设置文件结构（~/.smoco/settings.json）：**
```json
{
  "servers": [
    {
      "url": "http://server1:10060",
      "name": "GPU 服务器",
      "default": true
    },
    {
      "url": "http://localhost:8888",
      "name": "本地服务器",
      "default": false
    }
  ],
  "last_server": "http://server1:10060",
  "vad": {
    "silence_ms": 600,
    "max_chunk_ms": 15000,
    "min_chunk_ms": 500,
    "pad_ms": 100
  },
  "llm": {
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-...",
    "model": "gpt-4o"
  }
}
```

### VAD 参数

可在设置对话框中调整分块参数：

```python
# AudioChunker 参数
silence_ms=600      # 静音 600ms 后断句
max_chunk_ms=15000  # 最大 15 秒
min_chunk_ms=500    # 最小 500ms
```

## 打包为可执行文件

Smoco Desktop 可以打包为 Windows 可执行文件，无需 Python 环境即可运行。

### 快速打包

```bash
cd smoco-gui
build.bat
```

`build.bat` 会：
1. 用 PyInstaller 打包主程序（`bundle.py` → `SmocoDesktop.exe`）
2. 用 PyInstaller 二次打包 whisper-npu-api.exe（含 openvino/openvino-genai 等依赖）
3. 拷贝模型文件 `whisper-small-ov/` 到 `dist/SmocoDesktop/whisper-local-npu/`

### 分发版本（~770MB）

完全自包含：
- 主程序 `SmocoDesktop.exe`（PyQt6 等）
- `whisper-local-npu/whisper-npu-api.exe`（独立 OpenVINO-genai 转写服务）
- `whisper-small-ov/` 模型（244MB，可替换）
- 用户**无需安装 Python、无需联网**

详细打包说明请参阅 [BUILD.md](BUILD.md)。

### 用户要求

- **操作系统**: Windows 10/11（64位）
- **无需** Python 环境
- **无需** 安装任何依赖

详见 [BUILD.md](BUILD.md) 了解更多打包细节。

## 依赖

- PyQt6 >= 6.6.0
- pyaudiowpatch == 0.2.12.8 (Windows only)
- numpy >= 1.24
- scipy >= 1.10
- soundfile >= 0.12
- webrtcvad-wheels >= 2.0.11
- requests >= 2.31

**注意：** LLM 翻译功能使用 requests 库调用 OpenAI 兼容 API，无需额外依赖。

## 开发状态

- ✅ 核心 ASR 转录功能
- ✅ 品牌 Logo（界面 + 任务栏）
- ✅ 多语言界面（中文/日文/英文），切换后 UI 即时刷新
- ✅ 时间戳显示（HH:MM:SS 格式）
- ✅ 设置界面（4 个 tab：服务器 / VAD / 本地 Whisper / LLM）
- ✅ LLM 翻译功能（异步处理 + 上下文理解）
- ✅ 表格显示（时间戳 + 转录 + 翻译）
- ✅ ASR 数据日志（自动保存到用户目录）
- ✅ 跨平台路径支持（Windows/Linux）
- ✅ 启动对话框（服务器选择 + 健康检查 + 语言选择 + 翻译选项）
- ✅ 转录文本交互（右键复制功能）
- ✅ 本地 Whisper NPU（whisper-npu-api.exe 子进程，含 OpenVINO-genai）
- ✅ 转录历史查看（session/entry 两级浏览 + 分页 + 导出 + 复制）
- ✅ 应用日志查看（应用内查看 `~/.smoco/logs/`）
- ✅ 快捷键覆盖（开始/停止/翻页/复制/打开历史/日志/设置）
- ✅ 辅助功能（accessibleName 标注图标按钮/表格/列表）
- ✅ Toast 通知（操作即时反馈）
- ✅ 全局 QSS 样式系统（styles.qss）
- ✅ pytest 单元测试（history_reader 20 个用例）
- ✅ Windows 可执行文件打包（自包含分发版）
