"""core/plan_generator.py 测试

主要覆盖 parse_sections（按 --- 分段），其他函数涉及 streamlit UI 不在单测范围。
"""
from unittest.mock import MagicMock

from core.plan_generator import parse_sections, PlanGenerator


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