# Smoco Desktop 打包说明

## 快速开始

### 推荐打包方式

```bash
# 标准版（推荐，支持远程 Whisper）
build.bat

# 完整版（包含 Local Whisper）
build_with_local_whisper.bat
```

## 打包步骤详解

### 1. 环境准备

确保已安装开发依赖：
```bash
uv add --dev pyinstaller
```

### 2. 转换图标（可选）

将 `smoco_logo_circle.png` 转换为 `.ico` 格式：
```bash
python convert_icon.py
```

### 3. 执行打包

**标准版打包（推荐）**：
```bash
build.bat
```
- ✅ 支持远程 Whisper 服务器
- ✅ 体积小（~100MB）
- ✅ 启动快速
- ❌ 不包含 Local Whisper

**完整版打包（包含 Local Whisper）**：
```bash
build_with_local_whisper.bat
```
- ✅ 包含 Local Whisper 功能
- ✅ 开箱即用
- ❌ 体积大（~400MB+）

### 4. 查看结果

打包完成后，可执行文件位于：
```
dist/SmocoDesktop/SmocoDesktop.exe
```

---

## 打包常见问题与解决方案

### 问题 1：webrtcvad 模块缺失

**错误信息**：
```
ModuleNotFoundError: No module named 'webrtcvad'
```

**原因**：
- `webrtcvad` 在代码中动态导入，PyInstaller 无法检测
- webrtcvad-wheels 包缺少元数据

**解决方案**：
1. 在 `asr_chunker.py` 中将 `webrtcvad` 导入移到顶部
2. 添加 `--hidden-import=webrtcvad` 到打包命令
3. **禁用有问题的 webrtcvad hook**

### 问题 2：webrtcvad hook 元数据错误

**错误信息**：
```
importlib.metadata.PackageNotFoundError: No package metadata was found for webrtcvad
```

**解决方案**：
临时禁用系统的 hook-webrtcvad.py：
```bash
cd .venv\Lib\site-packages\_pyinstaller_hooks_contrib\stdhooks
ren hook-webrtcvad.py hook-webrtcvad.py.disabled
```

### 问题 3：本地模块未包含

**错误信息**：
```
ModuleNotFoundError: No module named 'main_window'
```

**原因**：
- PyInstaller 静态分析无法检测到本地模块的导入
- `sys.path.insert` 在打包环境中的路径错误

**解决方案**：
1. 创建 `bundle.py` 显式导入所有本地模块
2. 使用 `--add-data` 包含所有 `.py` 文件
3. 修复 `paths.py` 中的路径查找逻辑

### 问题 4：Local Whisper 弹出 cmd 窗口

**原因**：
- subprocess.Popen 默认创建控制台窗口
- 进程被 CTRL+C 信号终止

**解决方案**：
添加 `subprocess.CREATE_NO_WINDOW` 标志：
```python
creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
subprocess.Popen(..., creationflags=creation_flags)
```

### 问题 5：路径查找错误

**错误信息**：
```
API 文件不存在: C:\Users\...\AppData\Local\Temp\whisper-local\...
```

**原因**：
- 打包环境中的 `__file__` 指向临时目录
- `Path(__file__).parent.parent` 路径计算错误

**解决方案**：
在 `paths.py` 中使用 `sys.executable` 推断项目根目录：
```python
def get_smoco_root() -> Path:
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        if (exe_dir / "_internal" / "whisper-local").exists():
            return exe_dir / "_internal"
        return exe_dir.parent
    return Path(__file__).parent.parent
```

---

## 打包脚本说明

### build.bat（标准版）

**用途**：打包支持远程 Whisper 的标准版

**特点**：
- 禁用 webrtcvad hook
- 包含所有必要的 hiddenimport
- 体积小，启动快
- 适合大多数用户

### build_with_local_whisper.bat（完整版）

**用途**：打包包含 Local Whisper 的完整版

**特点**：
- 包含 whisper-local Python 文件
- 包含 whisper-local .venv（约 267MB）
- Local Whisper 功能开箱即用
- 适合需要离线使用的用户

**依赖**：
- 需要在 `whisper-local` 目录运行过 `uv sync`
- 确保 `.venv` 目录存在

---

## 打包配置详解

### 必要的 hiddenimport

```bash
--hidden-import=PyQt6.QtCore --hidden-import=PyQt6.QtGui --hidden-import=PyQt6.QtWidgets
--hidden-import=pyaudiowpatch --hidden-import=numpy --hidden-import=scipy --hidden-import=soundfile
--hidden-import=requests --hidden-import=aiohttp --hidden-import=logging.handlers
--hidden-import=webrtcvad
```

### 数据文件

```bash
--add-data="smoco_logo_circle.png;."
--add-data="main_window.py;."
--add-data="gui_logger.py;."
--add-data="paths.py;."
# ... 其他所有 .py 文件
```

### PyInstaller 参数

- `--clean`：清理旧构建
- `--onedir`：目录模式（启动快）
- `--noconsole`：隐藏控制台
- `--icon`：应用图标

---

## 用户数据目录结构

```
C:\Users\用户名\.smoco\
├── settings.json         # 用户设置
├── logs/                 # 应用日志
│   ├── gui_YYYYMMDD.log
│   └── error_YYYYMMDD.log
└── data/                 # 转录和翻译数据
    └── YYYYMMDD_HHMMSS/  # 会话目录
        ├── session.json
        ├── transcript.json
        └── translate.json
```

---

## 发布检查清单

### 功能测试

- [ ] 应用启动正常
- [ ] 设置保存/加载正常
- [ ] 音频设备识别正常
- [ ] 远程 Whisper 转录功能正常
- [ ] LLM 翻译功能正常
- [ ] 多语言切换正常
- [ ] 错误日志记录正常

### 完整版额外检查

- [ ] Local Whisper 启动正常
- [ ] 无 cmd 窗口弹出
- [ ] 进程稳定运行

### 打包质量

- [ ] 文件大小合理
- [ ] 杀毒软件测试
- [ ] 不同 Windows 版本测试
- [ ] 不同硬件环境测试

---

## 技术说明

### 打包模式

**当前使用：目录模式（`--onedir`）**
- 启动快速
- 便于调试
- 可以查看打包内容

**单文件模式（可选）**：
```bash
pyinstaller --onefile --noconsole main.py
```
- 单个 exe 文件
- 便于分发
- 启动稍慢

### PyInstaller 工作原理

1. **分析阶段**：递归分析导入，收集依赖
2. **打包阶段**：复制文件到 dist 目录
3. **运行时**：解压到临时目录，启动 Python

### bundle.py 作用

确保 PyInstaller 能检测到所有本地模块：
```python
# 显式导入所有本地模块
import main_window, gui_logger, i18n, paths, utils, ...
from main import main

if __name__ == "__main__":
    main()
```

---

## 分发说明

### 用户要求

- **操作系统**: Windows 10/11（64位）
- **无需** Python 环境
- **无需** 安装任何依赖

### 分发内容

**标准版**：
```
SmocoDesktop/
└── SmocoDesktop.exe
```

**完整版**：
```
SmocoDesktop/
├── SmocoDesktop.exe
└── _internal/
    └── whisper-local/
        ├── .venv/          # 完整的 Python 环境
        ├── whisper_local_api.py
        └── whisper_local_transcriber.py
```

### 使用说明

1. 双击 `SmocoDesktop.exe`
2. 首次运行配置 Whisper 服务器
3. 开始使用

---

## 版本发布流程

1. 更新版本号（`pyproject.toml`）
2. 执行打包：`build.bat`
3. 本地测试打包的 exe
4. 更新 BUILD.md 和 CHANGELOG
5. 打包为 zip 分发
6. 发布到发布平台

---

## 故障排除

### 打包失败

**Q: 权限错误**
```bash
PermissionError: [WinError 5] アクセスが拒否されました
```

A: 关闭所有正在运行的 SmocoDesktop.exe 和相关进程，然后重试。

**Q: 找不到模块**
```bash
ModuleNotFoundError: No module named 'xxx'
```

A: 添加 `--hidden-import=xxx` 到打包命令。

### 运行时问题

**Q: 杀毒软件报警**
A: PyInstaller 打包的 exe 可能被误报，可以：
- 添加数字签名
- 用户添加信任列表

**Q: 缺少运行时**
A: 确保目标机器安装了 Visual C++ Redistributable

---

## 许可证

遵循项目主许可证。
