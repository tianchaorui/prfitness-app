"""配置加载

借鉴 quantum-fit 的双来源模式：
1. Streamlit Secrets（云端部署用）
2. .env 文件（本地开发用）
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st

# ============= 优先级 1: 加载 .env 文件 =============
# 从项目根目录加载 .env 文件（本地开发用）
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)


def get_config(key: str, default: str = "") -> str:
    """统一获取配置：Streamlit Secrets > 环境变量 > 默认值
    
    每次调用时都会重新检查，避免模块初始化时的缓存问题
    """
    # 1. Streamlit Secrets（部署到 Streamlit Cloud 用）
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    # 2. 环境变量 / .env
    return os.getenv(key, default)


# ============= AI 配置 =============
# 注意：这些是在模块加载时的值，运行时应该用 get_config() 动态获取
DEEPSEEK_API_KEY = get_config("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = get_config("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = get_config("DEEPSEEK_MODEL", "deepseek-chat")
# 视觉模型：默认复用文本模型（向后兼容，老配置不动也照常工作）
DEEPSEEK_VISION_MODEL = get_config("DEEPSEEK_VISION_MODEL", DEEPSEEK_MODEL)

# ============= 飞书配置 =============
FEISHU_APP_ID = get_config("FEISHU_APP_ID")
FEISHU_APP_SECRET = get_config("FEISHU_APP_SECRET")
# 多维表格的 app_token（在飞书表格 URL 里能找到）
FEISHU_APP_TOKEN = get_config("FEISHU_APP_TOKEN")

# 5 张表的 table_id（在飞书表格的「字段」设置里能看到）
FEISHU_TABLES = {
    "body_records": get_config("FEISHU_TABLE_BODY", ""),
    "workout_logs": get_config("FEISHU_TABLE_WORKOUT", ""),
    "meal_logs": get_config("FEISHU_TABLE_MEAL", ""),
    "ai_conversations": get_config("FEISHU_TABLE_CONVERSATION", ""),
    "user_profile": get_config("FEISHU_TABLE_PROFILE", ""),
}


def check_config() -> list:
    """检查必要配置是否齐全，返回缺失项列表
    
    运行时动态检查，避免缓存问题
    """
    missing = []
    # 每次调用时重新获取配置值
    deepseek_key = get_config("DEEPSEEK_API_KEY")
    if not deepseek_key:
        missing.append("DEEPSEEK_API_KEY")
    
    # 飞书配置是可选的
    feishu_id = get_config("FEISHU_APP_ID")
    if not feishu_id:
        missing.append("FEISHU_APP_ID")
    feishu_secret = get_config("FEISHU_APP_SECRET")
    if not feishu_secret:
        missing.append("FEISHU_APP_SECRET")
    feishu_token = get_config("FEISHU_APP_TOKEN")
    if not feishu_token:
        missing.append("FEISHU_APP_TOKEN")
    
    return missing


def show_config_status():
    """在 UI 里展示配置状态（借鉴 quantum-fit 的友好错误提示）
    
    注意：DEEPSEEK_API_KEY 在运行时动态加载，不需要提前检查
    只警告飞书的可选配置缺失
    """
    feishu_id = get_config("FEISHU_APP_ID")
    feishu_secret = get_config("FEISHU_APP_SECRET")
    feishu_token = get_config("FEISHU_APP_TOKEN")
    
    missing = []
    if not feishu_id:
        missing.append("FEISHU_APP_ID")
    if not feishu_secret:
        missing.append("FEISHU_APP_SECRET")
    if not feishu_token:
        missing.append("FEISHU_APP_TOKEN")
    
    if missing:
        st.warning(
            f"⚠️ 以下飞书配置缺失: {', '.join(missing)}\n\n"
            "请在 `.env` 文件或 Streamlit Secrets 中配置。\n\n"
            "**没有配置也不影响 Demo**，可以体验 AI 对话功能。"
        )
        return False
    return True