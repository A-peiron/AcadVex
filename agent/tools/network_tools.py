"""
agent/tools/network_tools.py
-----------------------------
全局网络分析工具（4 个）：
  1. find_rising_stars_global(top_k)     — 全网新锐学者（跨社群）
  2. find_collab_path(a_id, b_id)        — BFS 最短合作路径
  3. suggest_team(query, size)           — 多样性算法组建研究团队
  4. get_network_overview()              — 网络整体统计（扩展版）

依赖：
  - model/inference.py
  - data/precomputed/centrality.json
  - data/graph_stats/dblp/edges.json
"""

import json
import sys
from collections import deque
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from model.inference import load_embeddings, predict_collab_score
from agent.utils.logger import logger

_DATA_ROOT   = Path(__file__).parent.parent.parent / "data"
_PRECOMPUTED = _DATA_ROOT / "precomputed"
_GRAPH_STATS = _DATA_ROOT / "graph_stats" / "dblp"


# ── 懒加载 ──────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_centrality() -> dict:
    with open(_PRECOMPUTED / "centrality.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_adjacency() -> dict[int, list[int]]:
    """
    构建邻接表，用于 BFS 路径搜索。
    格式：{node_id: [neighbor_id, ...]}
    """
    with open(_GRAPH_STATS / "edges.json", encoding="utf-8") as f:
        edges = json.load(f)

    adj: dict[int, list[int]] = {}
    for e in edges:
        u, v = int(e["source"]), int(e["target"])
        adj.setdefault(u, []).append(v)
        adj.setdefault(v, []).append(u)
    return adj


# ═══════════════════════════════════════════════════════════════════════════════
# 1. find_collab_path
# ═══════════════════════════════════════════════════════════════════════════════

def find_collab_path(author_a_id: int, author_b_id: int) -> str:
    try:
        data = load_embeddings()
        author_meta = data["author_meta"]

        for aid, label in [(author_a_id, "A"), (author_b_id, "B")]:
            if str(aid) not in author_meta:
                return f"错误：作者{label} ID={aid} 不存在"

        if author_a_id == author_b_id:
            return "错误：起点和终点是同一位作者。"

        adj = _load_adjacency()
        queue: deque = deque([[author_a_id]])
        visited: set[int] = {author_a_id}
        max_depth = 6

        while queue:
            path = queue.popleft()
            current = path[-1]
            if len(path) > max_depth + 1:
                break
            for neighbor in adj.get(current, []):
                if neighbor in visited:
                    continue
                new_path = path + [neighbor]
                if neighbor == author_b_id:
                    names = []
                    for pid in new_path:
                        pinfo = author_meta.get(str(pid), {})
                        names.append(f"{pinfo.get('name', f'ID={pid}')}(ID={pid})")
                    hops = len(new_path) - 1
                    lines = [f"合作路径（{hops} 跳）：\n", "  " + "\n  → ".join(names)]
                    lines.append("\n  两位作者直接合作过！" if hops == 1 else f"\n  通过 {hops-1} 位中间人相连")
                    return "\n".join(lines)
                visited.add(neighbor)
                queue.append(new_path)

        a_name = author_meta[str(author_a_id)]["name"]
        b_name = author_meta[str(author_b_id)]["name"]
        return (
            f"{a_name}（ID={author_a_id}）和 {b_name}（ID={author_b_id}）\n"
            f"  在 {max_depth} 跳内未找到合作路径（两人可能处于网络的不同连通分量）。"
        )
    except Exception as e:
        logger.error("tool_failed", tool="find_collab_path", error=str(e))
        return f"工具执行失败：{e}"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. suggest_team
# ═══════════════════════════════════════════════════════════════════════════════

def suggest_team(query: str, size: int = 3) -> str:
    try:
        import torch
        data = load_embeddings()
        author_meta = data["author_meta"]
        author_emb = data["author_emb"]

        query_lower = query.lower().replace("，", " ").replace(",", " ")
        query_tokens = set(query_lower.split())
        if not query_tokens:
            return "错误：请提供研究方向关键词（如 '图神经网络 推荐系统'）"

        def _match_count(kw_set: set[str]) -> int:
            score = 0
            for kw in kw_set:
                kw_parts = kw.split()
                if query_tokens & set(kw_parts):
                    score += 1
                elif kw in query_lower:
                    score += 1
            return score

        # 第一阶段：关键词过滤候选池
        candidates = []
        for aid_str, ainfo in author_meta.items():
            kw_set = set(kw.lower() for kw in ainfo.get("keywords", []))
            match_cnt = _match_count(kw_set)
            if match_cnt > 0:
                candidates.append({"id": int(aid_str), "info": ainfo, "keywords": kw_set, "match_count": match_cnt})

        if not candidates:
            return (
                f"未找到与查询「{query}」相关的作者。\n"
                f"请尝试更通用的英文关键词，如 'machine learning'、'data mining'、'neural network' 等。"
            )

        # 第二阶段：FPGCL 嵌入 + 关键词覆盖综合评分
        # 用候选池 top-20 的嵌入均值作为查询代理向量
        top20_ids = [c["id"] for c in sorted(candidates, key=lambda x: x["match_count"], reverse=True)[:20]]
        query_vec = author_emb[top20_ids].mean(dim=0)  # [d]

        for c in candidates:
            emb = author_emb[c["id"]]
            sim = torch.cosine_similarity(emb.unsqueeze(0), query_vec.unsqueeze(0)).item()
            c["fpgcl_sim"] = sim

        team: list[dict] = []
        covered_keywords: set[str] = set()

        for _ in range(size):
            best_candidate = None
            best_score = -1.0
            total_kw = max(len(c["keywords"]) for c in candidates) or 1
            for c in candidates:
                if any(m["id"] == c["id"] for m in team):
                    continue
                new_kw_ratio = len(c["keywords"] - covered_keywords) / total_kw
                score = c["fpgcl_sim"] * 0.6 + new_kw_ratio * 0.4
                if score > best_score:
                    best_score = score
                    best_candidate = c
            if best_candidate is None:
                break
            team.append(best_candidate)
            covered_keywords |= best_candidate["keywords"]

        if not team:
            return f"无法为「{query}」组建团队，候选作者不足。"

        lines = [f"为「{query}」组建的研究团队（{len(team)} 人）：\n"]
        for rank, member in enumerate(team, 1):
            info = member["info"]
            lines.append(
                f"  {rank}. {info['name']}（ID={member['id']}）\n"
                f"     方向：{info['research_area']}  |  论文：{info['paper_count']} 篇  |  FPGCL相似度：{member['fpgcl_sim']:.3f}\n"
                f"     关键词：{', '.join(list(member['keywords'])[:5])}"
            )
        lines.append(f"\n  团队共覆盖 {len(covered_keywords)} 个研究关键词")
        return "\n".join(lines)
    except Exception as e:
        logger.error("tool_failed", tool="suggest_team", error=str(e))
        return f"工具执行失败：{e}"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. get_network_overview（扩展版 get_network_stats）
# ═══════════════════════════════════════════════════════════════════════════════

def get_network_overview() -> str:
    try:
        data = load_embeddings()
        author_meta   = data["author_meta"]
        community_meta = data["community_meta"]
        centrality    = _load_centrality()
        adj = _load_adjacency()

        n_edges = sum(len(v) for v in adj.values()) // 2
        degrees = [len(v) for v in adj.values()]
        avg_deg = sum(degrees) / len(degrees) if degrees else 0
        max_deg = max(degrees) if degrees else 0

        deg_sorted = sorted(centrality["degree"].items(), key=lambda x: x[1], reverse=True)[:5]

        lines = [
            "学术合作网络全局概览",
            "=" * 40,
            f"  网络规模：{len(author_meta)} 位作者  |  {n_edges} 条合作边",
            f"  平均合作度：{avg_deg:.1f}  |  最大合作度：{max_deg}",
            f"  研究社群数：{len(community_meta)} 个",
            "\n  【各社群规模】"
        ]
        for cid, cinfo in community_meta.items():
            lines.append(f"  [{cinfo['name']}]  {cinfo['size']} 位作者")

        lines.append("\n  【全网影响力 Top-5】")
        for rank, (aid_str, deg_val) in enumerate(deg_sorted, 1):
            ainfo = author_meta.get(aid_str, {})
            name = ainfo.get("name", f"ID={aid_str}")
            lines.append(f"  {rank}. {name}（ID={aid_str}）  degree={deg_val:.4f}")

        return "\n".join(lines)
    except Exception as e:
        logger.error("tool_failed", tool="get_network_overview", error=str(e))
        return f"工具执行失败：{e}"
