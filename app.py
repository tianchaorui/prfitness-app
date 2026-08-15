"""AI 身材管家 - 主页

基于 Streamlit + DeepSeek + 飞书的个人健身管理 App
"""
# ============= 必须在最开始加载 .env =============
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

import streamlit as st

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