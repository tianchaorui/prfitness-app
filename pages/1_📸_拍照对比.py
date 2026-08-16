"""📸 拍照对比 - 核心差异化功能"""
import streamlit as st
from datetime import datetime, timedelta

from core.photo_analyzer import PhotoAnalyzer
from core.feishu_client import get_feishu_client
from core.config import get_config, show_config_status


st.title("📸 身材对比分析")
st.markdown("**核心功能**：上传两张身材照，AI 自动对比变化，给出评分和改进建议")

# 检查飞书配置（仅在需要时）
feishu = get_feishu_client()
has_feishu = feishu is not None and bool(get_config("FEISHU_TABLE_BODY"))

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 1️⃣ 上传旧照片")
    old_photo = st.file_uploader(
        "选择较早的照片（参考）",
        type=["jpg", "jpeg", "png"],
        key="old_photo",
        help="建议 1-3 个月前的照片",
    )
    if old_photo:
        st.image(old_photo, caption="旧照片", width='stretch')

with col2:
    st.markdown("### 2️⃣ 上传新照片")
    new_photo = st.file_uploader(
        "选择今天的照片",
        type=["jpg", "jpeg", "png"],
        key="new_photo",
    )
    if new_photo:
        st.image(new_photo, caption="新照片", width='stretch')

# 间隔天数
st.markdown("### 3️⃣ 设置对比间隔")
days = st.slider(
    "两张照片间隔多少天？",
    min_value=1,
    max_value=365,
    value=30,
    help="如实填写，AI 会根据时间评估进步速度",
)

# 可选：用户背景
with st.expander("📝 添加用户背景（可选，让 AI 更精准）"):
    user_context = st.text_area(
        "你的健身目标、当前情况",
        placeholder="例如：目标减脂，175/80kg，刚开始健身 3 个月",
        key="user_context",
    )

# 分析按钮
st.markdown("---")
if st.button("🔍 开始 AI 对比分析", type="primary", width='stretch'):
    if not old_photo or not new_photo:
        st.error("请先上传两张照片")
        st.stop()

    if not show_config_status():
        st.warning("DEEPSEEK_API_KEY 未配置，无法使用 AI 分析")
        st.stop()

    analyzer = PhotoAnalyzer()

    with st.spinner("🤖 AI 正在分析两张照片的变化..."):
        try:
            old_bytes = old_photo.read()
            new_bytes = new_photo.read()

            result = analyzer.compare_two(
                old_image_bytes=old_bytes,
                new_image_bytes=new_bytes,
                days_between=days,
                user_context=user_context or "未提供",
            )

            if not result:
                st.error("AI 返回结果解析失败，请重试")
                st.stop()

            # 展示结果
            st.markdown("---")
            st.markdown("## 🎯 AI 分析结果")

            # 评分卡片
            score = result.get("progress_score", 0)
            overall = result.get("overall_change", "持平")
            summary = result.get("summary", "")

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric(
                    "📊 进步评分",
                    f"{score}/100",
                    delta=f"{score - 50:+d}" if score else None,
                )
            with col_b:
                emoji = {"进步": "📈", "退步": "📉", "持平": "➡️"}.get(overall, "📊")
                st.metric("🎯 整体变化", f"{emoji} {overall}")
            with col_c:
                st.metric("⏱️ 间隔天数", f"{days} 天")

            # 一句话总结
            if summary:
                st.info(f"💡 **AI 总结**：{summary}")

            # 具体变化
            changes = result.get("specific_changes", [])
            if changes:
                st.markdown("### 🔍 具体变化")
                for change in changes:
                    st.markdown(f"- ✅ {change}")

            # 关注问题
            concerns = result.get("concerns", [])
            if concerns:
                st.markdown("### ⚠️ 需要关注")
                for concern in concerns:
                    st.markdown(f"- ⚠️ {concern}")

            # 下一步建议
            next_steps = result.get("next_steps", [])
            if next_steps:
                st.markdown("### 🎯 下一步建议")
                for i, step in enumerate(next_steps, 1):
                    st.markdown(f"{i}. 📌 {step}")

            # 保存按钮（仅在配置飞书时显示）
            st.markdown("---")
            col_save1, col_save2 = st.columns(2)
            with col_save1:
                if has_feishu:
                    if st.button("💾 保存分析到飞书", width='stretch'):
                        with st.spinner("保存中..."):
                            try:
                                record_id = analyzer.save_to_feishu(
                                    image_bytes=new_bytes,
                                    analysis=result,
                                    note=user_context,
                                )
                                if record_id:
                                    st.success(f"✅ 已保存（记录ID: {record_id}）")
                                else:
                                    st.error("保存失败")
                            except Exception as e:
                                st.error(f"保存失败：{str(e)}")
                else:
                    st.info("💡 提示：配置飞书后可保存分析结果")

            with col_save2:
                # 下载报告
                report_text = f"""# AI 身材对比报告

## 📊 评分：{score}/100
## 🎯 整体：{overall}

## 💡 总结
{summary}

## 🔍 具体变化
{chr(10).join(f'- {c}' for c in changes)}

## ⚠️ 关注
{chr(10).join(f'- {c}' for c in concerns)}

## 🎯 下一步
{chr(10).join(f'{i}. {s}' for i, s in enumerate(next_steps, 1))}

---
生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}
"""
                st.download_button(
                    "📄 下载报告",
                    data=report_text.encode("utf-8"),
                    file_name=f"对比报告_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown",
                    width='stretch',
                )

        except Exception as e:
            import traceback
            st.error(f"❌ 分析失败：{e}")
            with st.expander("详细错误（排查用）"):
                st.code(traceback.format_exc())

# 使用说明
with st.expander("💡 如何拍出有效的对比照片？"):
    st.markdown(
        """
        - **同一光线**：自然光最佳，避免一边亮一边暗
        - **同一角度**：正/侧/后，三个角度各拍一张
        - **同一姿势**：放松站立，不要刻意绷紧或摆 pose
        - **同一着装**：贴身衣物最佳，方便 AI 识别
        - **同一时间**：都是早上起床后空腹，效果最准
        """
    )