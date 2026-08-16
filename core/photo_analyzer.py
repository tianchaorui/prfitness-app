"""拍照对比分析器 - 核心差异化功能

豆包做不了的事：
1. 跨时间的照片对比
2. 基于个人数据的 AI 体态评估
3. 自动生成进度评分和建议
"""
import base64
from typing import Dict, Optional
from PIL import Image
import io

from core.ai_client import get_ai_client
from core.prompts import PHOTO_COMPARE_PROMPT, PHOTO_SINGLE_ANALYZE_PROMPT
from core.feishu_client import get_feishu_client


class PhotoAnalyzer:
    """拍照对比分析"""

    def __init__(self):
        self.ai = get_ai_client()
        self.feishu = get_feishu_client()

    @staticmethod
    def file_to_base64_data_uri(file_bytes: bytes, mime_type: str = "image/jpeg") -> str:
        """把图片文件转成 base64 data URI（DeepSeek Vision 用）"""
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        return f"data:{mime_type};base64,{b64}"

    @staticmethod
    def resize_image_if_needed(file_bytes: bytes, max_size_mb: float = 4.0) -> bytes:
        """如果图片太大或太小，先调整（DeepSeek/Qwen VL 限制）。

        - 大图：按比例缩到 ≤ max_size_mb
        - 小图：放大到至少 28×28（Qwen3-VL 要求）
        - 合适：原样返回（避免无谓的重编码）
        """
        img = Image.open(io.BytesIO(file_bytes))

        # Qwen3-VL 等多模态模型要求最小 28x28，否则报 400
        too_small = img.width < 28 or img.height < 28

        # 大图压缩到 max_size_mb 以内
        size_mb = len(file_bytes) / (1024 * 1024)
        too_big = size_mb > max_size_mb

        if not too_small and not too_big:
            return file_bytes  # 大小都合适，直接返回原字节

        if too_small:
            ratio = max(28 / img.width, 28 / img.height)
            new_size = (max(28, int(img.width * ratio)), max(28, int(img.height * ratio)))
        else:  # too_big
            ratio = (max_size_mb / size_mb) ** 0.5
            new_size = (max(28, int(img.width * ratio)), max(28, int(img.height * ratio)))
        img = img.resize(new_size, Image.LANCZOS)

        # 保存为 JPEG（质量 85）
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=85)
        return buf.getvalue()

    def analyze_single(self, image_bytes: bytes, user_context: str = "") -> Optional[Dict]:
        """分析单张照片

        Args:
            image_bytes: 图片字节流
            user_context: 用户背景（如「目标减脂，30 岁男性」）

        Returns:
            {"estimated_body_fat": ..., "body_type": ..., ...}
        """
        if not self.ai:
            return None

        image_bytes = self.resize_image_if_needed(image_bytes)
        image_url = self.file_to_base64_data_uri(image_bytes)

        prompt = PHOTO_SINGLE_ANALYZE_PROMPT
        response = self.ai.chat_with_vision(
            text=prompt,
            image_urls=[image_url],
            temperature=0.5,
            max_tokens=1500,
        )

        # 上游 API 报错时（chat_with_vision 失败会返回 "❌ ..." 字符串），
        # 把真实错误向上抛，让页面显示具体原因而不是笼统的「解析失败」
        if response.startswith("❌"):
            raise RuntimeError(response)

        # 解析 Vision 返回的 JSON
        import json
        import re

        # 清理响应文本（移除代码块标记）
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]  # 移除 ```json
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]  # 移除 ```
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]  # 移除尾部 ```
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass

        print(f"JSON 解析失败。原始响应：{response[:200]}")
        return None

    def compare_two(
        self,
        old_image_bytes: bytes,
        new_image_bytes: bytes,
        days_between: int = 7,
        user_context: str = "",
    ) -> Optional[Dict]:
        """对比两张照片

        Args:
            old_image_bytes: 旧照片
            new_image_bytes: 新照片
            days_between: 间隔天数
            user_context: 用户背景

        Returns:
            {"overall_change": ..., "progress_score": 0-100, ...}
        """
        if not self.ai:
            return None

        # 压缩图片
        old_image_bytes = self.resize_image_if_needed(old_image_bytes)
        new_image_bytes = self.resize_image_if_needed(new_image_bytes)

        old_url = self.file_to_base64_data_uri(old_image_bytes)
        new_url = self.file_to_base64_data_uri(new_image_bytes)

        # 调用 Vision
        text_prompt = PHOTO_COMPARE_PROMPT.format(
            days_between=days_between,
            user_context=user_context or "未提供",
        )
        response_text = self.ai.chat_with_vision(
            text=text_prompt,
            image_urls=[old_url, new_url],
            temperature=0.5,
            max_tokens=2000,
        )

        # 上游 API 报错时向上抛，不静默吞掉
        if response_text.startswith("❌"):
            raise RuntimeError(response_text)

        # 解析 Vision 返回的 JSON
        import json
        import re

        # 清理响应文本（移除代码块标记）
        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]  # 移除 ```json
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]  # 移除 ```
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]  # 移除尾部 ```
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # 尝试用正则表达式提取 JSON 对象
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        
        # 如果都失败了，返回 None
        print(f"JSON 解析失败。原始响应：{response_text[:200]}")
        return None

    def save_to_feishu(
        self,
        image_bytes: bytes,
        analysis: Dict,
        note: str = "",
        user_id: str = "",
    ) -> Optional[str]:
        """保存分析结果到飞书"""
        from core.config import get_config

        body_table_id = get_config("FEISHU_TABLE_BODY")
        if not self.feishu or not body_table_id:
            return None
        try:
            from datetime import datetime
            # 上传图片
            file_token = self.feishu.upload_file(image_bytes, f"body_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")

            # 保存记录（带 user_id）
            record_id = self.feishu.add_record(
                body_table_id,
                {
                    "日期": int(datetime.now().timestamp() * 1000),
                    "今日照片": [{"file_token": file_token}],
                    "备注": f"AI 评分：{analysis.get('progress_score', 'N/A')}\n{note}",
                },
                user_id=user_id,
            )
            return record_id
        except Exception as e:
            print(f"保存失败：{e}")
            return None