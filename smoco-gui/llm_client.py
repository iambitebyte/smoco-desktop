"""
LLM 客户端 - 翻译调用
"""

import sys
import json
import requests
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

# 添加父目录到 Python 路径
_smoco_root = Path(__file__).parent.parent
sys.path.insert(0, str(_smoco_root))

from i18n import i18n


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

        try:
            # 处理 base_url 可能包含 /v1 的情况
            base_url = self._config['base_url'].rstrip('/')
            if base_url.endswith('/v1'):
                url = f"{base_url}/chat/completions"
            else:
                url = f"{base_url}/v1/chat/completions"

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
            print(f"[LLM 验证] 请求 URL: {url}")
            print(f"[LLM 验证] 模型: {self._config['model']}")

            if response.status_code == 200:
                return True, i18n.t("llm_config_ok")
            else:
                print(f"[LLM 验证] 响应状态码: {response.status_code}")
                print(f"[LLM 验证] 响应内容: {response.text[:200]}")
                return False, f"{i18n.t('llm_config_error')} {response.status_code}"

        except requests.exceptions.Timeout:
            return False, i18n.t("llm_config_timeout")
        except requests.exceptions.ConnectionError:
            return False, i18n.t("llm_config_connection_error")
        except Exception as e:
            return False, f"{i18n.t('llm_config_failed')}: {str(e)}"

    def translate(self, entries: list[dict], target_lang: str = "zh") -> tuple[bool, list, str]:
        """
        翻译文本

        Args:
            entries: 待翻译的条目列表，格式 [{"id": 1, "text": "..."}, ...]
            target_lang: 目标语言

        Returns:
            (成功, 翻译结果列表, 错误信息)
        """
        if not all(self._config.values()):
            return False, [], i18n.t("llm_not_configured")

        try:
            # 处理 base_url 可能包含 /v1 的情况
            base_url = self._config['base_url'].rstrip('/')
            if base_url.endswith('/v1'):
                url = f"{base_url}/chat/completions"
            else:
                url = f"{base_url}/v1/chat/completions"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._config['api_key']}",
            }

            # 构建提示词
            entries_json = json.dumps(entries, ensure_ascii=False)
            target_lang_name = "中文" if target_lang == "zh" else target_lang

            system_prompt = f"""你是一个专业的日文到{target_lang_name}翻译助手。
请将以下日文文本翻译为{target_lang_name}，严格按照 JSON 格式返回。

输入格式：
{entries_json}

输出要求：
- 严格按照 JSON 数组格式返回
- 保持与输入相同的 id 顺序
- 每条翻译对应一个 id
- 只返回翻译文本，不要任何解释

输出格式：
[
  {{"id": 1, "translation": "{target_lang_name}翻译1"}},
  {{"id": 2, "translation": "{target_lang_name}翻译2"}},
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

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # 解析返回的 JSON
                try:
                    translations = json.loads(content)
                    if isinstance(translations, list):
                        return True, translations, ""
                    else:
                        return False, [], i18n.t("llm_invalid_response")
                except json.JSONDecodeError:
                    return False, [], i18n.t("llm_json_parse_error")
            else:
                return False, [], f"API 错误: {response.status_code}"

        except requests.exceptions.Timeout:
            return False, [], i18n.t("llm_timeout")
        except requests.exceptions.RequestException as e:
            return False, [], f"请求失败: {str(e)}"
        except Exception as e:
            return False, [], f"翻译异常: {str(e)}"


# 全局实例
_llm_client = None


def get_llm_client() -> LLMClient:
    """获取全局实例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
