"""训练计划生成器

借鉴 quantum-fit 的设计模式：
- 表单输入（2 列布局）
- 用 --- 分段让 AI 输出结构化内容
- 缓存结果
"""
from typing import Dict, Optional, List
import streamlit as st

from core.ai_client import get_ai_client
from core.prompts import PLAN_GENERATION_PROMPT
from core.feishu_client import get_feishu_client
from core.config import FEISHU_TABLES


class PlanGenerator:
    """训练计划生成器"""

    def __init__(self):
        self.ai = get_ai_client()
        self.feishu = get_feishu_client()

    def generate(self, profile: Dict) -> str:
        """生成周训练计划

        Args:
            profile: {
                "height": 175, "weight": 70, "age": 28, "gender": "男",
                "goal": "增肌", "experience": "新手",
                "hours_per_week": 5, "resources": ["健身房"],
                "notes": "无特殊"
            }
        """
        if not self.ai:
            return "❌ AI 客户端未配置，请检查 DEEPSEEK_API_KEY"

        prompt = PLAN_GENERATION_PROMPT.format(
            height=profile.get("height", "未提供"),
            weight=profile.get("weight", "未提供"),
            age=profile.get("age", "未提供"),
            gender=profile.get("gender", "未提供"),
            goal=profile.get("goal", "未提供"),
            experience=profile.get("experience", "未提供"),
            hours_per_week=profile.get("hours_per_week", "未提供"),
            resources=", ".join(profile.get("resources", [])) or "无",
            notes=profile.get("notes", "无"),
        )

        response = self.ai.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=3500,
        )
        return response

    def save_to_feishu(self, profile: Dict, plan_text: str) -> Optional[str]:
        """保存计划到飞书"""
        if not self.feishu or not FEISHU_TABLES.get("workout_logs"):
            return None
        try:
            from datetime import datetime
            record_id = self.feishu.add_record(
                FEISHU_TABLES["workout_logs"],
                {
                    "日期": int(datetime.now().timestamp() * 1000),  # 飞书 Date 字段是毫秒时间戳
                    "训练类型": "AI 计划",
                    "动作记录": f"档案：{profile}\n\n{plan_text[:1000]}",
                    "强度感受": "适中",
                },
            )
            return record_id
        except Exception as e:
            print(f"保存失败：{e}")
            return None


def render_plan_form() -> Optional[Dict]:
    """渲染训练计划输入表单（借鉴 quantum-fit 的 UI）"""
    with st.form("plan_form"):
        st.markdown("### 📋 填写你的档案")
        col1, col2 = st.columns(2)

        with col1:
            height = st.number_input("身高 (cm)", min_value=100, max_value=250, value=170)
            age = st.number_input("年龄", min_value=10, max_value=100, value=25)

        with col2:
            weight = st.number_input("体重 (kg)", min_value=30, max_value=200, value=65)
            gender = st.selectbox("性别", ["男", "女"])

        col3, col4 = st.columns(2)
        with col3:
            goal = st.selectbox("健身目标", ["增肌", "减脂", "塑形", "保持"])
            hours = st.slider("每周可用时间 (小时)", 1, 14, 5)

        with col4:
            experience = st.selectbox("经验水平", ["新手", "进阶", "专业"])
            resources = st.multiselect(
                "健身资源",
                ["健身房", "居家", "无器械", "哑铃", "杠铃"],
                default=["健身房"],
            )

        notes = st.text_area(
            "特殊要求（伤病、过敏、饮食偏好等）",
            placeholder="例如：左膝有伤、不能深蹲；海鲜过敏...",
        )

        submitted = st.form_submit_button("🎯 生成我的周计划", use_container_width=True)

        if submitted:
            # 借鉴 quantum-fit 的 BMI 显示
            bmi = weight / ((height / 100) ** 2)
            st.metric("📊 你的 BMI", f"{bmi:.1f}", help="正常范围 18.5-24")
            return {
                "height": height, "weight": weight, "age": age,
                "gender": gender, "goal": goal, "experience": experience,
                "hours_per_week": hours, "resources": resources, "notes": notes,
            }
    return None


def parse_sections(text: str) -> List[str]:
    """按 --- 分段（借鉴 quantum-fit 的 Tabs 展示）"""
    if "---" not in text:
        return [text]
    return [s.strip() for s in text.split("---") if s.strip()]


def render_plan_result(plan_text: str):
    """用 Tabs 展示计划（借鉴 quantum-fit）"""
    sections = parse_sections(plan_text)
    titles = ["📝 总体概览", "📆 周训练", "🥗 营养指南", "💊 补剂建议", "🛡️ 生活安全"]

    if len(sections) >= 2:
        tabs = st.tabs(titles[:len(sections)])
        for tab, title, section in zip(tabs, titles, sections):
            with tab:
                st.markdown(section)
    else:
        st.markdown(plan_text)