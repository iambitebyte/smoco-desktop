"""
客户端音频/文本质量过滤 —— 抑制 Whisper 在低质量音频上的幻觉。

Whisper 在静音/噪声段会“硬编”出训练集高频句（中文常见“谢谢观看”“字幕由…提供”、
日文“ありがとうございました”等），即 hallucination。当前 openvino-genai 引擎
不暴露 no_speech_prob / avg_logprob，无法在服务端按置信度过滤，故在客户端补两道闸：

  A. 能量门限：PCM RMS 过低（近静音）的 chunk 不送 Whisper，掐断静音幻觉源头。
  C. 文本启发式：拿到结果后检测重复 token / 乱码符号，明显幻觉直接丢弃。

策略偏保守：宁可漏判（放过个别可疑结果）也不误杀正常转录。所有阈值集中在本模块顶部，
配合 asr_worker 的日志可按实际场景调整。
"""

import math
from collections import Counter

import numpy as np

from gui_logger import get_gui_logger

logger = get_gui_logger(__name__)

# ---- A. 能量门限 ----
# 16-bit PCM 的 RMS 分贝（dBFS，满量程=0）。低于此值视为近静音/极低能量，丢弃。
# 参考：近场说话约 -20~-10 dBFS，远场轻声约 -36 dBFS，背景噪声约 -40~-30 dBFS，
# 几乎静音 < -50 dBFS。-45 只过滤明显静音段，远场语音保留。
LOW_ENERGY_DBFS = -45.0

# ---- C. 文本启发式 ----
MIN_TEXT_LEN = 4              # 文本短于此不判 garbled（避免误杀“是的”“いい”等短结果）
MAX_CHAR_RUN = 5              # 连续相同字符达此数 → 幻觉（“谢谢谢谢谢”“的的的的的”）
SINGLE_CHAR_DOMINANCE = 0.5   # 去标点空格后，单字符占比超此值 → 幻觉（仅在长度≥8 时判）
CORE_MIN_LEN = 8              # 参与单字符主导判断的最小有效长度
JUNK_RATIO = 0.5              # 非常规字符（控制符/罕见符号堆叠）占比超此值 → 幻觉

# 常见标点与空白（中英日），不计入“有效字符”
_PUNCT_SPACE = set(
    " \t\r\n"
    "，。、！？；：…—·"
    "“”‘’\"\"''"
    "（）()［］[]【】《》〈〉「」『』｛｝{}"
    ".,!?;:\"'-_/\\@#$%^&*+=|~`"
)


def compute_rms_dbfs(pcm_s16le: bytes) -> float:
    """计算 16-bit 有符号 PCM 的 RMS 分贝（dBFS，满量程=0，静音≈-120）。"""
    if not pcm_s16le or len(pcm_s16le) < 2:
        return -120.0
    samples = np.frombuffer(pcm_s16le, dtype="<i2").astype(np.float64)
    if samples.size == 0:
        return -120.0
    rms = math.sqrt(float(np.mean(np.square(samples)))) / 32768.0
    if rms <= 0.0:
        return -120.0
    return 20.0 * math.log10(rms)


def is_low_energy(pcm_s16le: bytes, threshold_dbfs: float = LOW_ENERGY_DBFS) -> tuple[bool, float]:
    """返回 (是否低能量需丢弃, 实际 dBFS)。"""
    dbfs = compute_rms_dbfs(pcm_s16le)
    return dbfs < threshold_dbfs, dbfs


def _max_char_run(text: str) -> int:
    """最长连续相同字符数。"""
    if not text:
        return 0
    best = run = 1
    prev = text[0]
    for ch in text[1:]:
        if ch == prev:
            run += 1
            if run > best:
                best = run
        else:
            run = 1
            prev = ch
    return best


def _is_allowed_codepoint(cp: int) -> bool:
    """是否为“正常”字符：ASCII 可见 / CJK / 假名 / 韩文 / 全角符号区。"""
    if 0x21 <= cp <= 0x7E:                       # ASCII 字母数字标点
        return True
    if 0x3000 <= cp <= 0x303F:                   # CJK 标点、全角符号
        return True
    if 0x3040 <= cp <= 0x30FF:                   # 平假名 + 片假名
        return True
    if 0x3400 <= cp <= 0x4DBF:                   # CJK 扩展 A
        return True
    if 0x4E00 <= cp <= 0x9FFF:                   # CJK 统一汉字
        return True
    if 0xAC00 <= cp <= 0xD7AF:                   # 韩文音节
        return True
    if 0xF900 <= cp <= 0xFAFF:                   # CJK 兼容汉字
        return True
    if 0xFF00 <= cp <= 0xFFEF:                   # 半全角形式
        return True
    return False


def _junk_ratio(text: str) -> float:
    """非常规字符（不在常见语言区、也非标点空白）占比。"""
    if not text:
        return 0.0
    junk = 0
    for ch in text:
        if ch in _PUNCT_SPACE or _is_allowed_codepoint(ord(ch)):
            continue
        junk += 1
    return junk / len(text)


def is_garbled_text(text: str, language: str = "") -> bool:
    """检测 Whisper 幻觉输出（连续重复 / 单字符主导 / 乱码符号）。

    Args:
        text: Whisper 返回的转录文本
        language: 当前语言代码（暂仅用于日志，检测本身语言无关、偏保守）

    Returns:
        True 表示疑似幻觉，建议丢弃。
    """
    text = (text or "").strip()
    if len(text) < MIN_TEXT_LEN:
        return False

    # 1. 连续相同字符过多（“谢谢谢谢谢”“。。。。。。”）
    if _max_char_run(text) >= MAX_CHAR_RUN:
        return True

    # 2. 去标点空格后单字符占比过高（“的的的的的的的”）
    core = [ch for ch in text if ch not in _PUNCT_SPACE]
    if len(core) >= CORE_MIN_LEN:
        most_common_count = Counter(core).most_common(1)[0][1]
        if most_common_count / len(core) > SINGLE_CHAR_DOMINANCE:
            return True

    # 3. 乱码符号占比过高（控制符/罕见符号堆叠）
    if _junk_ratio(text) > JUNK_RATIO:
        return True

    return False
