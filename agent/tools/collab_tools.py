"""
agent/tools/collab_tools.py
---------------------------
合作潜力预测相关工具函数。
每个函数对应一个可以被 LLM 调用的"工具"。
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from model.inference import predict_collab_score, get_author_info
from agent.utils.logger import logger


def predict_collaboration(author_a_id: int, author_b_id: int) -> str:
    """预测两位作者的合作潜力。"""
    try:
        score = predict_collab_score(author_a_id, author_b_id)
        a = get_author_info(author_a_id)
        b = get_author_info(author_b_id)
        return (
            f"合作潜力分数：{score:.4f}\n"
            f"作者A：{a['name']}（{a['research_area']}，发表 {a['paper_count']} 篇论文）\n"
            f"作者B：{b['name']}（{b['research_area']}，发表 {b['paper_count']} 篇论文）\n"
            f"关键词A：{', '.join(a['keywords'])}\n"
            f"关键词B：{', '.join(b['keywords'])}"
        )
    except Exception as e:
        logger.error("tool_failed", tool="predict_collaboration", error=str(e))
        return f"工具执行失败：{e}"


def search_author(query: str) -> str:
    """按姓名关键词搜索作者（返回前5个匹配）。"""
    try:
        from model.inference import load_embeddings
        data = load_embeddings()
        query_lower = query.lower()
        matches = [
            info for info in data['author_meta'].values()
            if query_lower in info['name'].lower()
        ][:5]
        if not matches:
            return f"未找到包含 '{query}' 的作者。"
        lines = [f"找到 {len(matches)} 位作者："]
        for m in matches:
            lines.append(f"  ID={m['id']} | {m['name']} | {m['research_area']} | {m['paper_count']} 篇论文")
        return "\n".join(lines)
    except Exception as e:
        logger.error("tool_failed", tool="search_author", error=str(e))
        return f"工具执行失败：{e}"


def get_network_stats() -> str:
    """获取整体学术合作网络的统计信息。"""
    try:
        from model.inference import load_embeddings
        data = load_embeddings()
        n_authors = len(data['author_meta'])
        n_papers  = len(data['paper_meta'])
        comms     = data['community_meta']
        lines = [
            f"网络规模：{n_authors} 位作者，{n_papers} 篇论文，{len(comms)} 个研究社群",
            "各社群概况："
        ]
        for c in comms.values():
            lines.append(f"  [{c['name']}] {c['size']} 位作者")
        return "\n".join(lines)
    except Exception as e:
        logger.error("tool_failed", tool="get_network_stats", error=str(e))
        return f"工具执行失败：{e}"


def analyze_community(community_id: int) -> str:
    """分析指定研究社群的详细信息。"""
    try:
        from model.inference import load_embeddings
        data = load_embeddings()
        comms = data['community_meta']
        key = str(community_id)
        if key not in comms:
            return f"错误：社群 ID {community_id} 不存在，有效范围 0~{len(comms)-1}"
        c = comms[key]
        top_names = []
        for aid in c['top_members'][:5]:
            info = data['author_meta'].get(str(aid), {})
            name = info.get('name', f'ID={aid}')
            top_names.append(f"{name}(ID={aid})")
        return (
            f"社群名称：{c['name']}\n"
            f"社群规模：{c['size']} 位作者\n"
            f"核心成员（影响力前5）：{', '.join(top_names)}"
        )
    except Exception as e:
        logger.error("tool_failed", tool="analyze_community", error=str(e))
        return f"工具执行失败：{e}"
