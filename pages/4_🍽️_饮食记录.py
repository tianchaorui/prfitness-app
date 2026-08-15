"""🍽️ 饮食记录 - 卡路里追踪"""
import streamlit as st
from datetime import datetime

from core.feishu_client import get_feishu_client
from core.config import FEISHU_TABLES


st.title("🍽️ 饮食记录")
st.markdown("**每日饮食追踪 + 卡路里管理**")

feishu = get_feishu_client()

if not feishu:
    st.warning("⚠️ 飞书未配置，饮食记录将无法保存。仍可输入查看效果。")

# 今日统计
st.markdown("### 📊 今日摄入")
col1, col2, col3, col4 = st.columns(4)

# 从飞书读取今日记录
today_records = []
if feishu:
    try:
        today_records = feishu.get_meal_records_today()
    except Exception as e:
        st.error(f"读取失败：{e}")

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

st.markdown("---")

# 记录一餐
st.markdown("### ➕ 记录一餐")

with st.form("meal_form"):
    col_a, col_b = st.columns(2)
    with col_a:
        meal_type = st.selectbox("餐次", ["早餐", "午餐", "晚餐", "加餐"])
    with col_b:
        record_date = st.date_input("日期", datetime.now())

    food = st.text_input("食物描述", placeholder="例如：鸡胸肉 100g + 糙米饭 150g")

    col_c, col_d, col_e, col_f = st.columns(4)
    with col_c:
        calories = st.number_input("卡路里 (kcal)", 0, 3000, 0, step=50)
    with col_d:
        protein = st.number_input("蛋白质 (g)", 0, 200, 0, step=5)
    with col_e:
        carbs = st.number_input("碳水 (g)", 0, 500, 0, step=10)
    with col_f:
        fat = st.number_input("脂肪 (g)", 0, 200, 0, step=5)

    note = st.text_input("备注", placeholder="例如：练后餐 / 嘴馋...")

    submitted = st.form_submit_button("✅ 记录", use_container_width=True)

    if submitted:
        if not food:
            st.error("请填写食物描述")
        elif not feishu:
            st.warning("飞书未配置，记录仅显示在页面上")
        else:
            try:
                record_id = feishu.add_record(
                    FEISHU_TABLES["meal_logs"],
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
                )
                st.success(f"✅ 已记录（{meal_type}：{food}，{calories} kcal）")
                st.balloons()
            except Exception as e:
                st.error(f"记录失败：{e}")

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

# 后续扩展
with st.expander("🔮 未来扩展：拍照识别食物"):
    st.markdown(
        """
        - 上传食物照片
        - AI 自动识别食物种类和重量
        - 自动估算卡路里和营养成分
        - 结合身体状态给个性化建议

        **已规划在 v2 版本，需要配置 DeepSeek-Vision**
        """
    )

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