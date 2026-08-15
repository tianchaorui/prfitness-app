"""core/ai_client.py 测试

覆盖：
- DeepSeekClient 初始化（缺 key 报错）
- chat 调用 OpenAI SDK 转发 messages
- chat_with_vision 构造多模态 content
- chat_json 三段式 JSON 解析（裸 JSON / ```json 块 / { ... } 抽取）
- get_ai_client 单例缓存 & 缺 key 返回 None
"""
import json
from unittest.mock import patch, MagicMock, ANY


def make_client(api_key="sk-test", base_url="https://x", model="m"):
    """绕过构造函数直接造一个 DeepSeekClient。"""
    from core.ai_client import DeepSeekClient
    c = DeepSeekClient.__new__(DeepSeekClient)
    c.api_key = api_key
    c.base_url = base_url
    c.model = model
    c.client = MagicMock()
    return c


class TestDeepSeekClientInit:
    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        with patch("core.config.st") as mock_st:
            mock_st.secrets = MagicMock()
            mock_st.secrets.__contains__ = MagicMock(return_value=False)
            from core.ai_client import DeepSeekClient
            with __import__("pytest").raises(ValueError, match="DEEPSEEK_API_KEY"):
                DeepSeekClient()

    def test_constructs_openai_client(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
        monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
        with patch("core.config.st") as mock_st:
            mock_st.secrets = MagicMock()
            mock_st.secrets.__contains__ = MagicMock(return_value=False)
            with patch("core.ai_client.OpenAI") as mock_openai:
                from core.ai_client import DeepSeekClient
                c = DeepSeekClient()
        assert c.api_key == "sk-test"
        mock_openai.assert_called_once()
        kwargs = mock_openai.call_args.kwargs
        assert kwargs["api_key"] == "sk-test"
        assert kwargs["base_url"]  # 默认值非空即可


class TestChat:
    def test_returns_content(self):
        from core.ai_client import DeepSeekClient
        c = make_client()
        c.client.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(content="hello"))]
        result = c.chat(messages=[{"role": "user", "content": "hi"}])
        assert result == "hello"

    def test_returns_error_string_on_exception(self):
        from core.ai_client import DeepSeekClient
        c = make_client()
        c.client.chat.completions.create.side_effect = RuntimeError("boom")
        result = c.chat(messages=[{"role": "user", "content": "x"}])
        assert result.startswith("❌")
        assert "boom" in result

    def test_passes_temperature_and_max_tokens(self):
        from core.ai_client import DeepSeekClient
        c = make_client()
        c.client.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(content="x"))]
        c.chat(messages=[{"role": "user", "content": "x"}], temperature=0.3, max_tokens=100)
        kwargs = c.client.chat.completions.create.call_args.kwargs
        assert kwargs["temperature"] == 0.3
        assert kwargs["max_tokens"] == 100


class TestChatWithVision:
    def test_builds_multimodal_payload(self):
        from core.ai_client import DeepSeekClient
        c = make_client()
        c.client.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(content="看见了"))]
        c.chat_with_vision(text="描述这张图", image_urls=["data:image/jpeg;base64,abc"])
        kwargs = c.client.chat.completions.create.call_args.kwargs
        msgs = kwargs["messages"]
        assert len(msgs) == 1
        content = msgs[0]["content"]
        # 第一项是 text，后面跟着 image_url
        assert content[0] == {"type": "text", "text": "描述这张图"}
        assert content[1] == {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,abc"}}

    def test_handles_multiple_images(self):
        from core.ai_client import DeepSeekClient
        c = make_client()
        c.client.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(content="x"))]
        c.chat_with_vision(text="对比", image_urls=["u1", "u2", "u3"])
        content = c.client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
        images = [c for c in content if c["type"] == "image_url"]
        assert len(images) == 3

    def test_returns_error_string_on_exception(self):
        from core.ai_client import DeepSeekClient
        c = make_client()
        c.client.chat.completions.create.side_effect = RuntimeError("401 invalid")
        result = c.chat_with_vision(text="x", image_urls=["u"])
        assert result.startswith("❌")
        assert "401" in result


class TestChatJson:
    def test_parses_plain_json(self):
        from core.ai_client import DeepSeekClient
        c = make_client()
        c.chat = MagicMock(return_value='{"a": 1, "b": "x"}')
        assert c.chat_json("hi") == {"a": 1, "b": "x"}

    def test_parses_json_code_block(self):
        from core.ai_client import DeepSeekClient
        c = make_client()
        c.chat = MagicMock(return_value='```json\n{"a": 2}\n```')
        assert c.chat_json("hi") == {"a": 2}

    def test_parses_bare_code_block(self):
        from core.ai_client import DeepSeekClient
        c = make_client()
        c.chat = MagicMock(return_value='```\n{"a": 3}\n```')
        assert c.chat_json("hi") == {"a": 3}

    def test_extracts_json_from_surrounding_text(self):
        from core.ai_client import DeepSeekClient
        c = make_client()
        c.chat = MagicMock(return_value='前面废话 {"a": 4, "nested": {"x": 1}} 后面也废话')
        assert c.chat_json("hi") == {"a": 4, "nested": {"x": 1}}

    def test_returns_none_on_invalid(self):
        from core.ai_client import DeepSeekClient
        c = make_client()
        c.chat = MagicMock(return_value="不是 JSON，根本无法解析")
        assert c.chat_json("hi") is None

    def test_returns_none_on_empty(self):
        from core.ai_client import DeepSeekClient
        c = make_client()
        c.chat = MagicMock(return_value="")
        assert c.chat_json("hi") is None


class TestGetAiClient:
    def test_returns_none_when_no_key(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        with patch("core.config.st") as mock_st:
            mock_st.secrets = MagicMock()
            mock_st.secrets.__contains__ = MagicMock(return_value=False)
            from core.ai_client import get_ai_client
            assert get_ai_client() is None

    def test_singleton_cached(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-x")
        with patch("core.config.st") as mock_st:
            mock_st.secrets = MagicMock()
            mock_st.secrets.__contains__ = MagicMock(return_value=False)
            with patch("core.ai_client.OpenAI"):
                from core.ai_client import get_ai_client
                c1 = get_ai_client()
                c2 = get_ai_client()
        assert c1 is c2  # 第二次返回的是同一个单例