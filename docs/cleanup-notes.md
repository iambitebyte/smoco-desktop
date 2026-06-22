# 清理登记（Tech Debt / 待办）

审计过程中发现、**暂不阻塞**但值得以后清理的小问题。每条标注位置、现状、建议处理。
已处理的划掉并记 commit。

---

## 2026-06-22 审计 smoco-gui 采集/转写循环退出逻辑时发现

> 背景：排查 `Pipeline._capture_loop` 死循环 bug（已于 `fix/pipeline-eof-hang` 修复）
> 时，顺带审了 smoco-gui 自己的采集/转写/关闭路径。GUI 的循环**没有**同类"停不下来"
> 隐患（详见各条），以下均为防御性/代码卫生项，非 bug。

### 1. `smoco/source/wasapi.py`：两个 `read_frame` 定义，前者是死代码

- **现状**：`WASAPILoopbackSource` 里有两份 `read_frame`（约 `:173` 和 `:185`）。
  第二份（`self._frames.get(timeout=0.1)`）覆盖第一份（`timeout=1.0`），第一份永不执行。
- **风险**：低。行为正确（生效的是 0.1s 超时版）。但留死代码易让人改错那份。
- **建议**：删除 `:173` 那份死定义，只保留 0.1s 超时版。

### 2. `smoco-gui/audio_meter_worker.py` / `asr_worker.py`：`_thread.wait()` 无超时

- **现状**：`AudioMeterController.stop()`（`audio_meter_worker.py:111`）与
  `ASRController.stop()`（`asr_worker.py:197`）调用 `self._thread.wait()` 未传 timeout。
- **风险**：低。实际 worker 线程都能在 ≤0.1s（meter）/ 立即（asr）退出，`wait()` 会很快返回。
- **建议**：加兜底超时，如 `self._thread.wait(timeout=2000)`（2s），避免任何未预见卡住时
  把 GUI 线程一起拖死。

### 3. `smoco-gui/asr_worker.py`：关闭时在途 HTTP 请求最多 ~10s 才排干

- **现状**：`ASRWorker.stop()` 用 `executor.shutdown(wait=False)` 不等线程池；
  每个 `requests.post(timeout=10.0)`。最坏情况进程退出前要等约 10s 排干在途请求。
- **风险**：低。有上限、非卡死。仅关闭瞬间可能略慢。
- **建议**：可接受现状；若想更利落，可在关闭时记录/丢弃在途任务，或缩短超时。

---

<!-- 模板：
### N. <位置>：<一句话标题>
- **现状**：
- **风险**：
- **建议**：
-->
