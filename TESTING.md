# 测试文档

## 运行测试

```bash
# 安装测试依赖
pip install -r requirements-dev.txt

# 跑全部测试
pytest

# 只跑单元测试（跳过 streamlit 页面 smoke test）
pytest --ignore=tests/test_pages_smoke.py

# 跑指定文件
pytest tests/test_photo_analyzer.py

# 带覆盖率
pytest --cov=core --cov-report=term-missing
```

## 测试结构

```
tests/
├── conftest.py                # 共享 fixtures
├── test_config.py             # core/config.py：get_config / show_config_status
├── test_ai_client.py          # core/ai_client.py：chat / chat_with_vision / chat_json
├── test_photo_analyzer.py     # core/photo_analyzer.py：JSON 解析 / 压缩图片
├── test_plan_generator.py     # core/plan_generator.py：parse_sections / 提示词格式化
├── test_rag.py                # core/rag.py：关键词打分 / context 选择
├── test_feishu_client.py      # core/feishu_client.py：HTTP 参数构造
├── test_food_analyzer.py      # core/food_analyzer.py：食物识别 JSON 解析
└── test_pages_smoke.py        # 页面级 smoke test（AppTest）
```

## 设计原则

- **不打真实 API**：所有外部调用（OpenAI / 飞书 / 视觉识别）都用 `unittest.mock.MagicMock` 替身
- **fixture 共享**：`conftest.py` 提供 `fake_image_bytes` / `mock_ai_client` / `mock_feishu_client` / 单例缓存清理
- **覆盖 JSON 解析路径**：AI 返回常常带 ` ```json ` 围栏或多余文字，三种兜底（裸 JSON / 围栏 / 正则抽取）各测一遍
- **边界值**：缺字段、字符串数字、None、空字典都要能优雅处理

## 新增功能时怎么加测试

1. 纯函数（如解析器、计算工具）→ 直接在 `tests/test_xxx.py` 加单元测试
2. 涉及外部 API → mock 掉再测（如 `test_ai_client.py`）
3. 涉及 streamlit UI → 优先 AppTest，受阻控件（file_uploader / form_submit_button）降级为 `py_compile` 检查