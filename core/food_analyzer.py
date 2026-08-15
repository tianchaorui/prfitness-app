"""食物图片识别 → 卡路里估算

上传一张食物照片，AI 识别图中食物、估算重量、给出卡路里和三大宏量营养素。
"""
import json
import re
from typing import Optional, Dict, List

from core.ai_client import get_ai_client
from core.photo_analyzer import PhotoAnalyzer
from core.prompts import FOOD_CALORIE_PROMPT


class FoodAnalyzer:
    """食物图片识别 + 营养估算"""

    def __init__(self):
        self.ai = get_ai_client()
        # 复用 PhotoAnalyzer 的图片预处理（base64 + 压缩）
        self._photo_helper = PhotoAnalyzer()

    def analyze_food(
        self,
        image_bytes: bytes,
        user_goal: str = "保持健康",
    ) -> Optional[Dict]:
        """分析一张食物照片，返回营养估算。

        Args:
            image_bytes: 食物照片的字节流
            user_goal: 用户健身目标（增肌/减脂/...），影响 AI 给出的建议

        Returns:
            {
                "food_items": [{"name", "estimated_weight_g", "calories"}],
                "total_calories": int,
                "total_protein_g": float,
                "total_carbs_g": float,
                "total_fat_g": float,
                "health_assessment": str,
                "suggestion": str,
            }
            解析失败返回 None
        """
        if not self.ai:
            return None

        # 压缩 + 转 base64
        image_bytes = self._photo_helper.resize_image_if_needed(image_bytes)
        image_url = PhotoAnalyzer.file_to_base64_data_uri(image_bytes)

        prompt = FOOD_CALORIE_PROMPT.format(user_goal=user_goal or "未提供")

        response = self.ai.chat_with_vision(
            text=prompt,
            image_urls=[image_url],
            temperature=0.3,  # 营养估算需要确定性，温度调低
            max_tokens=1500,
        )

        return self._parse_food_response(response)

    @staticmethod
    def _parse_food_response(response: str) -> Optional[Dict]:
        """解析 AI 返回的食物 JSON（带代码块/裸 JSON/正则三种兜底）。"""
        # 检查上游是否报错
        if response.startswith("❌"):
            return None

        # 清掉 ```json 围栏
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # 1. 直接解析
        try:
            data = json.loads(cleaned)
            return FoodAnalyzer._normalize_food_data(data)
        except json.JSONDecodeError:
            pass

        # 2. 抽取第一个 { ... }
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                return FoodAnalyzer._normalize_food_data(data)
            except json.JSONDecodeError:
                pass

        return None

    @staticmethod
    def _normalize_food_data(data: Dict) -> Dict:
        """规整化字段，确保下游 UI 拿到一致的 key。"""
        food_items = data.get("food_items") or []
        normalized_items: List[Dict] = []
        for item in food_items:
            if not isinstance(item, dict):
                continue
            raw_name = item.get("name")
            name = str(raw_name) if raw_name not in (None, "") else "未知"
            normalized_items.append({
                "name": name,
                "estimated_weight_g": _to_float(item.get("estimated_weight_g")),
                "calories": _to_float(item.get("calories")),
            })

        return {
            "food_items": normalized_items,
            "total_calories": _to_float(data.get("total_calories")),
            "total_protein_g": _to_float(data.get("total_protein_g")),
            "total_carbs_g": _to_float(data.get("total_carbs_g")),
            "total_fat_g": _to_float(data.get("total_fat_g")),
            "health_assessment": str(data.get("health_assessment", "")),
            "suggestion": str(data.get("suggestion", "")),
        }


def _to_float(value) -> float:
    """把 AI 返回的值（可能是 int / str / None）安全转成 float。"""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (ValueError, AttributeError):
        return 0.0