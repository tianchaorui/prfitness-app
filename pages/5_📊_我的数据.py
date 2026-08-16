"""📊 我的数据 - 进度可视化"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from core.feishu_client import get_feishu_client
from core.config import get_config
from core.ai_client import get_ai_client
from core.prompts import MONTHLY_REPORT_PROMPT
from core.user import render_user_selector


st.title("📊 我的数据")
st.markdown("**所有进度一目了然**——体重、围度、AI 月报")

# 用户选择
current_user = render_user_selector()

try:
    feishu = get_feishu_client()
except Exception as e:
    st.error(f"❌ 飞书客户端初始化失败：{e}")
    st.stop()

has_feishu = feishu is not None and bool(get_config("FEISHU_TABLE_BODY"))

if not has_feishu:
    st.info(
        "📌 **需要飞书配置才能查看数据**\n\n"
        "请先在 `.env` 或 Streamlit Secrets 中配置飞书信息，"
        "然后在飞书多维表格「身体记录」中添加数据。"
    )
    st.stop()

# 读取身体记录
records = []
try:
    records = feishu.get_body_records(limit=90, user_id=current_user)
except Exception as e:
    import traceback
    print(f"[MyData] 读取飞书数据失败: {e}", flush=True)
    traceback.print_exc()
    st.error(f"❌ 读取飞书数据失败：{e}")
    with st.expander("详细错误（排查用）"):
        st.code(traceback.format_exc())
    st.stop()

if not records:
    st.info(
        "📌 **表里还没有数据**\n\n"
        "可能原因：\n"
        "- 多维表格「身体记录」里没有任何记录\n"
        "- 飞书 app 没被授权读这张表（去飞书 UI 把 app 加为「可编辑」）\n"
        "- APP_TOKEN / FEISHU_TABLE_BODY 填错了"
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

try:
    df = pd.DataFrame(df_data)
    # 转换日期——兼容多种格式：毫秒时间戳、秒时间戳、字符串日期
    if "日期" in df.columns:
        def parse_date(val):
            if pd.isna(val) or val is None:
                return pd.NaT
            if isinstance(val, (int, float)):
                # 飞书 Date 字段可能是毫秒或秒时间戳
                # 判断依据： > 1e12 视为毫秒，否则视为秒
                if val > 1e12:
                    return pd.to_datetime(val, unit="ms", errors="coerce")
                else:
                    return pd.to_datetime(val, unit="s", errors="coerce")
            # 字符串日期（如 "2026-08-16"）
            return pd.to_datetime(val, errors="coerce")

        df["日期"] = df["日期"].apply(parse_date)
        df = df.dropna(subset=["日期"])
        df = df.sort_values("日期")

    # 数字列强制转 numeric——飞书 API 可能把 Number 字段以 string 形式返回
    numeric_cols = ["体重(kg)", "体脂率(%)", "胸围(cm)", "腰围(cm)", "臀围(cm)", "臂围(cm)"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
except Exception as e:
    st.error(f"❌ 数据解析失败：{e}")
    with st.expander("详细错误（排查用）"):
        import traceback
        st.code(traceback.format_exc())
    st.stop()

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
    try:
        st.line_chart(weight_df.set_index("日期")["体重(kg)"])
    except Exception as e:
        st.warning(f"体重图表加载失败：{e}")
else:
    st.info("暂无体重数据")

# 围度对比
st.markdown("### 📏 围度变化")
circumference_cols = ["胸围(cm)", "腰围(cm)", "臀围(cm)", "臂围(cm)"]
try:
    circ_df = df[["日期"] + [c for c in circumference_cols if c in df.columns]].copy()
    circ_df = circ_df.dropna(axis=1, how="all")
    if len(circ_df.columns) > 1:
        st.line_chart(circ_df.set_index("日期"))
    else:
        st.info("暂无围度数据")
except Exception as e:
    st.warning(f"围度图表加载失败：{e}")

st.markdown("---")

# AI 月报
st.markdown("### 🤖 AI 月度报告")
st.caption("基于近 30 天数据生成")

if st.button("📝 生成月报", width='stretch'):
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

# 历史照片墙 + AI 分析记录
st.markdown("---")
st.markdown("### 📸 历史照片与 AI 分析")
st.caption("你的身材变化轨迹")

if feishu:
    try:
        photo_records = [r for r in records if r.get("fields", {}).get("今日照片")]
        if photo_records:
            for i, r in enumerate(photo_records[:10]):
                fields = r.get("fields", {})
                photo_list = fields.get("今日照片", [])
                if photo_list:
                    date_str = ""
                    if fields.get("日期"):
                        try:
                            date_str = datetime.fromtimestamp(fields["日期"]/1000).strftime("%Y-%m-%d")
                        except (TypeError, ValueError, OSError):
                            date_str = "未知日期"
                    note = fields.get("备注", "")
                    # 提取 AI 评分
                    score_text = ""
                    if "AI 评分" in note:
                        score_text = note.split("AI 评分：")[1].split("\n")[0].strip()
                    label = f"📷 {date_str}"
                    if score_text:
                        label += f" | AI 评分：{score_text}"
                    # 显示详细信息
                    with st.expander(label):
                        if note:
                            st.markdown(note)
                        else:
                            st.caption("无备注信息")
            st.caption(f"共 {len(photo_records)} 条记录，已保存到飞书")
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
        width='stretch',
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