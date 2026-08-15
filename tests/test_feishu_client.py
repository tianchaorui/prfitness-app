"""core/feishu_client.py 测试

重点验证 HTTP 请求参数构造正确（不真打飞书 API）。
"""
import time
from unittest.mock import MagicMock, patch

import core.feishu_client


def make_client(token="tok", expires_at=None, fresh_token=False):
    """绕过 __init__ 构造一个 FeishuClient。

    - 默认 token 已就绪，不会触发请求
    - fresh_token=True 则强制下次 _get_access_token() 时去打 /auth 接口
    """
    c = core.feishu_client.FeishuClient.__new__(core.feishu_client.FeishuClient)
    c.app_token = "APP_T"
    if fresh_token:
        c._access_token = None
        c._token_expires_at = 0
    else:
        c._access_token = token
        c._token_expires_at = expires_at if expires_at is not None else (time.time() + 3600)
    return c


class TestGetAccessToken:
    def test_fetches_and_caches_token(self):
        c = make_client(fresh_token=True)
        fake_resp = MagicMock()
        fake_resp.json.return_value = {
            "code": 0,
            "tenant_access_token": "t-123",
            "expire": 7200,
        }
        with patch.object(core.feishu_client.requests, "post", return_value=fake_resp) as mock_post:
            tok = c._get_access_token()
        assert tok == "t-123"
        mock_post.assert_called_once()
        url = mock_post.call_args.args[0]
        assert "tenant_access_token/internal" in url
        # 第二次调用应直接返回缓存
        tok2 = c._get_access_token()
        assert tok2 == "t-123"
        assert mock_post.call_count == 1  # 没有再请求

    def test_refresh_after_expiry(self):
        c = make_client(token="old", expires_at=time.time() - 10)
        fake_resp = MagicMock()
        fake_resp.json.return_value = {
            "code": 0,
            "tenant_access_token": "new",
            "expire": 7200,
        }
        with patch.object(core.feishu_client.requests, "post", return_value=fake_resp):
            tok = c._get_access_token()
        assert tok == "new"

    def test_raises_on_auth_failure(self):
        c = make_client(fresh_token=True)
        fake_resp = MagicMock()
        fake_resp.json.return_value = {"code": 999, "msg": "auth failed"}
        with patch.object(core.feishu_client.requests, "post", return_value=fake_resp):
            import pytest
            with pytest.raises(RuntimeError, match="飞书鉴权失败"):
                c._get_access_token()


class TestListRecords:
    def test_sends_correct_url_and_params(self):
        c = make_client()
        c._access_token = "tok"
        fake = MagicMock()
        fake.json.return_value = {"code": 0, "data": {"items": [{"id": "r1"}]}}
        with patch.object(core.feishu_client.requests, "get", return_value=fake) as mock_get:
            items = c.list_records("tbl_1", page_size=50)
        url = mock_get.call_args.args[0]
        assert "apps/APP_T/tables/tbl_1/records" in url
        assert mock_get.call_args.kwargs["params"]["page_size"] == 50
        assert items == [{"id": "r1"}]

    def test_raises_on_api_error(self):
        c = make_client()
        c._access_token = "tok"
        fake = MagicMock()
        fake.json.return_value = {"code": 1, "msg": "bad"}
        with patch.object(core.feishu_client.requests, "get", return_value=fake):
            import pytest
            with pytest.raises(RuntimeError, match="飞书查询失败"):
                c.list_records("tbl_1")


class TestAddRecord:
    def test_returns_new_record_id(self):
        c = make_client()
        c._access_token = "tok"
        fake = MagicMock()
        fake.json.return_value = {"code": 0, "data": {"record": {"record_id": "new_rid"}}}
        with patch.object(core.feishu_client.requests, "post", return_value=fake) as mock_post:
            rid = c.add_record("tbl_x", {"字段1": "值1"})
        assert rid == "new_rid"
        kwargs = mock_post.call_args.kwargs
        assert kwargs["json"] == {"fields": {"字段1": "值1"}}


class TestUploadFile:
    def test_returns_file_token(self):
        c = make_client()
        c._access_token = "tok"
        fake = MagicMock()
        fake.json.return_value = {"code": 0, "data": {"file_token": "ft_xxx"}}
        with patch.object(core.feishu_client.requests, "post", return_value=fake) as mock_post:
            tok = c.upload_file(b"\xff\xd8\xff", "test.jpg")
        assert tok == "ft_xxx"
        # 上传必须用 multipart
        assert "files" in mock_post.call_args.kwargs


class TestGetMealRecordsToday:
    def test_filters_by_today_date(self, monkeypatch):
        # 用今天的日期当 fixture
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")
        c = make_client()
        c.list_records = MagicMock(return_value=[
            {"fields": {"日期": f"{today_str} 12:00"}},
            {"fields": {"日期": "2020-01-01 18:00"}},  # 远古日期
        ])
        items = c.get_meal_records_today()
        assert len(items) == 1