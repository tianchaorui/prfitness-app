"""core/rag.py 测试

覆盖关键词打分排序逻辑和 context 拼接。
"""
import os
from unittest.mock import MagicMock, patch

from core.rag import FitnessRAG

_MISSING = object()


def make_rag(ai_mock=_MISSING, knowledge_dir="/tmp/empty_kb"):
    r = FitnessRAG.__new__(FitnessRAG)
    if ai_mock is _MISSING:
        r.ai = MagicMock()
    else:
        r.ai = ai_mock
    r.knowledge_dir = knowledge_dir
    r._documents = None
    return r


class TestSelectRelevantContext:
    def test_empty_kb_returns_empty(self, tmp_path):
        r = make_rag(knowledge_dir=str(tmp_path))
        assert r._select_relevant_context("怎么练") == ""

    def test_filename_match_scores_higher(self, tmp_path):
        # 写两个知识文档：filename 和内容分别匹配
        (tmp_path / "蛋白质.md").write_text("蛋白质摄入指南", encoding="utf-8")
        (tmp_path / "有氧运动.md").write_text("跑步指南", encoding="utf-8")
        r = make_rag(knowledge_dir=str(tmp_path))
        ctx = r._select_relevant_context("蛋白质")
        # 文件名匹配应优先
        assert "蛋白质" in ctx

    def test_content_keyword_match(self, tmp_path):
        (tmp_path / "guide1.md").write_text("深蹲是练腿的王牌动作", encoding="utf-8")
        (tmp_path / "guide2.md").write_text("卧推练胸", encoding="utf-8")
        r = make_rag(knowledge_dir=str(tmp_path))
        ctx = r._select_relevant_context("深蹲")
        assert "深蹲" in ctx
        assert "卧推" not in ctx  # 不相关的不应该出现

    def test_max_docs_limit(self, tmp_path):
        # 写 5 个都包含 "训练" 的文档
        for i in range(5):
            (tmp_path / f"doc{i}.md").write_text(f"训练内容{i}", encoding="utf-8")
        r = make_rag(knowledge_dir=str(tmp_path))
        ctx = r._select_relevant_context("训练")
        # 只取前 2 个
        count = ctx.count("【doc")
        assert count == 2

    def test_zero_score_excluded(self, tmp_path):
        (tmp_path / "unrelated.md").write_text("完全不相关的内容", encoding="utf-8")
        r = make_rag(knowledge_dir=str(tmp_path))
        ctx = r._select_relevant_context("蛋白质")
        assert ctx == ""

    def test_long_content_truncated(self, tmp_path):
        long_content = "训练" * 5000
        (tmp_path / "long.md").write_text(long_content, encoding="utf-8")
        r = make_rag(knowledge_dir=str(tmp_path))
        ctx = r._select_relevant_context("训练", max_chars=100)
        assert len(ctx) <= 200  # 包括文件名标记 + 截断


class TestAsk:
    def test_no_ai_returns_error(self):
        r = make_rag(ai_mock=None)
        assert "❌" in r.ask("怎么练")

    def test_returns_ai_response(self):
        ai = MagicMock()
        ai.chat.return_value = "回答：每周3次力量训练"
        r = make_rag(ai_mock=ai, knowledge_dir="/tmp/empty_kb")
        result = r.ask("怎么安排训练")
        assert result == "回答：每周3次力量训练"
        # 验证调用参数是 [system, user] 形式
        msgs = ai.chat.call_args.kwargs["messages"]
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"

    def test_no_profile_uses_placeholder(self):
        ai = MagicMock()
        ai.chat.return_value = "ok"
        r = make_rag(ai_mock=ai, knowledge_dir="/tmp/empty_kb")
        r.ask("xxx")
        sys_prompt = ai.chat.call_args.kwargs["messages"][0]["content"]
        assert "未填写" in sys_prompt


class TestSaveConversation:
    def test_no_feishu_returns_none(self, monkeypatch):
        monkeypatch.setenv("FEISHU_TABLE_CONVERSATION", "")
        from core.feishu_client import _client
        import core.feishu_client
        core.feishu_client._client = None
        with patch("core.feishu_client.get_feishu_client", return_value=None):
            r = make_rag()
            assert r.save_conversation("user", "test") is None