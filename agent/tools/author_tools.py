"""
agent/tools/author_tools.py
---------------------------
个人作者分析工具（6 个）：
  1. find_collab_opportunities(author_id)  — 高相似度 - 已有合作边 = 潜力合作者
  2. get_author_influence(author_id)       — degree/betweenness/closeness 指标
  3. find_rising_stars(community_id, top_k)— 高潜力 + 低 degree 的新锐学者
  4. compare_authors(a_id, b_id)           — 相似度 + 关键词交集/差集对比
  5. get_collab_strength(a_id, b_id)       — 多因子合作强度评分
  6. get_author_papers(author_id)          — 返回作者论文列表

依赖：
  - model/inference.py  （embeddings、元数据、打分）
  - data/precomputed/centrality.json  （中心性指标）
  - data/graph_stats/dblp/edges.json  （合作边列表）
"""

import json
import sys
from functools import lru_cache
from pathlib import Path

# 将项目根目录加入路径，使 model.inference 可以被导入
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from model.inference import load_embeddings, predict_collab_score, get_author_info
from agent.utils.logger import logger

# ── 数据目录 ────────────────────────────────────────────────────────────────
_DATA_ROOT = Path(__file__).parent.parent.parent / "data"
_PRECOMPUTED = _DATA_ROOT / "precomputed"
_GRAPH_STATS = _DATA_ROOT / "graph_stats" / "dblp"


# ── 懒加载辅助：避免启动时全量加载 ─────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_centrality() -> dict:
    """加载预计算的中心性指标（只读一次）。"""
    with open(_PRECOMPUTED / "centrality.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_edges() -> set[tuple[int, int]]:
    """加载合作边集合，方便 O(1) 查询是否存在边（只读一次）。"""
    with open(_GRAPH_STATS / "edges.json", encoding="utf-8") as f:
        edges = json.load(f)
    edge_set: set[tuple[int, int]] = set()
    for e in edges:
        u, v = int(e["source"]), int(e["target"])
        edge_set.add((min(u, v), max(u, v)))   # 无向图：统一用较小值做 key
    return edge_set


def _has_edge(a: int, b: int) -> bool:
    """判断两位作者之间是否已有合作关系。"""
    return (min(a, b), max(a, b)) in _load_edges()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. find_collab_opportunities
# ═══════════════════════════════════════════════════════════════════════════════

def find_collab_opportunities(author_id: int, top_k: int = 10) -> str:
    try:
        data = load_embeddings()
        author_meta = data["author_meta"]
        if str(author_id) not in author_meta:
            return f"错误：作者 ID {author_id} 不存在（有效范围 0~{len(author_meta)-1}）"
        me = author_meta[str(author_id)]
        candidates = []
        for cid_str, cinfo in author_meta.items():
            cid = int(cid_str)
            if cid == author_id or _has_edge(author_id, cid):
                continue
            score = predict_collab_score(author_id, cid)
            candidates.append((cid, score, cinfo))
        candidates.sort(key=lambda x: x[1], reverse=True)
        top = candidates[:top_k]
        if not top:
            return f"作者 {me['name']}（ID={author_id}）在库中暂无推荐合作候选人。"
        lines = [f"为 {me['name']}（ID={author_id}，{me['research_area']}）推荐潜力合作者：\n"]
        for rank, (cid, score, cinfo) in enumerate(top, 1):
            common_kw = set(me.get("keywords", [])) & set(cinfo.get("keywords", []))
            kw_hint = f"共同关键词：{', '.join(list(common_kw)[:3])}" if common_kw else "无共同关键词"
            lines.append(f"  {rank}. {cinfo['name']}（ID={cid}，{cinfo['research_area']}）  评分={score:.4f}  {kw_hint}")
        return "\n".join(lines)
    except Exception as e:
        logger.error("tool_failed", tool="find_collab_opportunities", error=str(e))
        return f"工具执行失败：{e}"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. get_author_influence
# ═══════════════════════════════════════════════════════════════════════════════

def get_author_influence(author_id: int) -> str:
    try:
        data = load_embeddings()
        author_meta = data["author_meta"]
        key = str(author_id)
        if key not in author_meta:
            return f"错误：作者 ID {author_id} 不存在"
        info = author_meta[key]
        centrality = _load_centrality()
        deg = centrality["degree"].get(key, 0.0)
        bet = centrality["betweenness"].get(key, 0.0)
        clo = centrality["closeness"].get(key, 0.0)
        activity_level = "高度活跃" if deg > 0.01 else "中度活跃" if deg > 0.003 else "较少合作"
        bridge_role = "关键桥梁" if bet > 0.02 else "一定桥梁作用" if bet > 0.005 else "局部连接"
        return (
            f"作者影响力报告：{info['name']}（ID={author_id}）\n"
            f"  研究方向：{info['research_area']}\n"
            f"  论文数量：{info['paper_count']} 篇\n"
            f"\n  【网络中心性指标】\n"
            f"  度中心性（Degree）：{deg:.4f}  → {activity_level}\n"
            f"  介数中心性（Betweenness）：{bet:.4f}  → {bridge_role}\n"
            f"  紧密中心性（Closeness）：{clo:.4f}\n"
            f"\n  关键词：{', '.join(info.get('keywords', []))}"
        )
    except Exception as e:
        logger.error("tool_failed", tool="get_author_influence", error=str(e))
        return f"工具执行失败：{e}"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. find_rising_stars
# ═══════════════════════════════════════════════════════════════════════════════

def find_rising_stars(community_id: int, top_k: int = 5) -> str:
    try:
        import torch

        data = load_embeddings()
        author_meta = data["author_meta"]
        community_meta = data["community_meta"]
        author_emb = data["author_emb"]
        centrality = _load_centrality()

        comm_key = str(community_id)
        if comm_key not in community_meta:
            return f"错误：社群 ID {community_id} 不存在（有效范围 0~{len(community_meta)-1}）"

        comm_info = community_meta[comm_key]
        comm_name = comm_info["name"]

        leader_ids = comm_info.get("top_members", [])[:5]
        if not leader_ids:
            return f"社群 {comm_name}（ID={community_id}）暂无核心成员数据。"

        leader_embs = author_emb[leader_ids]

        comm_authors = [
            (int(k), v) for k, v in author_meta.items()
            if v.get("community_id") == community_id and int(k) not in leader_ids
        ]

        scored = []
        for aid, ainfo in comm_authors:
            emb = author_emb[aid]
            sim = torch.cosine_similarity(
                emb.unsqueeze(0),
                leader_embs,
            ).mean().item()
            deg = centrality["degree"].get(str(aid), 0.0)
            rising_score = sim - deg * 10
            scored.append((aid, rising_score, sim, deg, ainfo))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:top_k]

        if not top:
            return f"社群 {comm_name}（ID={community_id}）中暂无符合条件的新锐学者。"

        lines = [f"社群【{comm_name}】中的新锐学者（高潜力 + 低合作度）：\n"]
        for rank, (aid, rising_score, sim, deg, ainfo) in enumerate(top, 1):
            lines.append(
                f"  {rank}. {ainfo['name']}（ID={aid}）"
                f"  潜力相似度={sim:.3f}  degree={deg:.4f}"
                f"  关键词：{', '.join(ainfo.get('keywords', [])[:3])}"
            )

        return "\n".join(lines)
    except Exception as e:
        logger.error("tool_failed", tool="find_rising_stars", error=str(e))
        return f"工具执行失败：{e}"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. compare_authors
# ═══════════════════════════════════════════════════════════════════════════════

def compare_authors(author_a_id: int, author_b_id: int) -> str:
    try:
        data = load_embeddings()
        author_meta = data["author_meta"]

        for aid, label in [(author_a_id, "A"), (author_b_id, "B")]:
            if str(aid) not in author_meta:
                return f"错误：作者{label} ID={aid} 不存在"

        a = author_meta[str(author_a_id)]
        b = author_meta[str(author_b_id)]
        centrality = _load_centrality()
        score = predict_collab_score(author_a_id, author_b_id)

        kw_a = set(a.get("keywords", []))
        kw_b = set(b.get("keywords", []))
        common = kw_a & kw_b
        only_a = kw_a - kw_b
        only_b = kw_b - kw_a

        deg_a = centrality["degree"].get(str(author_a_id), 0.0)
        deg_b = centrality["degree"].get(str(author_b_id), 0.0)
        bet_a = centrality["betweenness"].get(str(author_a_id), 0.0)
        bet_b = centrality["betweenness"].get(str(author_b_id), 0.0)

        existing = _has_edge(author_a_id, author_b_id)
        collab_status = "已有合作关系" if existing else "尚无合作关系"

        return (
            f"作者对比报告\n"
            f"{'='*40}\n"
            f"  作者A：{a['name']}（ID={author_a_id}，{a['research_area']}）\n"
            f"  作者B：{b['name']}（ID={author_b_id}，{b['research_area']}）\n"
            f"\n  合作潜力分数：{score:.4f}  |  {collab_status}\n"
            f"\n  【关键词分析】\n"
            f"  共同研究方向（{len(common)} 个）：{', '.join(list(common)[:5]) or '无'}\n"
            f"  {a['name']} 独有方向：{', '.join(list(only_a)[:5]) or '无'}\n"
            f"  {b['name']} 独有方向：{', '.join(list(only_b)[:5]) or '无'}\n"
            f"\n  【网络影响力对比】\n"
            f"  度中心性：{a['name']}={deg_a:.4f}  vs  {b['name']}={deg_b:.4f}\n"
            f"  介数中心性：{a['name']}={bet_a:.4f}  vs  {b['name']}={bet_b:.4f}"
        )
    except Exception as e:
        logger.error("tool_failed", tool="compare_authors", error=str(e))
        return f"工具执行失败：{e}"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. get_collab_strength
# ═══════════════════════════════════════════════════════════════════════════════

def get_collab_strength(author_a_id: int, author_b_id: int) -> str:
    try:
        import math
        data = load_embeddings()
        author_meta = data["author_meta"]

        for aid, label in [(author_a_id, "A"), (author_b_id, "B")]:
            if str(aid) not in author_meta:
                return f"错误：作者{label} ID={aid} 不存在"

        a = author_meta[str(author_a_id)]
        b = author_meta[str(author_b_id)]

        raw_score = predict_collab_score(author_a_id, author_b_id)
        sim_score = 1 / (1 + math.exp(-raw_score))

        kw_a = set(a.get("keywords", []))
        kw_b = set(b.get("keywords", []))
        union = kw_a | kw_b
        jaccard = len(kw_a & kw_b) / len(union) if union else 0.0

        same_community = a.get("community_id") == b.get("community_id")
        comm_bonus = 0.2 if same_community else 0.0
        strength = sim_score * 0.5 + jaccard * 0.3 + comm_bonus * 0.2 / 0.2

        if strength >= 0.6:
            level = "强合作潜力"
        elif strength >= 0.4:
            level = "中等合作潜力"
        else:
            level = "合作潜力较低"

        existing = _has_edge(author_a_id, author_b_id)

        return (
            f"合作强度分析：{a['name']} × {b['name']}\n"
            f"  综合强度分数：{strength:.3f}  →  {level}\n"
            f"  当前合作状态：{'已合作' if existing else '未合作'}\n"
            f"\n  【评分分解】\n"
            f"  向量相似度（权重50%）：{sim_score:.3f}\n"
            f"  关键词 Jaccard（权重30%）：{jaccard:.3f}（共 {len(kw_a & kw_b)} 个共同关键词）\n"
            f"  社群关系（权重20%）：{'同社群(+0.20)' if same_community else '跨社群(+0.00)'}"
        )
    except Exception as e:
        logger.error("tool_failed", tool="get_collab_strength", error=str(e))
        return f"工具执行失败：{e}"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. get_author_papers
# ═══════════════════════════════════════════════════════════════════════════════

def get_author_papers(author_id: int) -> str:
    try:
        data = load_embeddings()
        author_meta = data["author_meta"]
        paper_meta = data["paper_meta"]

        key = str(author_id)
        if key not in author_meta:
            return f"错误：作者 ID {author_id} 不存在"

        info = author_meta[key]
        paper_count = info.get("paper_count", 0)
        all_papers = list(paper_meta.values())[:paper_count] if paper_count else []

        if not all_papers:
            return (
                f"作者 {info['name']}（ID={author_id}）\n"
                f"  研究方向：{info['research_area']}\n"
                f"  发表论文：{paper_count} 篇\n"
                f"  （暂无论文详情，待数据集完整 author-paper 映射后支持）"
            )

        lines = [f"作者 {info['name']}（ID={author_id}）共发表 {paper_count} 篇论文：\n"]
        for i, p in enumerate(all_papers[:10], 1):
            lines.append(f"  {i}. [{p.get('venue', '未知')}] {p.get('title', '未知标题')}")
        if paper_count > 10:
            lines.append(f"  ... 共 {paper_count} 篇（仅显示前 10 篇）")
        return "\n".join(lines)
    except Exception as e:
        logger.error("tool_failed", tool="get_author_papers", error=str(e))
        return f"工具执行失败：{e}"
