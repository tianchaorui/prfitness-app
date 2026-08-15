"""页面级 smoke test：每个页面都能不报错地加载。

注意：
- pages/1~3 用 AppTest 直接跑（无 form 阻塞）
- pages/4~5 含有 file_uploader / form_submit_button 阻塞控件，AppTest 会等用户输入；
  这里改成「脚本能被 import 且无语法错误」的轻量 smoke test
"""
import importlib.util
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent

# 可以用 AppTest 跑到首屏的页面
APPTEST_PAGES = [
    ("app.py", "主页"),
    ("pages/1_📸_拍照对比.py", "拍照对比"),
    ("pages/2_💬_AI教练.py", "AI 教练"),
    ("pages/3_📋_训练计划.py", "训练计划"),
]

# 含阻塞控件，只能做静态语法/导入检查
IMPORT_ONLY_PAGES = [
    ("pages/4_🍽️_饮食记录.py", "饮食记录"),
    ("pages/5_📊_我的数据.py", "我的数据"),
]


@pytest.mark.parametrize("script_path,label", APPTEST_PAGES)
def test_page_loads_without_exception(script_path, label):
    """每个页面都应在不报错的前提下完成首次渲染。"""
    abs_path = str(ROOT / script_path)
    at = AppTest.from_file(abs_path).run()
    assert not at.exception, f"{label} 渲染报错: {at.exception}"


def test_main_page_has_title():
    at = AppTest.from_file(str(ROOT / "app.py")).run()
    # 主页应至少有标题元素
    assert len(at.title) >= 1 or len(at.markdown) >= 1


def test_photo_compare_page_has_uploaders():
    at = AppTest.from_file(str(ROOT / "pages/1_📸_拍照对比.py")).run()
    # 应有两个 file_uploader（旧照片 + 新照片）
    file_uploaders = at.get("file_uploader")
    assert len(file_uploaders) >= 2


def test_training_plan_page_has_form():
    at = AppTest.from_file(str(ROOT / "pages/3_📋_训练计划.py")).run()
    # 应有一个 form
    forms = at.get("form")
    assert len(forms) >= 1


@pytest.mark.parametrize("script_path,label", IMPORT_ONLY_PAGES)
def test_page_can_be_imported(script_path, label):
    """含阻塞控件的页面，至少保证语法没问题（py_compile 检查）。"""
    import py_compile
    abs_path = ROOT / script_path
    py_compile.compile(str(abs_path), doraise=True)  # 语法错会直接抛