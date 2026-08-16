"""core/photo_analyzer.py 测试

重点覆盖改过的 JSON 解析逻辑（移除 ```json 围栏 + 正则兜底）
"""
import json
import base64
from unittest.mock import MagicMock, patch

from core.photo_analyzer import PhotoAnalyzer

_MISSING = object()


def make_analyzer(ai_mock, feishu_mock=_MISSING):
    """构造一个不依赖真实 API 的 PhotoAnalyzer。

    feishu_mock=_MISSING（默认）→ 创建一个 MagicMock
    feishu_mock=None → 真的设成 None（用于测试「无飞书」分支）
    """
    a = PhotoAnalyzer.__new__(PhotoAnalyzer)
    a.ai = ai_mock
    if feishu_mock is _MISSING:
        a.feishu = MagicMock()
    else:
        a.feishu = feishu_mock
    return a


class TestFileToBase64DataUri:
    def test_default_mime_is_jpeg(self):
        out = PhotoAnalyzer.file_to_base64_data_uri(b"\xff\xd8\xff")
        assert out.startswith("data:image/jpeg;base64,")
        # 验证 base64 部分能被还原
        b64 = out.split(",", 1)[1]
        assert base64.b64decode(b64) == b"\xff\xd8\xff"

    def test_custom_mime(self):
        out = PhotoAnalyzer.file_to_base64_data_uri(b"\x89PNG", mime_type="image/png")
        assert out.startswith("data:image/png;base64,")


class TestResizeImageIfNeeded:
    def test_returns_unchanged_when_small(self, fake_image_bytes):
        # 32x32 的 JPEG 远小于 4 MB
        out = PhotoAnalyzer.resize_image_if_needed(fake_image_bytes)
        assert out == fake_image_bytes

    def test_resizes_large_image(self, fake_large_image_bytes):
        original_size = len(fake_large_image_bytes)
        assert original_size > 4 * 1024 * 1024, "fixture 应该 > 4MB"
        out = PhotoAnalyzer.resize_image_if_needed(fake_large_image_bytes, max_size_mb=2.0)
        assert len(out) <= 2 * 1024 * 1024

    def test_resize_preserves_jpeg_format(self, fake_large_image_bytes):
        out = PhotoAnalyzer.resize_image_if_needed(fake_large_image_bytes, max_size_mb=1.0)
        # JPEG 文件以 ff d8 开头
        assert out[:2] == b"\xff\xd8"


class TestAnalyzeSingleJSONParsing:
    """针对 [photo_analyzer.py:73-98] 的 JSON 解析路径。"""

    def _ai_returning(self, response):
        ai = MagicMock()
        ai.chat_with_vision.return_value = response
        return ai

    def test_plain_json(self, fake_image_bytes):
        ai = self._ai_returning('{"estimated_body_fat": "18%", "body_type": "匀称"}')
        a = make_analyzer(ai)
        result = a.analyze_single(fake_image_bytes)
        assert result == {"estimated_body_fat": "18%", "body_type": "匀称"}

    def test_json_in_code_block(self, fake_image_bytes):
        ai = self._ai_returning('```json\n{"x": 1, "y": "z"}\n```')
        a = make_analyzer(ai)
        assert a.analyze_single(fake_image_bytes) == {"x": 1, "y": "z"}

    def test_bare_code_block(self, fake_image_bytes):
        ai = self._ai_returning('```\n{"k": "v"}\n```')
        a = make_analyzer(ai)
        assert a.analyze_single(fake_image_bytes) == {"k": "v"}

    def test_json_with_surrounding_text(self, fake_image_bytes):
        ai = self._ai_returning('好的，结果如下：\n{"score": 88}\n仅供参考')
        a = make_analyzer(ai)
        assert a.analyze_single(fake_image_bytes) == {"score": 88}

    def test_unparseable_returns_none(self, fake_image_bytes, capsys):
        ai = self._ai_returning("这不是 JSON")
        a = make_analyzer(ai)
        result = a.analyze_single(fake_image_bytes)
        assert result is None
        captured = capsys.readouterr()
        assert "JSON 解析失败" in captured.out

    def test_returns_none_when_no_ai(self):
        a = make_analyzer(ai_mock=None)
        assert a.analyze_single(b"\xff\xd8") is None

    def test_raises_on_upstream_error(self, fake_image_bytes):
        """vision 返回 ❌ 开头时应直接抛错，不静默吞掉。"""
        ai = self._ai_returning("❌ Vision 调用失败：401 invalid api key")
        a = make_analyzer(ai)
        import pytest
        with pytest.raises(RuntimeError, match="401"):
            a.analyze_single(fake_image_bytes)


class TestCompareTwoJSONParsing:
    """[photo_analyzer.py:140-167] 走的是同一套解析逻辑，再点测一次保险。"""

    def _ai_returning(self, response):
        ai = MagicMock()
        ai.chat_with_vision.return_value = response
        return ai

    def test_raises_on_upstream_error(self, fake_image_bytes):
        """vision 返回 ❌ 开头时应直接抛错。"""
        ai = self._ai_returning("❌ Vision 调用失败：model does not exist")
        a = make_analyzer(ai)
        import pytest
        with pytest.raises(RuntimeError, match="model does not exist"):
            a.compare_two(fake_image_bytes, fake_image_bytes, days_between=30)


class TestCompareTwoJSONParsing:
    """[photo_analyzer.py:140-167] 走的是同一套解析逻辑，再点测一次保险。"""

    def _ai_returning(self, response):
        ai = MagicMock()
        ai.chat_with_vision.return_value = response
        return ai

    def test_full_payload(self, fake_image_bytes):
        payload = {
            "overall_change": "进步",
            "progress_score": 75,
            "summary": "线条更明显",
            "specific_changes": ["肩膀更宽"],
            "concerns": ["右侧略不对称"],
            "next_steps": ["继续力量训练"],
        }
        ai = self._ai_returning("```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```")
        a = make_analyzer(ai)
        result = a.compare_two(fake_image_bytes, fake_image_bytes, days_between=30)
        assert result == payload

    def test_passes_user_context(self, fake_image_bytes):
        ai = self._ai_returning("{}")
        a = make_analyzer(ai)
        a.compare_two(fake_image_bytes, fake_image_bytes, days_between=7, user_context="减脂")
        # 验证 prompt 被传进去（不需要验证完整内容）
        ai.chat_with_vision.assert_called_once()
        kwargs = ai.chat_with_vision.call_args.kwargs
        assert "减脂" in kwargs["text"]

    def test_resizes_both_images_before_sending(self, fake_large_image_bytes):
        ai = self._ai_returning("{}")
        a = make_analyzer(ai)
        a.compare_two(fake_large_image_bytes, fake_large_image_bytes, days_between=10)
        # 拿到传给 chat_with_vision 的 image_urls，每张图应 < 4MB
        image_urls = ai.chat_with_vision.call_args.kwargs["image_urls"]
        for url in image_urls:
            # data URI 去掉前缀后 base64 decode 得到原始 bytes
            b64 = url.split(",", 1)[1]
            raw = base64.b64decode(b64)
            assert len(raw) <= 4 * 1024 * 1024, f"图太大: {len(raw)/1024/1024:.1f} MB"


class TestSaveToFeishu:
    def test_no_feishu_returns_none(self, fake_image_bytes):
        ai = MagicMock()
        a = make_analyzer(ai_mock=ai, feishu_mock=None)
        assert a.save_to_feishu(fake_image_bytes, {"progress_score": 75}) is None

    def test_no_table_id_returns_none(self, fake_image_bytes, monkeypatch):
        monkeypatch.setenv("FEISHU_TABLE_BODY", "")
        ai = MagicMock()
        feishu = MagicMock()
        a = make_analyzer(ai, feishu)
        assert a.save_to_feishu(fake_image_bytes, {}) is None

    def test_success_returns_record_id(self, fake_image_bytes, monkeypatch):
        monkeypatch.setenv("FEISHU_TABLE_BODY", "tbl123")
        ai = MagicMock()
        feishu = MagicMock()
        feishu.upload_file.return_value = "file_tok"
        feishu.add_record.return_value = "rec_xyz"
        a = make_analyzer(ai, feishu)
        rid = a.save_to_feishu(fake_image_bytes, {"progress_score": 88}, note="测试备注")
        assert rid == "rec_xyz"
        feishu.upload_file.assert_called_once()
        # 写入飞书的 fields 应包含文件 + 备注
        kwargs = feishu.add_record.call_args
        fields = kwargs.kwargs.get("fields") or kwargs.args[1]
        assert "今日照片" in fields
        assert "备注" in fields
        assert "88" in fields["备注"]

    def test_exception_does_not_propagate(self, fake_image_bytes, monkeypatch, capsys):
        monkeypatch.setenv("FEISHU_TABLE_BODY", "tbl123")
        ai = MagicMock()
        feishu = MagicMock()
        feishu.upload_file.side_effect = RuntimeError("feishu 挂了")
        a = make_analyzer(ai, feishu)
        assert a.save_to_feishu(fake_image_bytes, {}) is None
        captured = capsys.readouterr()
        assert "保存失败" in captured.out