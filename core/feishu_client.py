"""飞书开放 API 封装

参考文档：
- 多维表格: https://open.feishu.cn/document/server-docs/docs/bitable-v1/bitable-overview
- 鉴权: https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token
"""
import requests
import time
from typing import List, Dict, Optional, Any

from core.config import (
    FEISHU_APP_ID,
    FEISHU_APP_SECRET,
    FEISHU_APP_TOKEN,
    FEISHU_TABLES,
)

BASE_URL = "https://open.feishu.cn/open-apis"


class FeishuClient:
    """飞书客户端（简化版，只封装用到的接口）"""

    def __init__(self):
        if not all([FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_APP_TOKEN]):
            raise ValueError("飞书配置不完整：APP_ID / APP_SECRET / APP_TOKEN")
        self.app_token = FEISHU_APP_TOKEN
        self._access_token = None
        self._token_expires_at = 0

    # ============= 鉴权 =============
    def _get_access_token(self) -> str:
        """获取 tenant_access_token（缓存 2 小时）"""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        url = f"{BASE_URL}/auth/v3/tenant_access_token/internal"
        resp = requests.post(
            url,
            json={
                "app_id": FEISHU_APP_ID,
                "app_secret": FEISHU_APP_SECRET,
            },
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"飞书鉴权失败：{data}")

        self._access_token = data["tenant_access_token"]
        # 提前 5 分钟过期，避免临界
        self._token_expires_at = time.time() + data["expire"] - 300
        return self._access_token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json; charset=utf-8",
        }

    # ============= 多维表格 CRUD =============
    def list_records(
        self,
        table_id: str,
        view_id: Optional[str] = None,
        filter_dict: Optional[Dict] = None,
        sort: Optional[List[Dict]] = None,
        page_size: int = 100,
    ) -> List[Dict]:
        """列出记录

        Args:
            table_id: 表格 ID
            filter_dict: 过滤条件，如 {"逻辑运算": "AND", "条件": [...]}
            sort: 排序，如 [{"字段名": "日期", "是否倒序": True}]
        """
        url = f"{BASE_URL}/bitable/v1/apps/{self.app_token}/tables/{table_id}/records"
        params = {"page_size": page_size}
        if view_id:
            params["view_id"] = view_id
        if sort:
            params["sort"] = str(sort).replace("'", '"')
        if filter_dict:
            params["filter"] = str(filter_dict).replace("'", '"')

        resp = requests.get(url, headers=self._headers(), params=params)
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"飞书查询失败：{data}")

        items = data.get("data", {}).get("items", [])
        return items

    def add_record(self, table_id: str, fields: Dict) -> str:
        """新增一条记录

        Args:
            table_id: 表格 ID
            fields: 字段 dict，key 是飞书表格的字段名

        Returns:
            新记录的 record_id
        """
        url = f"{BASE_URL}/bitable/v1/apps/{self.app_token}/tables/{table_id}/records"
        resp = requests.post(
            url,
            headers=self._headers(),
            json={"fields": fields},
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"飞书新增失败：{data}")
        return data["data"]["record"]["record_id"]

    def update_record(self, table_id: str, record_id: str, fields: Dict) -> None:
        """更新记录"""
        url = (
            f"{BASE_URL}/bitable/v1/apps/{self.app_token}"
            f"/tables/{table_id}/records/{record_id}"
        )
        resp = requests.put(
            url,
            headers=self._headers(),
            json={"fields": fields},
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"飞书更新失败：{data}")

    def delete_record(self, table_id: str, record_id: str) -> None:
        """删除记录"""
        url = (
            f"{BASE_URL}/bitable/v1/apps/{self.app_token}"
            f"/tables/{table_id}/records/{record_id}"
        )
        resp = requests.delete(url, headers=self._headers())
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"飞书删除失败：{data}")

    # ============= 附件上传 =============
    def upload_file(self, file_bytes: bytes, file_name: str) -> str:
        """上传文件到飞书云空间

        Returns:
            file_token（在表格里作为附件字段值）
        """
        url = f"{BASE_URL}/drive/v1/files/upload_all"
        files = {"file": (file_name, file_bytes)}
        # 注意：上传文件不能用 JSON header
        headers = {"Authorization": f"Bearer {self._get_access_token()}"}

        resp = requests.post(url, headers=headers, files=files)
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"飞书上传失败：{data}")
        return data["data"]["file_token"]

    # ============= 便捷方法 =============
    def get_body_records(self, limit: int = 30) -> List[Dict]:
        """获取身体记录列表（按日期倒序）"""
        if not FEISHU_TABLES["body_records"]:
            return []
        items = self.list_records(
            FEISHU_TABLES["body_records"],
            sort=[{"字段名": "日期", "是否倒序": True}],
            page_size=limit,
        )
        return items

    def get_meal_records_today(self) -> List[Dict]:
        """获取今日饮食记录"""
        if not FEISHU_TABLES["meal_logs"]:
            return []
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        # 简化：拿最近 50 条再过滤
        items = self.list_records(
            FEISHU_TABLES["meal_logs"],
            sort=[{"字段名": "日期", "是否倒序": True}],
            page_size=50,
        )
        return [item for item in items if today in str(item.get("fields", {}).get("日期", ""))]


# 全局单例
_client: Optional[FeishuClient] = None


def get_feishu_client() -> Optional[FeishuClient]:
    """获取飞书客户端（配置不全返回 None）"""
    global _client
    if _client is None:
        try:
            _client = FeishuClient()
        except ValueError:
            return None
    return _client