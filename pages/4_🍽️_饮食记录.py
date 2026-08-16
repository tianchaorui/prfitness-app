"""🍽️ 饮食记录 - 卡路里追踪 + AI 拍照识别"""
import streamlit as st
from datetime import datetime

from core.feishu_client import get_feishu_client
from core.config import get_config
from core.food_analyzer import FoodAnalyzer
from core.user import render_user_selector


st.title("🍽️ 饮食记录")
st.markdown("**每日饮食追踪 + 卡路里管理**")

# 用户选择
current_user = render_user_selector()

feishu = get_feishu_client()
has_feishu = feishu is not None and bool(get_config("FEISHU_TABLE_MEAL"))

if not has_feishu:
    st.info("💡 提示：配置飞书后可将饮食记录保存到飞书表格，实现跨设备同步")

# 今日统计
st.markdown("### 📊 今日摄入")
col1, col2, col3, col4 = st.columns(4)

# 从飞书读取今日记录
today_records = []
if has_feishu:
    try:
        today_records = feishu.get_meal_records_today(user_id=current_user)
    except Exception:
        pass  # 静默失败，不影响用户体验

# 计算今日总计
total_cal = sum(r.get("fields", {}).get("卡路里", 0) or 0 for r in today_records)
total_protein = sum(r.get("fields", {}).get("蛋白质(g)", 0) or 0 for r in today_records)
total_carbs = sum(r.get("fields", {}).get("碳水(g)", 0) or 0 for r in today_records)
total_fat = sum(r.get("fields", {}).get("脂肪(g)", 0) or 0 for r in today_records)

with col1:
    st.metric("🔥 卡路里", f"{total_cal:.0f} kcal")
with col2:
    st.metric("🥩 蛋白质", f"{total_protein:.0f} g")
with col3:
    st.metric("🍚 碳水", f"{total_carbs:.0f} g")
with col4:
    st.metric("🥑 脂肪", f"{total_fat:.0f} g")

# 宏量目标进度条（从训练计划同步过来）
macros = st.session_state.get("daily_macros")
if macros and any(v > 0 for v in macros.values()):
    st.markdown("### 🎯 今日目标进度")
    targets = {
        "🔥 热量": (total_cal, macros.get("daily_calories", 0), "kcal"),
        "🥩 蛋白质": (total_protein, macros.get("daily_protein_g", 0), "g"),
        "🍚 碳水": (total_carbs, macros.get("daily_carbs_g", 0), "g"),
        "🥑 脂肪": (total_fat, macros.get("daily_fat_g", 0), "g"),
    }
    for label, (current, target, unit) in targets.items():
        if target > 0:
            pct = min(current / target, 1.5)
            try:
                st.progress(pct, text=f"{label}：{current:.0f} / {target} {unit} ({pct*100:.0f}%)")
            except TypeError:
                # Streamlit < 1.33 不支持 text 参数
                st.progress(pct)
                st.caption(f"{label}：{current:.0f} / {target} {unit} ({pct*100:.0f}%)")
    remaining_cal = macros.get("daily_calories", 0) - total_cal
    if remaining_cal > 0:
        st.info(f"💡 今日还可摄入 **{remaining_cal:.0f} kcal**")
    else:
        st.warning(f"⚠️ 已超出目标 **{abs(remaining_cal):.0f} kcal**")
else:
    st.caption("💡 去「训练计划」生成方案后，这里会显示每日营养目标进度")

st.markdown("---")

# 记录一餐
st.markdown("### ➕ 记录一餐")

# ============ 拍照识别区 ============
with st.expander("📸 **AI 拍照识别食物**（推荐：又快又准）", expanded=False):
    st.caption("上传一张食物照片，AI 自动识别食物、估算重量和营养。识别结果会**自动填入下方表单**，你可以再微调。")

    food_image = st.file_uploader(
        "选择食物照片",
        type=["jpg", "jpeg", "png"],
        key="food_image",
    )
    if food_image:
        st.image(food_image, caption="食物照片", width='stretch')

    user_goal = st.text_input(
        "你的目标（影响建议方向）",
        value=st.session_state.get("user_profile", {}).get("目标", "保持"),
        placeholder="例如：减脂 / 增肌 / 保持",
        key="ai_user_goal",
    )

    if st.button("🤖 AI 识别卡路里", width='stretch', disabled=not food_image):
        if not food_image:
            st.error("请先上传一张食物照片")
        else:
            with st.spinner("🤖 AI 正在识别食物和营养..."):
                try:
                    analyzer = FoodAnalyzer()
                    img_bytes = food_image.read()
                    result = analyzer.analyze_food(img_bytes, user_goal=user_goal)
                    if result is None:
                        st.error("❌ 识别失败：AI 返回内容无法解析，请重试或改用下方手动输入")
                    elif not result.get("food_items"):
                        st.warning("⚠️ AI 没识别到明确食物。试试换个角度、保证光线充足再拍")
                    else:
                        # 把结果写进 session_state，让下方表单能取到
                        st.session_state.ai_food_result = result
                        st.success(f"✅ 识别到 {len(result['food_items'])} 项食物")
                except Exception as e:
                    st.error(f"❌ 识别失败：{e}")

    # 展示识别结果（如果有）
    ai_result = st.session_state.get("ai_food_result")
    if ai_result and ai_result.get("food_items"):
        st.markdown("**识别结果**：")
        for item in ai_result["food_items"]:
            st.markdown(
                f"- {item['name']}：约 **{item['estimated_weight_g']:.0f} g**，"
                f"**{item['calories']:.0f} kcal**"
            )
        st.markdown(
            f"**总计**：{ai_result['total_calories']:.0f} kcal ｜ "
            f"蛋白质 {ai_result['total_protein_g']:.0f} g ｜ "
            f"碳水 {ai_result['total_carbs_g']:.0f} g ｜ "
            f"脂肪 {ai_result['total_fat_g']:.0f} g"
        )
        if ai_result.get("health_assessment"):
            st.info(f"💚 健康度：{ai_result['health_assessment']}")
        if ai_result.get("suggestion"):
            st.info(f"💡 建议：{ai_result['suggestion']}")

# ============ 手动记录表单（AI 识别结果会自动填入这里）============
with st.form("meal_form"):
    col_a, col_b = st.columns(2)
    with col_a:
        meal_type = st.selectbox("餐次", ["早餐", "午餐", "晚餐", "加餐"])
    with col_b:
        record_date = st.date_input("日期", datetime.now())

    # 如果有 AI 识别结果，用它预填；否则为空
    ai_prefill = st.session_state.get("ai_food_result", {}) or {}

    # 食物描述：把 AI 识别的食物名拼起来
    ai_items = ai_prefill.get("food_items", [])
    ai_food_text = "、".join(item["name"] for item in ai_items) if ai_items else ""

    food = st.text_input(
        "食物描述",
        value=ai_food_text,
        placeholder="例如：鸡胸肉 100g + 糙米饭 150g",
    )

    col_c, col_d, col_e, col_f = st.columns(4)
    with col_c:
        calories = st.number_input(
            "卡路里 (kcal)", 0, 3000,
            int(ai_prefill.get("total_calories", 0) or 0),
            step=50,
        )
    with col_d:
        protein = st.number_input(
            "蛋白质 (g)", 0, 200,
            int(ai_prefill.get("total_protein_g", 0) or 0),
            step=5,
        )
    with col_e:
        carbs = st.number_input(
            "碳水 (g)", 0, 500,
            int(ai_prefill.get("total_carbs_g", 0) or 0),
            step=10,
        )
    with col_f:
        fat = st.number_input(
            "脂肪 (g)", 0, 200,
            int(ai_prefill.get("total_fat_g", 0) or 0),
            step=5,
        )

    note = st.text_input("备注", placeholder="例如：练后餐 / 嘴馋...")

    submitted = st.form_submit_button("✅ 记录", width='stretch')

    if submitted:
        if not food:
            st.error("请填写食物描述")
        else:
            # 本地显示结果
            st.success(f"✅ 已记录（{meal_type}：{food}，{calories} kcal）")
            st.balloons()

            # 尝试保存到飞书（如果配置了）
            if has_feishu:
                try:
                    record_id = feishu.add_record(
                        get_config("FEISHU_TABLE_MEAL"),
                        {
                            "日期": int(datetime.combine(record_date, datetime.min.time()).timestamp() * 1000),
                            "餐次": meal_type,
                            "食物": food,
                            "卡路里": calories,
                            "蛋白质(g)": protein,
                            "碳水(g)": carbs,
                            "脂肪(g)": fat,
                            "备注": note,
                        },
                        user_id=current_user,
                    )
                    st.info(f"📚 已同步到飞书（记录ID: {record_id}）")
                except Exception as e:
                    st.warning(f"💾 本地记录成功，但飞书同步失败（{str(e)[:50]}）")
                    st.error(f"记录失败：{e}")

            # 清掉 AI 预填状态，避免下一次记录被错误预填
            st.session_state.ai_food_result = None

# 今日明细
st.markdown("---")
st.markdown("### 📋 今日明细")
if today_records:
    for r in today_records:
        fields = r.get("fields", {})
        with st.expander(f"🍽️ {fields.get('餐次', '?')} - {fields.get('食物', '?')} ({fields.get('卡路里', 0)} kcal)"):
            st.markdown(f"- **卡路里**: {fields.get('卡路里', 0)} kcal")
            st.markdown(f"- **蛋白质**: {fields.get('蛋白质(g)', 0)} g")
            st.markdown(f"- **碳水**: {fields.get('碳水(g)', 0)} g")
            st.markdown(f"- **脂肪**: {fields.get('脂肪(g)', 0)} g")
            if fields.get("备注"):
                st.markdown(f"- **备注**: {fields.get('备注')}")
else:
    st.info("还没有记录，去填一填吧")

# 食物卡路里速查
with st.expander("📚 常见食物卡路里速查"):
    st.markdown(
        """
        | 食物 | 量 | 卡路里 |
        |------|----|----|
        | 鸡胸肉 | 100g | 165 kcal |
        | 牛肉 | 100g | 250 kcal |
        | 鸡蛋 | 1 个 | 70 kcal |
        | 米饭 | 100g | 130 kcal |
        | 全麦面包 | 1 片 | 80 kcal |
        | 香蕉 | 1 根 | 90 kcal |
        | 苹果 | 1 个 | 95 kcal |
        | 牛奶 | 250ml | 150 kcal |
        | 酸奶 | 100g | 70 kcal |
        | 花生 | 30g | 170 kcal |
        """
    )