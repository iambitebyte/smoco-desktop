# Smoco Desktop 打包说明

## 快速开始

```bash
cd smoco-gui
build.bat
```

`build.bat` 现在打出一个**完全自包含**的发行版（~770MB）：
- 主程序 `SmocoDesktop.exe`（PyQt6 GUI + 业务逻辑）
- `whisper-local-npu/whisper-npu-api.exe`（独立 OpenVINO-genai 转写服务，PyInstaller 二次打包）
- `whisper-local-npu/whisper-small-ov/`（244MB OpenVINO IR 模型，可替换）
- 用户**无需安装 Python、无需联网**

---

## 打包步骤详解

### 1. 环境准备

确保已安装开发依赖：
```bash
uv sync --dev    # 含 pyinstaller、pytest、pillow
```

### 2. 转换图标（可选）

将 `smoco_logo_circle.png` 转换为 `.ico` 格式：
```bash
python convert_icon.py
```

### 3. 执行打包

```bash
build.bat
```

`build.bat` 内部流程：

1. **禁用 webrtcvad hook**（避免 PackageNotFoundError）
2. **主程序打包**：`uv run pyinstaller bundle.py` → `SmocoDesktop.exe`
3. **whisper-npu-api 二次打包**：在 `whisper-local-npu/` 跑 `uv sync` + `uv run --with pyinstaller pyinstaller whisper_npu_api.py`，含 `--collect-all openvino / openvino_genai / openvino_tokenizers`
4. **拷贝产物**：
   - `whisper-npu-api/` 整目录 → `dist/SmocoDesktop/whisper-local-npu/whisper-npu-api/`
   - `whisper-small-ov/` 模型 → `dist/SmocoDesktop/whisper-local-npu/whisper-small-ov/`
   - `init-whisper-npu.bat` → `dist/SmocoDesktop/`（fallback 修复脚本）
5. **末尾打印 dist 体积报告**

打包产物：

```
dist/SmocoDesktop/
├── SmocoDesktop.exe              # 主程序（~12MB）
├── _internal/                    # PyInstaller 主程序运行时（~194MB）
│   ├── python312.dll
│   ├── styles.qss                 # 全局样式表
│   └── ... (PyQt6、各业务 .py 文件)
├── whisper-local-npu/
│   ├── whisper-npu-api/          # 转写服务（独立 PyInstaller onedir）
│   │   ├── whisper-npu-api.exe
│   │   └── _internal/            # 含 openvino 等（~480MB）
│   ├── whisper-small-ov/         # OpenVINO IR 模型（244MB，可替换）
│   └── whisper_npu_api.py        # 源码参考
└── init-whisper-npu.bat          # 用户侧修复 venv 的 fallback
```

---

## 必须知道的：新增 Python 模块时如何打包

PyInstaller 不会自动发现新加的本地模块。**新增任何被运行时代码 import 的 `.py` 文件时，必须同步改两个地方**：

### `bundle.py`

显式 import 让 PyInstaller 能追踪依赖：

```python
import main_window
import gui_logger
# ...
import your_new_module   # ← 加这一行
```

### `build.bat`

加 `--hidden-import` 和 `--add-data`：

```bat
uv run pyinstaller ... ^
    --hidden-import=your_new_module ^       ← 加这一行
    ...
    --add-data="your_new_module.py;." ^     ← 加这一行
```

漏掉任一处，运行时会报 `ModuleNotFoundError: No module named 'your_new_module'`。

### 当前已打包的本地模块清单

| 文件 | 用途 |
|---|---|
| `main.py` | 应用入口 |
| `bundle.py` | PyInstaller 入口 |
| `main_window.py` | 主窗口 + 4 个 page（设备选择/转录/历史/详情） |
| `gui_logger.py` | 日志系统 |
| `i18n.py` | 多语言（中/日/英） |
| `paths.py` | 用户目录定位 |
| `utils.py` | 工具函数 |
| `audio_meter_worker.py` | 音量条 |
| `asr_worker.py` | ASR 转录控制器 |
| `asr_chunker.py` | VAD 分块 |
| `asr_logger.py` | 转录/翻译数据写入 |
| `settings_dialog.py` | 设置对话框（4 tab） |
| `startup_dialog.py` | 启动确认对话框 |
| `transcript_edit.py` | 自定义转录编辑控件 |
| `local_whisper_manager.py` | Local Whisper 子进程管理 |
| `translation_worker.py` | LLM 翻译 worker |
| `llm_client.py` | LLM HTTP 客户端 |
| `history_page.py` | 转录历史 - 会话列表 |
| `history_detail_page.py` | 转录历史 - 条目列表 + 详情弹窗 |
| `history_reader.py` | 历史数据读取层（纯 Python） |
| `log_viewer_page.py` | 应用日志查看页 |
| `styles.py` | 全局 QSS 加载器 |
| `toast.py` | Toast 通知组件 |

不需要打包的文件：
- `convert_icon.py`（独立工具脚本）
- `main_app.py`（疑似废弃入口）
- `hook-webrtcvad.py`（PyInstaller hook，build.bat 内手动处理）
- `tests/`（pytest 测试）
- `__init__.py`（目录标记）

### 数据文件

```bat
--add-data="smoco_logo_circle.png;."    # 应用 logo
--add-data="styles.qss;."               # 全局样式表（必须有）
```

---

## 打包常见问题与解决方案

### 问题 1：webrtcvad 模块缺失

**错误信息**：
```
ModuleNotFoundError: No module named 'webrtcvad'
```

**原因**：webrtcvad 在代码中动态导入，且 webrtcvad-wheels 包缺元数据。

**解决方案**：build.bat 已经处理（`--hidden-import=webrtcvad` + 禁用 hook）。

### 问题 2：webrtcvad hook 元数据错误

**错误信息**：
```
importlib.metadata.PackageNotFoundError: No package metadata was found for webrtcvad
```

**解决方案**：build.bat 已经处理（在 `.venv/.../stdhooks/` 重命名 `hook-webrtcvad.py` 为 `.disabled`，build 结束后恢复）。

### 问题 3：本地模块未包含

**错误信息**：
```
ModuleNotFoundError: No module named 'history_page'
```

**原因**：新增 `.py` 模块没同步到 `bundle.py` + `build.bat`。

**解决方案**：见上一节「新增 Python 模块时如何打包」。

### 问题 4：openvino_tokenizers.dll 加载失败

**错误信息**：
```
Cannot load library "openvino_tokenizers.dll": 126
```

**原因**：openvino 运行时动态加载 tokenizers 扩展，PyInstaller 默认不会收集。

**解决方案**：build.bat 已经处理（`--collect-all openvino_tokenizers`）。

### 问题 5：Local Whisper 跨机器不可用

**历史问题**：曾尝试拷贝 `.venv`，但 uv 创建的 venv 是跳板 exe，硬编码了开发机 base Python 路径，部署机找不到解释器。

**当前解决方案**：用 PyInstaller 把 `whisper_npu_api.py` 二次打包成独立的 `whisper-npu-api.exe`，完全自包含、跨机器零依赖。

---

## 用户数据目录结构

```
~/.smoco/
├── settings.json              # 用户设置
├── logs/                       # 应用日志
│   ├── gui_YYYYMMDD.log        # 全级别日志（10MB 轮转）
│   └── error_YYYYMMDD.log      # 仅 ERROR 及以上
└── data/                       # 转录和翻译数据
    └── YYYYMMDD_HHMMSS/        # 会话目录
        ├── metadata.json       # 会话元数据 + entries 摘要
        ├── entry_0001.json     # 单条转录记录
        ├── translate_0001.json # 单批翻译（可能含多条 id）
        └── ...
```

应用内可查看（主页 📜 按钮）：
- 文件下拉切换
- 「仅错误日志」过滤
- 显示尾部 5000 行（避免大文件卡顿）
- 自动滚到底部（最新可见）

---

## 发布检查清单

### 功能测试

- [ ] 应用启动正常（无 ModuleNotFoundError）
- [ ] 设置保存/加载正常（4 个 tab）
- [ ] 音频设备识别正常
- [ ] 远程 Whisper 转录功能正常
- [ ] **Local Whisper 启动正常**（设置 → 本地 Whisper 模型 tab → 启动服务）
- [ ] **Local Whisper 跨机器可用**（dist 拷到无 Python 的机器跑）
- [ ] LLM 翻译功能正常
- [ ] 多语言切换后所有 UI 即时刷新
- [ ] **转录历史查看**（主页 📋 → 列表 → 详情 → 弹窗）
- [ ] **导出会话**（txt + markdown）
- [ ] **快捷键**（F5 / Ctrl+H / Ctrl+L / Esc / Ctrl+E 等）
- [ ] **日志查看**（主页 📜）
- [ ] 错误日志记录正常

### 打包质量

- [ ] dist 体积在 720-800MB 范围
- [ ] 杀毒软件测试（PyInstaller exe 可能误报）
- [ ] 不同 Windows 版本测试
- [ ] 不同硬件环境测试（含/不含 Intel GPU）

---

## 技术说明

### PyInstaller 工作原理

1. **分析阶段**：递归分析 bundle.py 的 imports，收集依赖
2. **打包阶段**：复制文件到 dist 目录
3. **运行时**：解压到临时目录或当前目录，启动 Python

### bundle.py 作用

显式 import 所有本地模块，确保 PyInstaller 能检测到：

```python
import main_window
import gui_logger
# ... 所有运行时需要的模块
from main import main

if __name__ == "__main__":
    main()
```

### 全局 QSS 样式系统

- `styles.qss` 定义通用控件样式（按 objectName 分类）
- `styles.py:load_global_stylesheet(app)` 在 `main.py` 启动时调用
- 控件用 `setObjectName("primaryButton")` 等方式声明类别，删去内嵌 `setStyleSheet`

### PyInstaller 参数

- `--clean`：清理旧构建
- `--onedir`：目录模式（启动快）
- `--noconsole`：隐藏控制台
- `--icon`：应用图标
- `--collect-all <pkg>`：收集包的所有文件（含 native libs/data）

---

## 故障排除

### 打包失败

**Q: 权限错误**
```
PermissionError: [WinError 5] アクセスが拒否されました
```

A: 关闭所有正在运行的 SmocoDesktop.exe 和相关进程，然后重试。

**Q: 找不到模块**
```
ModuleNotFoundError: No module named 'xxx'
```

A: 把 `xxx` 加到 `bundle.py` 的 imports + `build.bat` 的 `--hidden-import` + `--add-data`。

### 运行时问题

**Q: 杀毒软件报警**

A: PyInstaller 打包的 exe 可能被误报，可以：
- 添加数字签名
- 用户添加信任列表

**Q: 缺少运行时**

A: 确保目标机器安装了 Visual C++ Redistributable。

**Q: Local Whisper 启动报 No Python**

A: 这是历史问题（uv venv trampoline 硬编码路径），现在用 PyInstaller 二次打包已解决。如果再次出现，检查 `whisper-local-npu/whisper-npu-api/whisper-npu-api.exe` 是否存在。

---

## 许可证

遵循项目主许可证。
