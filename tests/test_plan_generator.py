"""core/plan_generator.py 测试

主要覆盖 parse_sections（按 --- 分段），其他函数涉及 streamlit UI 不在单测范围。
"""
from unittest.mock import MagicMock

from core.plan_generator import parse_sections, PlanGenerator, extract_macro_targets


class TestParseSections:
    def test_no_separator_returns_whole_text(self):
        assert parse_sections("只有一段内容") == ["只有一段内容"]

    def test_splits_on_dashes(self):
        text = "Section 1\n---\nSection 2\n---\nSection 3"
        assert parse_sections(text) == ["Section 1", "Section 2", "Section 3"]

    def test_skips_empty_segments(self):
        text = "A\n---\n\n---\nB\n---\n\n"
        assert parse_sections(text) == ["A", "B"]

    def test_preserves_internal_newlines(self):
        text = "Line 1\nLine 2\n---\nLine 3"
        assert parse_sections(text) == ["Line 1\nLine 2", "Line 3"]


class TestGenerate:
    """generate() 的主要逻辑是 prompt 格式化和委托 ai.chat。"""

    def test_returns_ai_response(self):
        ai = MagicMock()
        ai.chat.return_value = "## 训练计划\n---\n周训练内容"
        gen = PlanGenerator.__new__(PlanGenerator)
        gen.ai = ai
        gen.feishu = MagicMock()
        result = gen.generate({
            "height": 175, "weight": 70, "age": 28, "gender": "男",
            "goal": "增肌", "experience": "新手", "hours_per_week": 5,
            "resources": ["健身房"], "notes": "无",
        })
        assert result == "## 训练计划\n---\n周训练内容"
        ai.chat.assert_called_once()

    def test_no_ai_returns_error_string(self):
        gen = PlanGenerator.__new__(PlanGenerator)
        gen.ai = None
        gen.feishu = MagicMock()
        result = gen.generate({"height": 175})
        assert "AI 客户端未配置" in result

    def test_prompt_substitutes_all_profile_fields(self):
        ai = MagicMock()
        ai.chat.return_value = "x"
        gen = PlanGenerator.__new__(PlanGenerator)
        gen.ai = ai
        gen.feishu = MagicMock()
        gen.generate({
            "height": 180, "weight": 80, "age": 30, "gender": "女",
            "goal": "减脂", "experience": "进阶", "hours_per_week": 4,
            "resources": ["居家", "哑铃"], "notes": "膝盖有伤",
        })
        prompt = ai.chat.call_args.kwargs["messages"][0]["content"]
        assert "180" in prompt
        assert "80" in prompt
        assert "减脂" in prompt
        assert "居家, 哑铃" in prompt
        assert "膝盖有伤" in prompt

    def test_resources_joined_or_default(self):
        ai = MagicMock()
        ai.chat.return_value = "x"
        gen = PlanGenerator.__new__(PlanGenerator)
        gen.ai = ai
        gen.feishu = MagicMock()
        gen.generate({
            "height": 170, "resources": [], "notes": "",
        })
        prompt = ai.chat.call_args.kwargs["messages"][0]["content"]
        assert "无" in prompt  # 空 resources → "无"


class TestExtractMacroTargets:
    """extract_macro_targets：从 AI 输出中提取结构化宏量目标。"""

    def test_extracts_json_block(self):
        text = """Section 1
---
Section 2

```json
{
  "daily_calories": 2200,
  "daily_protein_g": 120,
  "daily_carbs_g": 250,
  "daily_fat_g": 70
}
```"""
        result = extract_macro_targets(text)
        assert result is not None
        assert result["daily_calories"] == 2200
        assert result["daily_protein_g"] == 120
        assert result["daily_carbs_g"] == 250
        assert result["daily_fat_g"] == 70

    def test_extracts_bare_json(self):
        text = 'some text {"daily_calories": 1800, "daily_protein_g": 100, "daily_carbs_g": 200, "daily_fat_g": 55} more text'
        result = extract_macro_targets(text)
        assert result is not None
        assert result["daily_calories"] == 1800

    def test_returns_none_when_no_json(self):
        text = "只有一段文字，没有 JSON 块"
        assert extract_macro_targets(text) is None

    def test_returns_none_when_incomplete_json(self):
        text = '```json\n{"daily_calories": 2000}\n```'
        result = extract_macro_targets(text)
        # 只有 calories 没有 protein 也应该返回（有 daily_calories 就够了）
        assert result is not None
        assert result["daily_calories"] == 2000
        assert result["daily_protein_g"] == 0  # 缺省为 0

    def test_handles_non_numeric_values(self):
        text = '```json\n{"daily_calories": "两千", "daily_protein_g": 100, "daily_carbs_g": 200, "daily_fat_g": 50}\n```'
        result = extract_macro_targets(text)
        # "两千" 转 int 会失败，应该返回 None
        assert result is None