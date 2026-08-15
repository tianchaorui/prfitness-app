"""💬 AI 教练 - RAG 健身问答"""
import streamlit as st
import uuid

from core.rag import FitnessRAG
from core.config import show_config_status


st.title("💬 AI 私人教练")
st.markdown("**基于健身知识库的智能问答**——有上下文、能引用、可保存")

# 配置检查（只检查可选的飞书配置）
show_config_status()

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
            st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})

    # 保存到飞书（异步，不阻塞）
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