"""📋 训练计划 - 借鉴 quantum-fit 的核心页面"""
import streamlit as st

from core.plan_generator import PlanGenerator, render_plan_form, render_plan_result
from core.config import show_config_status, get_config
from core.user import render_user_selector


st.title("📋 AI 训练计划")
st.markdown("**输入档案 → 生成个性化周计划**")

# 用户选择
current_user = render_user_selector()

if not show_config_status():
    st.warning("DEEPSEEK_API_KEY 未配置，无法使用")

# 缓存上次的结果
if "last_plan" not in st.session_state:
    st.session_state.last_plan = None
if "last_profile" not in st.session_state:
    st.session_state.last_profile = None

# 表单
profile = render_plan_form()

# 生成计划
if profile:
    generator = PlanGenerator()
    with st.spinner("🤖 AI 教练正在为你定制周计划..."):
        plan_text = generator.generate(profile)

    st.session_state.last_plan = plan_text
    st.session_state.last_profile = profile

    # 显示
    render_plan_result(plan_text)

    # 保存按钮（仅在飞书配置完整时显示）
    from core.feishu_client import get_feishu_client
    
    feishu = get_feishu_client()
    has_feishu = feishu is not None and bool(get_config("FEISHU_TABLE_WORKOUT"))
    
    if has_feishu:
        if st.button("💾 保存到飞书", width='stretch'):
            try:
                feishu_id = generator.save_to_feishu(profile, plan_text, user_id=current_user)
                if feishu_id:
                    st.success(f"✅ 已保存到飞书（记录ID: {feishu_id}）")
                else:
                    st.error("保存失败，请检查飞书配置")
            except Exception as e:
                st.error(f"保存失败：{str(e)}")
    else:
        st.info("💡 提示：配置飞书后可保存计划到飞书表格")

    # 下载
    st.download_button(
        "📄 下载计划",
        data=plan_text.encode("utf-8"),
        file_name=f"训练计划_{profile['goal']}.md",
        mime="text/markdown",
        width='stretch',
    )

# 显示之前的结果（如果用户切回来）
elif st.session_state.last_plan:
    st.markdown("---")
    st.markdown("### 📋 之前的计划")
    render_plan_result(st.session_state.last_plan)

st.markdown("---")
with st.expander("💡 计划生成说明"):
    st.markdown(
        """
        - 计划根据你的**身高、体重、年龄、性别**个性化生成
        - 包含**周训练 + 营养 + 补剂 + 安全**建议
        - 建议每周重新生成一次，根据进度调整
        - 配合「我的数据」页面追踪效果最佳
        """
    )