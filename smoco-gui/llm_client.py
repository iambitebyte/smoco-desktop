"""
LLM 客户端 - 翻译调用
"""

import sys
import json
import requests
import logging
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

# 只在开发环境中修改 sys.path
if not getattr(sys, 'frozen', False):
    _smoco_root = Path(__file__).parent.parent
    sys.path.insert(0, str(_smoco_root))

from i18n import i18n
from gui_logger import get_gui_logger

# 获取日志记录器
logger = get_gui_logger(__name__)


class LLMClient(QObject):
    """LLM 客户端"""

    def __init__(self):
        super().__init__()
        self._config = {
            "base_url": "",
            "api_key": "",
            "model": "",
        }

    def set_config(self, base_url: str, api_key: str, model: str):
        """设置配置"""
        self._config = {
            "base_url": base_url.rstrip("/"),
            "api_key": api_key,
            "model": model,
        }

    def get_config(self) -> dict:
        """获取配置"""
        return self._config.copy()

    def validate(self) -> tuple[bool, str]:
        """验证配置"""
        if not all(self._config.values()):
            return False, i18n.t("llm_config_incomplete")

        # 处理 base_url 可能包含 /v1 的情况
        base_url = self._config['base_url'].rstrip('/')
        if base_url.endswith('/v1'):
            url = f"{base_url}/chat/completions"
        else:
            url = f"{base_url}/v1/chat/completions"

        # 请求前就打印诊断信息，防止请求挂死时什么日志都没有
        logger.info(f"LLM 验证: base_url={self._config['base_url']!r}")
        logger.info(f"LLM 验证: 构造的请求 URL={url!r}")
        logger.info(f"LLM 验证: model={self._config['model']!r}")
        logger.info(f"LLM 验证: api_key 长度={len(self._config['api_key'])} 前缀={self._config['api_key'][:8]!r}...")

        # 检查代理环境变量（企业网络常见问题）
        import os
        proxy_vars = {k: v for k, v in os.environ.items() if 'proxy' in k.lower()}
        if proxy_vars:
            logger.info(f"LLM 验证: 检测到代理环境变量: {proxy_vars}")
        else:
            logger.info(f"LLM 验证: 未检测到代理环境变量")

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._config['api_key']}",
            }

            response = requests.post(
                url,
                json={
                    "model": self._config["model"],
                    "messages": [
                        {"role": "user", "content": "OK"}
                    ],
                    "temperature": 0
                },
                headers=headers,
                timeout=10.0
            )

            logger.info(f"LLM 验证: 响应状态码={response.status_code}")

            if response.status_code == 200:
                logger.info(f"LLM 验证: 成功")
                return True, i18n.t("llm_config_ok")
            else:
                logger.warning(f"LLM 验证: 响应内容={response.text[:500]!r}")
                return False, f"{i18n.t('llm_config_error')} {response.status_code}"

        except requests.exceptions.Timeout as e:
            logger.error(f"LLM 验证超时: url={url!r}, error={e}")
            return False, i18n.t("llm_config_timeout")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"LLM 验证连接错误: url={url!r}, error={e}")
            # 展开 ConnectionError 的底层原因
            if e.args:
                logger.error(f"LLM 验证: 底层原因 args={e.args!r}")
            return False, i18n.t("llm_config_connection_error")
        except Exception as e:
            logger.exception(f"LLM 验证未知异常: url={url!r}")
            return False, f"{i18n.t('llm_config_failed')}: {str(e)}"

    def translate(self, entries: list[dict], target_lang: str = "zh",
                  source_lang: str = "ja") -> tuple[bool, list, str]:
        """
        翻译文本

        Args:
            entries: 待翻译的条目列表，格式 [{"id": 1, "text": "..."}, ...]
            target_lang: 目标语言代码
            source_lang: 来源语言代码

        Returns:
            (成功, 翻译结果列表, 错误信息)
        """
        if not all(self._config.values()):
            return False, [], i18n.t("llm_not_configured")

        # 处理 base_url 可能包含 /v1 的情况
        base_url = self._config['base_url'].rstrip('/')
        if base_url.endswith('/v1'):
            url = f"{base_url}/chat/completions"
        else:
            url = f"{base_url}/v1/chat/completions"

        logger.info(f"LLM 翻译请求: url={url!r}, model={self._config['model']!r}, entries={len(entries)}")

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._config['api_key']}",
            }

            # 构建提示词
            entries_json = json.dumps(entries, ensure_ascii=False)
            src_name = _lang_name(source_lang)
            tgt_name = _lang_name(target_lang)

            system_prompt = f"""你是一个专业的{src_name}到{tgt_name}翻译助手。
请将以下{src_name}文本翻译为{tgt_name}，严格按照 JSON 格式返回。

输入格式：
{entries_json}

输出要求：
- 严格按照 JSON 数组格式返回
- 保持与输入相同的 id 顺序
- 每条翻译对应一个 id
- 只返回翻译文本，不要任何解释

输出格式：
[
  {{"id": 1, "translation": "{tgt_name}翻译1"}},
  {{"id": 2, "translation": "{tgt_name}翻译2"}},
  ...
]"""

            user_prompt = json.dumps(entries, ensure_ascii=False)

            response = requests.post(
                url,
                json={
                    "model": self._config["model"],
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.3
                },
                headers=headers,
                timeout=30.0
            )

            logger.info(f"LLM 翻译: 响应状态码={response.status_code}")

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # 解析返回的 JSON
                try:
                    translations = json.loads(content)
                    if isinstance(translations, list):
                        logger.info(f"LLM 翻译: 成功，返回 {len(translations)} 条翻译")
                        return True, translations, ""
                    else:
                        logger.warning(f"LLM 翻译: 响应不是列表: {content[:200]!r}")
                        return False, [], i18n.t("llm_invalid_response")
                except json.JSONDecodeError as e:
                    logger.warning(f"LLM 翻译: JSON 解析失败: {e}, content={content[:200]!r}")
                    return False, [], i18n.t("llm_json_parse_error")
            else:
                logger.warning(f"LLM 翻译: 响应内容={response.text[:500]!r}")
                return False, [], f"API 错误: {response.status_code}"

        except requests.exceptions.Timeout as e:
            logger.error(f"LLM 翻译超时: url={url!r}, error={e}")
            return False, [], i18n.t("llm_timeout")
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM 翻译请求异常: url={url!r}, error={e}")
            return False, [], f"请求失败: {str(e)}"
        except Exception as e:
            logger.exception(f"LLM 翻译未知异常: url={url!r}")
            return False, [], f"翻译异常: {str(e)}"


def _lang_name(lang_code: str) -> str:
    """将语言代码映射为人类可读的名称"""
    mapping = {
        "ja": "日文",
        "zh": "中文",
        "en": "英文",
        "ko": "韩文",
    }
    return mapping.get(lang_code, lang_code)


# 全局实例
_llm_client = None


def get_llm_client() -> LLMClient:
    """获取全局实例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
