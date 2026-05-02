"""
agent/tools/community_tools.py
-------------------------------
社群分析工具（3 个）：
  1. get_community_leaders(community_id)          — 社群中心性排名前 K 作者
  2. get_community_topics(community_id)           — TF-IDF Top-20 关键词
  3. get_inter_community_strength(comm_a, comm_b) — 跨社群合作边统计

依赖：
  - model/inference.py  （元数据）
  - data/precomputed/centrality.json
  - data/precomputed/community_topics.json
  - data/graph_stats/dblp/edges.json
"""

import json
import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from model.inference import load_embeddings
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
def _load_community_topics() -> dict:
    with open(_PRECOMPUTED / "community_topics.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_edges_with_meta() -> list[dict]:
    """加载边列表，含 weight 字段。"""
    with open(_GRAPH_STATS / "edges.json", encoding="utf-8") as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. get_community_leaders
# ═══════════════════════════════════════════════════════════════════════════════

def get_community_leaders(community_id: int, top_k: int = 5) -> str:
    try:
        data = load_embeddings()
        author_meta   = data["author_meta"]
        community_meta = data["community_meta"]

        comm_key = str(community_id)
        if comm_key not in community_meta:
            return f"错误：社群 ID {community_id} 不存在（有效范围 0~{len(community_meta)-1}）"

        comm_info = community_meta[comm_key]
        comm_name = comm_info["name"]
        centrality = _load_centrality()

        comm_authors = [
            (k, v) for k, v in author_meta.items()
            if v.get("community_id") == community_id
        ]
        if not comm_authors:
            return f"社群 {comm_name}（ID={community_id}）中暂无作者数据。"

        scored = []
        for aid_str, ainfo in comm_authors:
            deg = centrality["degree"].get(aid_str, 0.0)
            bet = centrality["betweenness"].get(aid_str, 0.0)
            clo = centrality["closeness"].get(aid_str, 0.0)
            combined = deg * 0.5 + bet * 0.3 + clo * 0.2
            scored.append((int(aid_str), combined, deg, bet, clo, ainfo))

        scored.sort(key=lambda x: x[1], reverse=True)
        lines = [f"社群【{comm_name}】（共 {comm_info['size']} 位作者）影响力排名：\n"]
        for rank, (aid, combined, deg, bet, clo, ainfo) in enumerate(scored[:top_k], 1):
            lines.append(
                f"  {rank}. {ainfo['name']}（ID={aid}）"
                f"  综合={combined:.4f}  degree={deg:.4f}  betweenness={bet:.4f}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error("tool_failed", tool="get_community_leaders", error=str(e))
        return f"工具执行失败：{e}"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. get_community_topics
# ═══════════════════════════════════════════════════════════════════════════════

def get_community_topics(community_id: int, top_k: int = 10) -> str:
    try:
        topics = _load_community_topics()
        comm_key = str(community_id)
        if comm_key not in topics:
            return f"错误：社群 ID {community_id} 的主题数据不存在"

        comm_data = topics[comm_key]
        comm_name = comm_data["name"]
        keywords = comm_data["top_keywords"][:top_k]

        lines = [f"社群【{comm_name}】（ID={community_id}）核心研究主题：\n"]
        for i, kw in enumerate(keywords, 1):
            bar_len = int(kw["score"] / keywords[0]["score"] * 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            lines.append(f"  {i:2d}. {bar}  {kw['word']}（TF-IDF={kw['score']:.4f}）")
        return "\n".join(lines)
    except Exception as e:
        logger.error("tool_failed", tool="get_community_topics", error=str(e))
        return f"工具执行失败：{e}"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. get_inter_community_strength
# ═══════════════════════════════════════════════════════════════════════════════

def get_inter_community_strength(comm_a_id: int, comm_b_id: int) -> str:
    try:
        data = load_embeddings()
        author_meta   = data["author_meta"]
        community_meta = data["community_meta"]

        for cid, label in [(comm_a_id, "A"), (comm_b_id, "B")]:
            if str(cid) not in community_meta:
                return f"错误：社群{label} ID={cid} 不存在"

        name_a = community_meta[str(comm_a_id)]["name"]
        name_b = community_meta[str(comm_b_id)]["name"]

        author_comm: dict[int, int] = {
            int(k): v["community_id"]
            for k, v in author_meta.items()
            if "community_id" in v
        }

        edges = _load_edges_with_meta()
        cross_edges = []
        for e in edges:
            src, tgt = int(e["source"]), int(e["target"])
            ca = author_comm.get(src)
            cb = author_comm.get(tgt)
            if (ca == comm_a_id and cb == comm_b_id) or \
               (ca == comm_b_id and cb == comm_a_id):
                cross_edges.append({"src": src, "tgt": tgt, "weight": e.get("weight", 1.0)})

        if not cross_edges:
            return (
                f"社群【{name_a}】与社群【{name_b}】之间\n"
                f"  暂无直接合作关系（合作边数量：0）"
            )

        total_edges = len(cross_edges)
        avg_weight = sum(e["weight"] for e in cross_edges) / total_edges
        cross_edges.sort(key=lambda x: x["weight"], reverse=True)

        lines = [
            f"跨社群合作分析：【{name_a}】← → 【{name_b}】\n",
            f"  合作边总数：{total_edges} 条",
            f"  平均合作权重：{avg_weight:.3f}",
            f"\n  最活跃合作对（Top-3）："
        ]
        for e in cross_edges[:3]:
            a_name = author_meta.get(str(e["src"]), {}).get("name", f"ID={e['src']}")
            b_name = author_meta.get(str(e["tgt"]), {}).get("name", f"ID={e['tgt']}")
            lines.append(f"    {a_name}  ←→  {b_name}  （权重={e['weight']:.2f}）")
        return "\n".join(lines)
    except Exception as e:
        logger.error("tool_failed", tool="get_inter_community_strength", error=str(e))
        return f"工具执行失败：{e}"
