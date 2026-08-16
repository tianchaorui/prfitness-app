"""core/user.py 测试"""
from unittest.mock import patch, MagicMock


def make_session_state(initial=None):
    """造一个支持属性赋值 + 字典访问的 session_state 替身。"""
    data = dict(initial or {})

    class FakeSessionState:
        def get(self, key, default=None):
            return data.get(key, default)

        def __setitem__(self, key, value):
            data[key] = value

        def __getitem__(self, key):
            return data[key]

        def __contains__(self, key):
            return key in data

        def __setattr__(self, key, value):
            data[key] = value

        def __getattr__(self, key):
            try:
                return data[key]
            except KeyError:
                raise AttributeError(key)

    return FakeSessionState(), data


class TestGetCurrentUser:
    def test_returns_default_when_no_state(self):
        """没设过任何值时返回「我」。"""
        ss, _ = make_session_state()
        with patch("core.user.st") as mock_st:
            mock_st.query_params = MagicMock()
            mock_st.query_params.get = MagicMock(return_value=None)
            mock_st.session_state = ss
            from core.user import get_current_user, DEFAULT_USER
            assert get_current_user() == DEFAULT_USER

    def test_returns_session_state_value(self):
        ss, _ = make_session_state({"current_user": "老婆"})
        with patch("core.user.st") as mock_st:
            mock_st.query_params = MagicMock()
            mock_st.query_params.get = MagicMock(return_value=None)
            mock_st.session_state = ss
            from core.user import get_current_user
            assert get_current_user() == "老婆"

    def test_url_param_overrides_session_state(self):
        ss, data = make_session_state({"current_user": "我"})
        with patch("core.user.st") as mock_st:
            mock_st.query_params = MagicMock()
            mock_st.query_params.get = MagicMock(return_value="小明")
            mock_st.session_state = ss
            from core.user import get_current_user
            assert get_current_user() == "小明"
            # 同时也回写到 session_state
            assert data["current_user"] == "小明"


class TestSetUser:
    def test_writes_to_session_and_url(self):
        ss, data = make_session_state()
        with patch("core.user.st") as mock_st:
            mock_st.session_state = ss
            mock_st.query_params = MagicMock()
            from core.user import set_user
            set_user("老婆")
        assert data["current_user"] == "老婆"
        mock_st.query_params.__setitem__.assert_called_with("user", "老婆")

    def test_falls_back_to_default_for_blank(self):
        ss, data = make_session_state()
        with patch("core.user.st") as mock_st:
            mock_st.session_state = ss
            mock_st.query_params = MagicMock()
            from core.user import set_user
            set_user("   ")
        assert data["current_user"] == "我"