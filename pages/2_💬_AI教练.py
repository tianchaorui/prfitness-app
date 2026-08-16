"""💬 AI 教练 - RAG 健身问答"""
import streamlit as st
import uuid

from core.rag import FitnessRAG
from core.config import show_config_status


st.title("💬 AI 私人教练")
st.markdown("**基于健身知识库的智能问答**——有上下文、能引用、可保存")

# 配置检查（只检查可选的飞书配置）
show_config_status()

# AI 配置预检：避免用户输入后才看到错误
from core.ai_client import get_ai_client, get_ai_last_error
from core.config import get_config
ai = get_ai_client()
if not ai:
    # 收集到底缺什么，给用户精确指引
    missing = []
    if not get_config("DEEPSEEK_API_KEY"):
        missing.append("`DEEPSEEK_API_KEY`（缺 API key）")
    if not get_config("DEEPSEEK_BASE_URL"):
        missing.append("`DEEPSEEK_BASE_URL`")
    if not get_config("DEEPSEEK_MODEL"):
        missing.append("`DEEPSEEK_MODEL`")

    last_err = get_ai_last_error()
    error_detail = f"\n\n**初始化错误**：`{last_err}`" if last_err else ""

    st.error(
        f"❌ **AI 客户端未配置**\n\n"
        f"{'以下变量未设置：' + chr(10).join('- ' + m for m in missing) if missing else '所有变量都有，但初始化失败，请看下面错误。'}"
        f"{error_detail}\n\n"
        f"**修复步骤**：\n"
        f"1. 进 https://share.streamlit.io/ → 你的 app → ⚙️ Settings → Secrets\n"
        f"2. 确保这 4 行都填了：\n"
        f"```toml\n"
        f'DEEPSEEK_API_KEY = "你的硅基流动 key"\n'
        f'DEEPSEEK_BASE_URL = "https://api.siliconflow.cn/v1"\n'
        f'DEEPSEEK_MODEL = "Qwen/Qwen2.5-7B-Instruct"\n'
        f'DEEPSEEK_VISION_MODEL = "Qwen/Qwen3-VL-32B-Instruct"\n'
        f"```\n"
        f"3. Save → 等 30 秒自动重启 → 刷新页面"
    )
    st.stop()

# 初始化 RAG
@st.cache_resource
def get_rag():
    return FitnessRAG()

rag = get_rag()

# 会话管理
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "messages" not in st.session_state:
    st.session_state.messages = []

# 侧边栏：用户档案（让 AI 更懂你）
with st.sidebar:
    st.markdown("### 👤 我的档案")
    with st.form("user_profile_form"):
        age = st.number_input("年龄", 10, 100, 25, key="age")
        gender = st.selectbox("性别", ["男", "女"], key="gender")
        goal = st.selectbox("目标", ["增肌", "减脂", "塑形", "保持"], key="goal")
        experience = st.selectbox("经验", ["新手", "进阶", "专业"], key="exp")
        if st.form_submit_button("💾 保存档案"):
            st.session_state.user_profile = {
                "年龄": age, "性别": gender, "目标": goal, "经验": experience,
            }
            st.success("已保存")

    st.markdown("---")
    st.markdown("### 🗑️ 管理")
    if st.button("清空对话", width='stretch'):
        st.session_state.messages = []
        st.rerun()

    st.markdown(f"**会话 ID**: `{st.session_state.session_id}`")

# 显示历史对话
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 用户输入
if prompt := st.chat_input("问问你的健身问题..."):
    # 显示用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # AI 回答
    with st.chat_message("assistant"):
        with st.spinner("🤔 AI 思考中..."):
            user_profile = st.session_state.get("user_profile", {})
            response = rag.ask(prompt, user_profile=user_profile)
            # 上游失败时返回 "❌ ..." 字符串，要显示成红色警告而不是聊天气泡
            if response.startswith("❌"):
                st.error(response)
            else:
                st.markdown(response)

    # 只有真正成功时才把回复记进会话历史（避免错误信息污染上下文）
    if not response.startswith("❌"):
        st.session_state.messages.append({"role": "assistant", "content": response})

    # 保存到飞书（异步，不阻塞）—— 只在 AI 真正回复成功时才保存
    if not response.startswith("❌"):
        try:
            rag.save_conversation("user", prompt, st.session_state.session_id)
            rag.save_conversation("assistant", response, st.session_state.session_id)
        except Exception:
            pass  # 保存失败不影响体验

# 快捷问题（首次打开时显示）
if not st.session_state.messages:
    st.markdown("---")
    st.markdown("### 💡 试试这些问题：")
    col1, col2 = st.columns(2)

    sample_questions = [
        "我是上班族，久坐，想瘦肚子，怎么练？",
        "深蹲膝盖响怎么办？",
        "增肌期每天要吃多少蛋白质？",
        "有氧和无氧哪个先做？",
        "如何计算我的基础代谢？",
        "减脂期可以吃零食吗？",
    ]

    for i, q in enumerate(sample_questions):
        col = col1 if i % 2 == 0 else col2
        if col.button(q, key=f"sample_{i}", width='stretch'):
            st.session_state.messages.append({"role": "user", "content": q})
            st.rerun()