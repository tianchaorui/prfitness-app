"""健身知识 RAG（轻量级实现）

设计选择：
- 不引入外部 embedding API（避免额外成本）
- 用 DeepSeek 自己作为「重排序 + 答案生成」
- 简单地把知识文档作为 context 拼到 prompt 里（适合小知识库）

适合场景：
- 知识库 < 50 篇文档
- 不需要精确的语义检索
- 优先考虑简单和成本
"""
import os
import glob
from typing import List, Optional
import streamlit as st

from core.ai_client import get_ai_client
from core.prompts import COACH_SYSTEM_PROMPT


class FitnessRAG:
    """健身知识问答（轻量级）"""

    def __init__(self, knowledge_dir: str = "data/knowledge"):
        self.ai = get_ai_client()
        self.knowledge_dir = knowledge_dir
        self._documents: Optional[List[Dict]] = None

    def _load_documents(self) -> List[Dict]:
        """加载所有知识文档"""
        if self._documents is not None:
            return self._documents

        docs = []
        if not os.path.exists(self.knowledge_dir):
            return docs

        for filepath in glob.glob(os.path.join(self.knowledge_dir, "*.md")):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                docs.append({
                    "name": os.path.basename(filepath),
                    "content": content,
                })
            except Exception as e:
                print(f"加载 {filepath} 失败：{e}")

        self._documents = docs
        return docs

    def _select_relevant_context(self, query: str, max_docs: int = 2, max_chars: int = 3000) -> str:
        """选择最相关的文档作为 context

        简单实现：根据关键词匹配 + 文件名相关性
        （生产环境应该用向量检索）
        """
        docs = self._load_documents()
        if not docs:
            return ""

        # 关键词匹配打分
        query_keywords = set(query.lower().split())
        scored = []
        for doc in docs:
            score = 0
            # 文件名匹配加分
            for kw in query_keywords:
                if kw in doc["name"].lower():
                    score += 5
            # 内容匹配加分
            content_lower = doc["content"].lower()
            for kw in query_keywords:
                if len(kw) >= 2 and kw in content_lower:
                    score += 1
            scored.append((score, doc))

        # 按分数排序，取 top max_docs
        scored.sort(key=lambda x: -x[0])
        top_docs = [doc for score, doc in scored[:max_docs] if score > 0]

        # 拼接
        context = "\n\n---\n\n".join(
            f"【{doc['name']}】\n{doc['content'][:max_chars]}"
            for doc in top_docs
        )
        return context

    def ask(self, query: str, user_profile: Optional[dict] = None) -> str:
        """RAG 问答"""
        if not self.ai:
            return "❌ AI 客户端未配置"

        knowledge_context = self._select_relevant_context(query)
        profile_str = str(user_profile) if user_profile else "未填写"

        system_prompt = COACH_SYSTEM_PROMPT.format(
            user_profile=profile_str,
            knowledge_context=knowledge_context or "（无相关知识库内容）",
        )

        return self.ai.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            temperature=0.7,
            max_tokens=2000,
        )

    def save_conversation(self, role: str, content: str, session_id: str = "default") -> Optional[str]:
        """保存对话到飞书"""
        from core.feishu_client import get_feishu_client
        from core.config import FEISHU_TABLES
        from datetime import datetime

        feishu = get_feishu_client()
        if not feishu or not FEISHU_TABLES.get("ai_conversations"):
            return None

        try:
            record_id = feishu.add_record(
                FEISHU_TABLES["ai_conversations"],
                {
                    "时间": int(datetime.now().timestamp() * 1000),
                    "角色": role,
                    "会话ID": session_id,
                    "内容": content,
                },
            )
            return record_id
        except Exception as e:
            print(f"保存对话失败：{e}")
            return None