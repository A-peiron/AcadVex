# agent/tools/rag_tools.py
"""
RAG 相关工具函数，供各 Skill 调用
--------------------------------------------------
- search_knowledge：在 AcadVex 知识库中检索相关内容，返回文本结果
"""

from rag.retriever import retrieve


def search_knowledge(query: str) -> str:
    """在 AcadVex 知识库中检索与 query 相关的文档片段"""
    results = retrieve(query, top_k=3)
    if not results:
        return "知识库中未找到相关内容。"
    lines = [f"检索到 {len(results)} 条相关知识：\n"]
    for i, doc in enumerate(results, start=1):
        lines.append(f"[{i}] {doc['text']}")
    return "\n\n".join(lines)
