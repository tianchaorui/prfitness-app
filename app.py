"""AI 身材管家 - 主页

基于 Streamlit + DeepSeek + 飞书的个人健身管理 App
"""
# ============= 必须在最开始加载 .env =============
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

import streamlit as st
import io
import base64
from PIL import Image

from core.config import check_config, show_config_status

# ============= 页面配置 =============
st.set_page_config(
    page_title="AI 身材管家",
    page_icon="💪",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ============= 主页内容 =============
st.title("💪 AI 身材管家")
st.markdown("### 你的私人健身数据管家")

st.info(
    """
    **核心理念**：和豆包等通用 AI 助手的区别——
    - 📊 **有数据**：记住你的体重、围度、训练历史
    - 📸 **有对比**：跨时间的照片对比分析
    - 🎯 **有趋势**：自动生成进度报告和预测
    - 💾 **可追溯**：所有数据存在你自己的飞书表格
    """
)

st.markdown("---")

st.markdown("### 🚀 开始使用")
st.markdown(
    """
    请从左侧菜单进入各个功能：

    | 功能 | 说明 |
    |------|------|
    | 📸 **拍照对比** | 上传两张身材照，AI 自动对比分析变化 |
    | 💬 **AI 教练** | 基于健身知识库的智能问答 |
    | 📋 **训练计划** | 输入档案，AI 生成个性化周计划 |
    | 🍽️ **饮食记录** | 记录每日饮食，追踪卡路里 |
    | 📊 **我的数据** | 体重曲线、围度趋势、AI 月报 |
    """
)

st.markdown("---")

# ============= 配置检查 =============
st.markdown("### ⚙️ 配置状态")
if show_config_status():
    st.success("✅ 所有配置齐全，可以正常使用")
else:
    st.warning(
        """
        **部分功能可能不可用**，但仍可以体验：

        - ✅ AI 教练对话（只需 DEEPSEEK_API_KEY）
        - ✅ 拍照对比（只需 DEEPSEEK_API_KEY）
        - ✅ 训练计划生成（只需 DEEPSEEK_API_KEY）
        - ❌ 数据持久化（需要飞书配置）
        """
    )

# ============= 诊断面板（看实际部署了什么）============
with st.expander("🔍 **诊断面板**——看实际配置值（这里决定功能能不能用）", expanded=False):
    from core.config import (
        get_config, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DEEPSEEK_VISION_MODEL,
        FEISHU_TABLES,
    )
    from core.ai_client import get_ai_client
    from core.feishu_client import get_feishu_client

    def mask(s: str, keep: int = 4) -> str:
        if not s:
            return "❌ 未配置"
        return f"{s[:4]}...{s[-keep:]}" if len(s) > keep + 4 else "***"

    st.markdown("**AI 配置**")
    api_key = get_config("DEEPSEEK_API_KEY")
    st.code(
        f"DEEPSEEK_API_KEY      = {mask(api_key, 4)}\n"
        f"DEEPSEEK_BASE_URL     = {DEEPSEEK_BASE_URL or '❌ 未配置'}\n"
        f"DEEPSEEK_MODEL        = {DEEPSEEK_MODEL or '❌ 未配置'}\n"
        f"DEEPSEEK_VISION_MODEL = {DEEPSEEK_VISION_MODEL or '❌ 未配置'}",
        language="bash",
    )

    st.markdown("**飞书配置**")
    st.code(
        f"FEISHU_APP_ID         = {mask(get_config('FEISHU_APP_ID'), 4)}\n"
        f"FEISHU_APP_SECRET     = {mask(get_config('FEISHU_APP_SECRET'), 0)}\n"
        f"FEISHU_APP_TOKEN      = {mask(get_config('FEISHU_APP_TOKEN'), 4)}\n"
        f"FEISHU_TABLE_BODY     = {FEISHU_TABLES.get('body_records') or '❌ 未配置'}",
        language="bash",
    )

    st.markdown("**连通性测试**")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("🤖 测试 AI", width='stretch'):
            with st.spinner(""):
                try:
                    client = get_ai_client()
                    if not client:
                        from core.ai_client import get_ai_last_error
                        st.error(f"❌ AI 客户端未配置：{get_ai_last_error() or '未知原因'}")
                    else:
                        r = client.chat(
                            messages=[{"role": "user", "content": "ping"}],
                            temperature=0.0,
                            max_tokens=20,
                        )
                        if r.startswith("❌"):
                            st.error(r)
                        else:
                            st.success(f"✅ AI 通：{r[:60]}")
                except Exception as e:
                    st.error(f"❌ {e}")
    with col_b:
        if st.button("👁️ 测试 Vision", width='stretch'):
            with st.spinner(""):
                try:
                    client = get_ai_client()
                    if not client:
                        st.error("❌ AI 客户端未配置")
                    else:
                        # 1x1 红色像素
                        tiny = Image.new("RGB", (1, 1), color=(255, 0, 0))
                        buf = io.BytesIO(); tiny.save(buf, format="PNG")
                        b64 = base64.b64encode(buf.getvalue()).decode()
                        r = client.chat_with_vision(
                            text="这张图什么颜色？只回答颜色名。",
                            image_urls=[f"data:image/png;base64,{b64}"],
                            temperature=0.0,
                            max_tokens=10,
                        )
                        if r.startswith("❌"):
                            st.error(r)
                        else:
                            st.success(f"✅ Vision 通：{r[:60]}")
                except Exception as e:
                    st.error(f"❌ {e}")
    with col_c:
        if st.button("📋 测试飞书", width='stretch'):
            with st.spinner(""):
                try:
                    fc = get_feishu_client()
                    if not fc:
                        st.error("❌ 飞书未配置")
                    else:
                        items = fc.list_records(FEISHU_TABLES.get("body_records", ""), page_size=1)
                        st.success(f"✅ 飞书通：拿到 {len(items)} 条样例")
                except Exception as e:
                    st.error(f"❌ {e}")

st.markdown("---")

# ============= 快速开始 =============
with st.expander("📚 如何配置环境变量？"):
    st.markdown(
        """
        **本地开发**：在项目根目录创建 `.env` 文件：

        ```
        DEEPSEEK_API_KEY=sk-xxx
        DEEPSEEK_BASE_URL=https://api.deepseek.com
        FEISHU_APP_ID=cli_xxx
        FEISHU_APP_SECRET=xxx
        FEISHU_APP_TOKEN=xxx
        ```

        **Streamlit Cloud 部署**：在 App Settings → Secrets 里填入同样的内容。
        """
    )

with st.expander("🔧 如何获取 API Key？"):
    st.markdown(
        """
        - **DeepSeek**: https://platform.deepseek.com/ 注册 → API Keys
        - **飞书**: https://open.feishu.cn/ 创建应用 → 多维表格权限
        """
    )

st.caption("💡 提示：第一次使用建议先去「训练计划」生成方案，体验完整流程")

# 显示当前部署的 commit hash（方便确认线上版本）
import subprocess
try:
    _commit = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(Path(__file__).parent),
        stderr=subprocess.DEVNULL,
    ).decode().strip()
except Exception:
    _commit = "unknown"
st.caption(f"🔖 当前部署版本：`{_commit}` | Streamlit Cloud 跑的不是这个？→ 看 Logs / 强制 Reboot")