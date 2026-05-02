# agent/tools/rag_tools.py
"""
RAG 相关工具函数，供各 Skill 调用
--------------------------------------------------
- search_knowledge：在 AcadVex 知识库中检索相关内容，返回文本结果
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rag.retriever import retrieve
from agent.utils.logger import logger


def search_knowledge(query: str) -> str:
    """在 AcadVex 知识库中检索与 query 相关的文档片段"""
    try:
        results = retrieve(query, top_k=3)
        if not results:
            return "知识库中未找到相关内容。"
        lines = [f"检索到 {len(results)} 条相关知识：\n"]
        for i, doc in enumerate(results, start=1):
            lines.append(f"[{i}] {doc['text']}")
        return "\n\n".join(lines)
    except Exception as e:
        logger.error("tool_failed", tool="search_knowledge", error=str(e))
        return f"工具执行失败：{e}"
