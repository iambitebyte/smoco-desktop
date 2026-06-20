# Whisper 本地转写器

在 Windows 上运行 Whisper 本地转写，使用 faster-whisper 和 CPU。

## 安装

```bash
cd whisper-local

# 使用 uv 同步依赖
uv sync
```

## 快速启动

### 方法 1：交互式模式（推荐）

双击 `start.bat`，然后：
1. 选择模型（1-7）
2. 选择语言（日语、中文、英语等）
3. 首次运行会自动下载模型
4. 模型就绪后，可转写音频文件

### 方法 2：命令行

```bash
# 转写音频文件
uv run python whisper_local_transcriber.py --model medium --language ja --audio-file test.wav
```

**模型说明：**
- **推荐**：`medium`（平衡）、`large-v3-turbo`（快速准确）、`distil-large-v3`（更快）
- **快速**：`tiny`, `base`
- **高准确率**：`large-v3`

## 模型选择

| 模型 | 大小 | 速度 | 准确率 | 推荐 |
|------|------|------|--------|------|
| tiny | ~73M | 最快 | 较低 | 测试用 |
| base | ~140M | 很快 | 一般 | - |
| small | ~460M | 快 | 较好 | - |
| **medium** | ~1.5G | 中等 | 好 | **推荐** |
| large-v3-turbo | ~3.3M | 快 | 很好 | **推荐** |
| distil-large-v3 | ~3.3M | 很快 | 很好 | **推荐** |
| large-v3 | ~2.9G | 慢 | 最好 | 高准确率 |

## CPU 优化

默认使用 `int8` 量化，显著降低 CPU 占用。首次运行会自动下载模型到缓存目录：
- Windows: `C:\Users\<用户>\.cache\huggingface\hub\`
- 下载大小：medium 约 1.5G，large-v3-turbo 约 3.3G

## API 服务器模式

提供 HTTP API 服务供 smoco 调用，与 `whisper-server` 功能相同但在本地 CPU 运行。

### 启动 API 服务器

```bash
# 方式 1：交互式配置（推荐）
uv run python whisper_local_api.py --interactive

# 方式 2：命令行
uv run python whisper_local_api.py --model medium --language ja --port 8000
```

或双击 `start-api.bat` 启动。

### API 端点

- `GET /health` - 健康检查
- `POST /transcribe?language=ja` - 转写音频

### 与 smoco 集成

```bash
# 终端 1：启动本地 API 服务器
cd whisper-local
uv run python whisper_local_api.py --interactive

# 终端 2：运行 smoco
uv run smoco run --wasapi --meter --whisper-local-api --whisper-lang ja
```

## 语言支持

交互式菜单支持：
- 日语 (ja)
- 中文 (zh)
- 英语 (en)
- 韩语 (ko)
- 法语 (fr)
- 德语 (de)
- 西班牙语 (es)

Whisper 共支持 99 种语言。

## 与 smoco 集成

在 smoco 中使用本地 Whisper：

```bash
# Windows 上
uv run smoco run --wasapi --meter --whisper-local --whisper-model medium --whisper-lang ja
```
