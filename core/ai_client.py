"""DeepSeek API 封装

DeepSeek 兼容 OpenAI SDK，用法类似。
"""
from typing import List, Optional, Dict, Any
from openai import OpenAI

from core.config import get_config


class DeepSeekClient:
    """DeepSeek API 客户端"""

    def __init__(self):
        # 动态获取配置，避免模块初始化时的缓存问题
        self.api_key = get_config("DEEPSEEK_API_KEY")
        self.base_url = get_config("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = get_config("DEEPSEEK_MODEL", "deepseek-chat")
        # 视觉模型独立配置；未设时回落为 model（向后兼容）
        self.vision_model = get_config("DEEPSEEK_VISION_MODEL", self.model)

        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY 未配置")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs,
    ) -> str:
        """普通对话

        Args:
            messages: [{"role": "user/system/assistant", "content": "..."}]
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ AI 调用失败：{str(e)}"

    def chat_with_vision(
        self,
        text: str,
        image_urls: List[str],
        temperature: float = 0.5,
        max_tokens: int = 2000,
    ) -> str:
        """Vision 对话（支持图片分析）

        Args:
            text: 文本 prompt
            image_urls: 图片 URL 列表（支持 http URL 或 base64 data URI）
        """
        content = [{"type": "text", "text": text}]
        for url in image_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": url}
            })

        try:
            response = self.client.chat.completions.create(
                model=self.vision_model,  # 用专用视觉模型；未设时已回落为 model
                messages=[{"role": "user", "content": content}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Vision 调用失败：{str(e)}"

    def chat_json(
        self,
        prompt: str,
        temperature: float = 0.5,
        max_tokens: int = 2000,
    ) -> Optional[Dict[str, Any]]:
        """让 AI 输出 JSON 并解析

        Returns:
            解析后的 dict，失败返回 None
        """
        import json
        import re

        response = self.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 尝试提取 JSON（兼容 AI 在 JSON 外加 ```json 块）
        try:
            # 直接尝试解析
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 提取 ```json ... ``` 块
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 提取第一个 { ... } 块
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return None


# 全局单例
_client: Optional[DeepSeekClient] = None
_last_error: Optional[str] = None


def get_ai_client() -> Optional[DeepSeekClient]:
    """获取 AI 客户端单例（如果 key 未配置返回 None）。

    失败原因可通过 get_ai_last_error() 拿到，方便页面告诉用户具体缺什么。
    """
    global _client, _last_error
    if _client is None:
        try:
            _client = DeepSeekClient()
            _last_error = None  # 成功了清空
        except Exception as e:
            _last_error = f"{type(e).__name__}: {e}"
            print(f"[AI Client] 初始化失败: {_last_error}", flush=True)
            return None
    return _client


def get_ai_last_error() -> Optional[str]:
    """最近一次 AI 客户端初始化失败的原因。成功时返回 None。"""
    return _last_error