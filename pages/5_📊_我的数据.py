"""📊 我的数据 - 进度可视化"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from core.feishu_client import get_feishu_client
from core.config import FEISHU_TABLES
from core.ai_client import get_ai_client
from core.prompts import MONTHLY_REPORT_PROMPT


st.title("📊 我的数据")
st.markdown("**所有进度一目了然**——体重、围度、AI 月报")

feishu = get_feishu_client()

# 读取身体记录
records = []
if feishu:
    try:
        records = feishu.get_body_records(limit=90)
    except Exception as e:
        st.error(f"读取失败：{e}")

if not records:
    st.info(
        "📌 **还没有数据**\n\n"
        "先去「拍照对比」页面记录第一条数据，或直接在飞书表格里手动添加。"
    )
    st.stop()

# 转成 DataFrame
df_data = []
for r in records:
    fields = r.get("fields", {})
    df_data.append({
        "日期": fields.get("日期"),
        "体重(kg)": fields.get("体重(kg)"),
        "体脂率(%)": fields.get("体脂率(%)"),
        "胸围(cm)": fields.get("胸围(cm)"),
        "腰围(cm)": fields.get("腰围(cm)"),
        "臀围(cm)": fields.get("臀围(cm)"),
        "臂围(cm)": fields.get("臂围(cm)"),
    })

df = pd.DataFrame(df_data)
# 转换日期
if "日期" in df.columns:
    df["日期"] = pd.to_datetime(df["日期"], unit="ms", errors="coerce")
    df = df.dropna(subset=["日期"])
    df = df.sort_values("日期")

st.markdown("---")

# 关键指标卡片
st.markdown("### 🎯 关键指标")
if not df.empty:
    latest = df.iloc[-1]
    if len(df) > 1:
        prev = df.iloc[-2]
    else:
        prev = latest

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if pd.notna(latest.get("体重(kg)")):
            delta = (latest["体重(kg)"] - prev["体重(kg)"]) if pd.notna(prev.get("体重(kg)")) else None
            st.metric(
                "⚖️ 体重",
                f"{latest['体重(kg)']:.1f} kg",
                delta=f"{delta:+.1f} kg" if delta is not None else None,
            )

    with col2:
        if pd.notna(latest.get("体脂率(%)")):
            delta = (latest["体脂率(%)"] - prev["体脂率(%)"]) if pd.notna(prev.get("体脂率(%)")) else None
            st.metric(
                "📊 体脂率",
                f"{latest['体脂率(%)']:.1f}%",
                delta=f"{delta:+.1f}%" if delta is not None else None,
            )

    with col3:
        if pd.notna(latest.get("腰围(cm)")):
            delta = (latest["腰围(cm)"] - prev["腰围(cm)"]) if pd.notna(prev.get("腰围(cm)")) else None
            st.metric(
                "📏 腰围",
                f"{latest['腰围(cm)']:.1f} cm",
                delta=f"{delta:+.1f} cm" if delta is not None else None,
            )

    with col4:
        # 记录天数
        days = (df["日期"].max() - df["日期"].min()).days if len(df) > 1 else 0
        st.metric("📅 已记录", f"{days} 天")

st.markdown("---")

# 体重曲线
st.markdown("### 📈 体重趋势")
weight_df = df.dropna(subset=["体重(kg)"])
if not weight_df.empty:
    st.line_chart(weight_df.set_index("日期")["体重(kg)"], height=300)
else:
    st.info("暂无体重数据")

# 围度对比
st.markdown("### 📏 围度变化")
circumference_cols = ["胸围(cm)", "腰围(cm)", "臀围(cm)", "臂围(cm)"]
circ_df = df[["日期"] + [c for c in circumference_cols if c in df.columns]].copy()
circ_df = circ_df.dropna(axis=1, how="all")
if len(circ_df.columns) > 1:
    st.line_chart(circ_df.set_index("日期"), height=300)
else:
    st.info("暂无围度数据")

st.markdown("---")

# AI 月报
st.markdown("### 🤖 AI 月度报告")
st.caption("基于近 30 天数据生成")

if st.button("📝 生成月报", use_container_width=True):
    ai = get_ai_client()
    if not ai:
        st.error("DEEPSEEK_API_KEY 未配置")
    elif df.empty:
        st.info("数据不足，无法生成月报")
    else:
        # 取最近 30 天
        recent_df = df.tail(30).copy()
        recent_df["日期"] = recent_df["日期"].dt.strftime("%Y-%m-%d")

        with st.spinner("🤖 AI 分析中..."):
            prompt = MONTHLY_REPORT_PROMPT.format(data=recent_df.to_string(index=False))
            report = ai.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000,
            )

        st.markdown("---")
        st.markdown(report)

        # 下载报告
        st.download_button(
            "📄 下载月报",
            data=report.encode("utf-8"),
            file_name=f"AI月报_{datetime.now().strftime('%Y%m')}.md",
            mime="text/markdown",
        )

# 历史照片墙
st.markdown("---")
st.markdown("### 📸 历史照片")
st.caption("你的身材变化轨迹")

if feishu:
    try:
        photo_records = [r for r in records if r.get("fields", {}).get("今日照片")]
        if photo_records:
            cols = st.columns(min(4, len(photo_records)))
            for i, r in enumerate(photo_records[:8]):
                fields = r.get("fields", {})
                photo_list = fields.get("今日照片", [])
                if photo_list:
                    # 飞书附件格式：[{file_token, name, ...}]
                    # 实际访问需要调用下载接口，这里简化处理
                    date_str = ""
                    if fields.get("日期"):
                        date_str = datetime.fromtimestamp(fields["日期"]/1000).strftime("%Y-%m-%d")
                    cols[i % 4].markdown(f"📷 {date_str}<br>（点击查看完整照片）")
        else:
            st.info("还没有照片，去「拍照对比」页面记录第一张吧")
    except Exception as e:
        st.warning(f"照片加载失败：{e}")

# 数据导出
st.markdown("---")
with st.expander("📥 导出我的数据"):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📊 下载 CSV（Excel 可打开）",
        data=csv,
        file_name=f"fitness_data_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

# 使用统计
st.markdown("---")
st.markdown("### 📊 数据统计")
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.metric("总记录数", f"{len(df)} 条")
with col_b:
    if not df.empty:
        st.metric("最早记录", df["日期"].min().strftime("%Y-%m-%d"))
with col_c:
    if not df.empty:
        st.metric("最新记录", df["日期"].max().strftime("%Y-%m-%d"))