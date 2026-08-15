"""共享 fixtures 和工具。

所有测试都不打真实 API——OpenAI/飞书/HTTP 调用都用 mock 替代。
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

# 让 pytest 能找到 core/ 包
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest


@pytest.fixture
def fake_image_bytes():
    """一张 32x32 的红色 JPEG，足以喂给 vision API。"""
    from PIL import Image
    import io
    img = Image.new("RGB", (32, 32), color=(220, 60, 60))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def fake_large_image_bytes():
    """一张 4.5 MB 的大图，用来测试 resize_image_if_needed 压缩逻辑。"""
    from PIL import Image
    import io
    # 用细密噪点把图片撑大
    import random
    random.seed(0)
    img = Image.new("RGB", (4000, 4000))
    pixels = img.load()
    for x in range(img.width):
        for y in range(img.height):
            pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=100)
    return buf.getvalue()


@pytest.fixture
def mock_ai_client():
    """模拟 DeepSeekClient，所有方法返回可控字符串。"""
    client = MagicMock()
    client.chat.return_value = "AI 普通回复"
    client.chat_with_vision.return_value = '{"result": "ok"}'
    client.chat_json.return_value = {"result": "ok"}
    client.api_key = "sk-test"
    client.base_url = "https://example.com"
    client.model = "test-model"
    return client


@pytest.fixture
def mock_feishu_client():
    """模拟飞书客户端。"""
    client = MagicMock()
    client.list_records.return_value = []
    client.add_record.return_value = "rec_test"
    client.update_record.return_value = None
    client.delete_record.return_value = None
    client.upload_file.return_value = "file_test"
    return client


@pytest.fixture(autouse=True)
def reset_singletons():
    """每个测试前清掉 core 模块里的全局单例缓存，避免状态污染。"""
    import importlib
    import core.ai_client
    import core.feishu_client
    core.ai_client._client = None
    core.feishu_client._client = None
    yield
    core.ai_client._client = None
    core.feishu_client._client = None