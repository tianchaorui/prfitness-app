"""简单的用户身份管理。

不引入账号体系——通过 URL query param 持久化用户名（关闭浏览器再开还在），
session_state 里始终有一个当前用户名。数据隔离靠 飞书表「用户」字段 过滤。
"""
import streamlit as st


DEFAULT_USER = "我"


def get_current_user() -> str:
    """获取当前用户名。优先 URL 参数，其次 session_state，最后默认「我」。"""
    try:
        qp_user = st.query_params.get("user")
        if qp_user:
            st.session_state.current_user = str(qp_user)
            return str(qp_user)
    except Exception:
        pass
    return st.session_state.get("current_user", DEFAULT_USER)


def set_user(name: str) -> None:
    """设置当前用户名，同步到 session_state 和 URL。"""
    name = (name or "").strip() or DEFAULT_USER
    st.session_state.current_user = name
    try:
        st.query_params["user"] = name
    except Exception:
        pass


def render_user_selector() -> str:
    """在页面上渲染用户名选择器。返回当前用户名。"""
    current = get_current_user()

    st.markdown(f"👤 **当前用户：`{current}`** （切换用户后只看到对应用户的数据）")

    with st.expander("切换用户", expanded=False):
        col1, col2 = st.columns([3, 1])
        with col1:
            new_name = st.text_input(
                "输入用户名",
                value=current,
                key=f"user_input_{current}",
                placeholder="例如：我 / 老婆 / 老公 / 小明",
            )
        with col2:
            if st.button("切换", key=f"user_switch_{current}"):
                if new_name and new_name != current:
                    set_user(new_name)
                    st.success(f"已切换到 `{new_name}`")
                    st.rerun()

    return current