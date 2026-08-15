"""core/food_analyzer.py 测试

覆盖：
- 解析 AI 返回的食物 JSON（裸 JSON / ```json 块 / 错误前缀）
- 字段规整化（缺字段、类型异常）
- analyze_food 端到端（mock ai + 验证图片处理）
"""
import json
from unittest.mock import MagicMock, patch

from core.food_analyzer import FoodAnalyzer, _to_float


class TestParseFoodResponse:
    """_parse_food_response 的 JSON 解析路径"""

    @staticmethod
    def _good_payload():
        return {
            "food_items": [
                {"name": "鸡胸肉", "estimated_weight_g": 150, "calories": 248},
                {"name": "糙米饭", "estimated_weight_g": 200, "calories": 220},
            ],
            "total_calories": 468,
            "total_protein_g": 45,
            "total_carbs_g": 50,
            "total_fat_g": 6,
            "health_assessment": "蛋白质充足，适合增肌",
            "suggestion": "可以加一份蔬菜补充纤维",
        }

    def test_parses_plain_json(self):
        result = FoodAnalyzer._parse_food_response(json.dumps(self._good_payload(), ensure_ascii=False))
        assert result is not None
        assert len(result["food_items"]) == 2
        assert result["total_calories"] == 468

    def test_parses_json_code_block(self):
        text = "```json\n" + json.dumps(self._good_payload(), ensure_ascii=False) + "\n```"
        result = FoodAnalyzer._parse_food_response(text)
        assert result is not None
        assert result["total_protein_g"] == 45

    def test_parses_bare_code_block(self):
        text = "```\n" + json.dumps(self._good_payload()) + "\n```"
        result = FoodAnalyzer._parse_food_response(text)
        assert result is not None

    def test_returns_none_on_upstream_error_prefix(self):
        result = FoodAnalyzer._parse_food_response("❌ Vision 调用失败：401 invalid")
        assert result is None

    def test_returns_none_on_invalid_json(self):
        result = FoodAnalyzer._parse_food_response("这不是 JSON，根本无法解析")
        assert result is None

    def test_returns_none_on_empty(self):
        assert FoodAnalyzer._parse_food_response("") is None

    def test_extracts_json_from_surrounding_text(self):
        text = "好的，这是识别结果：\n" + json.dumps(self._good_payload(), ensure_ascii=False) + "\n仅供参考"
        result = FoodAnalyzer._parse_food_response(text)
        assert result is not None
        assert result["total_calories"] == 468


class TestNormalizeFoodData:
    """_normalize_food_data 字段规整化"""

    def test_missing_optional_fields_default_to_zero(self):
        data = {"food_items": [{"name": "苹果"}]}  # 缺 weight/calories
        result = FoodAnalyzer._normalize_food_data(data)
        assert result["food_items"][0]["name"] == "苹果"
        assert result["food_items"][0]["estimated_weight_g"] == 0
        assert result["food_items"][0]["calories"] == 0
        assert result["total_calories"] == 0

    def test_handles_string_numbers(self):
        """AI 有时把数字包成字符串，要能转回 float。"""
        data = {
            "food_items": [{"name": "x", "estimated_weight_g": "100", "calories": "200"}],
            "total_calories": "500",
            "total_protein_g": "30",
            "total_carbs_g": "40",
            "total_fat_g": "10",
        }
        result = FoodAnalyzer._normalize_food_data(data)
        assert result["food_items"][0]["estimated_weight_g"] == 100.0
        assert result["total_calories"] == 500.0

    def test_skips_non_dict_items(self):
        data = {"food_items": [{"name": "鸡"}, "garbage", None, {"name": "鱼"}]}
        result = FoodAnalyzer._normalize_food_data(data)
        assert len(result["food_items"]) == 2
        assert result["food_items"][1]["name"] == "鱼"

    def test_empty_food_items_preserved(self):
        data = {"food_items": [], "total_calories": 0}
        result = FoodAnalyzer._normalize_food_data(data)
        assert result["food_items"] == []
        assert result["health_assessment"] == ""

    def test_unknown_name_fallback(self):
        data = {"food_items": [{"name": None}]}
        result = FoodAnalyzer._normalize_food_data(data)
        assert result["food_items"][0]["name"] == "未知"


class TestToFloat:
    def test_none_returns_zero(self):
        assert _to_float(None) == 0.0

    def test_int_passes(self):
        assert _to_float(42) == 42.0

    def test_float_passes(self):
        assert _to_float(3.14) == 3.14

    def test_string_number(self):
        assert _to_float("100") == 100.0

    def test_invalid_string_returns_zero(self):
        assert _to_float("abc") == 0.0

    def test_empty_string_returns_zero(self):
        assert _to_float("") == 0.0


class TestAnalyzeFoodEnd2End:
    """analyze_food 端到端：图片处理 + 调 vision + 解析。"""

    def _make_analyzer(self, vision_response):
        """造一个 FoodAnalyzer，注入 mock AI。"""
        ai = MagicMock()
        ai.chat_with_vision.return_value = vision_response
        # 不走真实 get_ai_client，直接 bypass __init__
        fa = FoodAnalyzer.__new__(FoodAnalyzer)
        fa.ai = ai
        fa._photo_helper = MagicMock()
        fa._photo_helper.resize_image_if_needed = lambda b: b  # 不压缩
        return fa

    def test_returns_parsed_dict(self, fake_image_bytes):
        payload = {"food_items": [{"name": "苹果"}], "total_calories": 95}
        fa = self._make_analyzer('```json\n' + json.dumps(payload) + '\n```')
        result = fa.analyze_food(fake_image_bytes, user_goal="减脂")
        assert result is not None
        assert result["total_calories"] == 95.0

    def test_passes_user_goal_to_prompt(self, fake_image_bytes):
        fa = self._make_analyzer('{}')
        fa.analyze_food(fake_image_bytes, user_goal="增肌到80kg")
        prompt = fa.ai.chat_with_vision.call_args.kwargs["text"]
        assert "增肌到80kg" in prompt

    def test_returns_none_when_no_ai(self, fake_image_bytes):
        fa = FoodAnalyzer.__new__(FoodAnalyzer)
        fa.ai = None
        fa._photo_helper = MagicMock()
        assert fa.analyze_food(fake_image_bytes) is None

    def test_resizes_large_images(self, fake_large_image_bytes):
        """大图应先压缩再传，避免超出 API 限制。"""
        fa = self._make_analyzer('{}')
        captured = {}
        fa._photo_helper.resize_image_if_needed = lambda b: (captured.setdefault("called", True), b)[1]
        fa.analyze_food(fake_large_image_bytes)
        assert captured.get("called") is True

    def test_handles_vision_error_response(self, fake_image_bytes):
        """vision 返回 ❌ 开头时，结果是 None 而不是抛异常。"""
        fa = self._make_analyzer("❌ Vision 调用失败：401 invalid key")
        result = fa.analyze_food(fake_image_bytes)
        assert result is None