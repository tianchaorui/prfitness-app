"""core/config.py 测试

覆盖：
- get_config 从 .env 读
- get_config 从 st.secrets 读（优先级最高）
- show_config_status 在缺飞书配置时给警告
- check_config 返回缺失项列表
"""
from unittest.mock import patch, MagicMock


class TestGetConfig:
    """get_config 的查找优先级：st.secrets > os.getenv > default"""

    def test_returns_env_var(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env-test")
        with patch("core.config.st") as mock_st:
            # 模拟 st.secrets 访问抛出（未配置 secrets.toml）
            mock_st.secrets = MagicMock()
            mock_st.secrets.__contains__ = MagicMock(return_value=False)
            from core.config import get_config
            assert get_config("DEEPSEEK_API_KEY") == "sk-env-test"

    def test_secrets_overrides_env(self, monkeypatch):
        """st.secrets 命中时应优先于环境变量。"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env")
        with patch("core.config.st") as mock_st:
            secrets_mock = MagicMock()
            secrets_mock.__contains__ = MagicMock(return_value=True)
            secrets_mock.__getitem__ = MagicMock(return_value="sk-secret")
            mock_st.secrets = secrets_mock
            from core.config import get_config
            assert get_config("DEEPSEEK_API_KEY") == "sk-secret"

    def test_returns_default_when_missing(self, monkeypatch):
        monkeypatch.delenv("FOO_BAR", raising=False)
        with patch("core.config.st") as mock_st:
            mock_st.secrets = MagicMock()
            mock_st.secrets.__contains__ = MagicMock(return_value=False)
            from core.config import get_config
            assert get_config("FOO_BAR", "fallback") == "fallback"

    def test_returns_empty_default_when_no_default_given(self, monkeypatch):
        monkeypatch.delenv("MISSING_KEY", raising=False)
        with patch("core.config.st") as mock_st:
            mock_st.secrets = MagicMock()
            mock_st.secrets.__contains__ = MagicMock(return_value=False)
            from core.config import get_config
            assert get_config("MISSING_KEY") == ""

    def test_st_secrets_access_error_falls_back_to_env(self, monkeypatch):
        """st.secrets 访问本身抛异常时（不在 streamlit 上下文），应回落到 env。"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-from-env")
        with patch("core.config.st") as mock_st:
            # 让 st.secrets[key] 抛异常
            mock_st.secrets.__contains__ = MagicMock(side_effect=RuntimeError("no streamlit"))
            from core.config import get_config
            assert get_config("DEEPSEEK_API_KEY") == "sk-from-env"


class TestCheckConfig:
    def test_returns_missing_deepseek(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.delenv("FEISHU_APP_ID", raising=False)
        from core.config import check_config
        with patch("core.config.st") as mock_st:
            mock_st.secrets = MagicMock()
            mock_st.secrets.__contains__ = MagicMock(return_value=False)
            missing = check_config()
        assert "DEEPSEEK_API_KEY" in missing

    def test_all_present_returns_empty(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-1")
        monkeypatch.setenv("FEISHU_APP_ID", "cli_1")
        monkeypatch.setenv("FEISHU_APP_SECRET", "sec_1")
        monkeypatch.setenv("FEEPSEEK_APP_TOKEN", "tok_1")
        from core.config import check_config
        with patch("core.config.st") as mock_st:
            mock_st.secrets = MagicMock()
            mock_st.secrets.__contains__ = MagicMock(return_value=False)
            missing = check_config()
        # DEEPSEEK 已经在，没了；FEISHU_* 都在
        assert "DEEPSEEK_API_KEY" not in missing
        assert "FEISHU_APP_ID" not in missing


class TestShowConfigStatus:
    def test_warning_when_feishu_missing(self, monkeypatch, capsys):
        """缺飞书配置时应 st.warning 并返回 False。"""
        monkeypatch.delenv("FEISHU_APP_ID", raising=False)
        monkeypatch.delenv("FEISHU_APP_SECRET", raising=False)
        monkeypatch.delenv("FEISHU_APP_TOKEN", raising=False)
        from core.config import show_config_status
        with patch("core.config.st") as mock_st:
            mock_st.secrets = MagicMock()
            mock_st.secrets.__contains__ = MagicMock(return_value=False)
            result = show_config_status()
        assert result is False

    def test_ok_when_feishu_present(self, monkeypatch):
        monkeypatch.setenv("FEISHU_APP_ID", "cli_x")
        monkeypatch.setenv("FEISHU_APP_SECRET", "sec_x")
        monkeypatch.setenv("FEISHU_APP_TOKEN", "tok_x")
        from core.config import show_config_status
        with patch("core.config.st") as mock_st:
            mock_st.secrets = MagicMock()
            mock_st.secrets.__contains__ = MagicMock(return_value=False)
            result = show_config_status()
        assert result is True