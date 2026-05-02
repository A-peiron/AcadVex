"""
预计算 DBLP 合作网络中每位作者的中心性指标。

读取：data/graph_stats/dblp/edges.json
输出：data/precomputed/centrality.json

输出格式：
{
    "degree":      {"0": 0.01, "1": 0.03, ...},   # 归一化度中心性
    "betweenness": {"0": 0.00, ...},               # 归一化介数中心性（近似值）
    "closeness":   {"0": 0.12, ...}                # 紧密中心性
}

说明：
- degree      反映作者直接合作者数量，数值越高越"活跃"
- betweenness 反映作者在网络中充当"桥梁"的程度
- closeness   反映作者到达其他所有作者的平均距离

运行方式（在 AcadVex 项目根目录）：
    /d/Anaconda_envs/envs/acadvex/python.exe scripts/precompute/compute_centrality.py
"""

import json
import os

import networkx as nx

# ── 路径配置 ─────────────────────────────────────────────────────────────────
# __file__ 是 scripts/precompute/compute_centrality.py
# 向上两级就是项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EDGES_IN = os.path.join(BASE_DIR, "data", "graph_stats", "dblp", "edges.json")
OUTPUT   = os.path.join(BASE_DIR, "data", "precomputed", "centrality.json")

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)


def main():
    # ── 1. 加载边列表，构建图 ───────────────────────────────────────────────
    print(f"[1/4] 从 {EDGES_IN} 加载边列表 ...")
    with open(EDGES_IN, encoding="utf-8") as f:
        edges = json.load(f)   # 格式：[{"source": int, "target": int, "weight": float}, ...]

    G = nx.Graph()
    for e in edges:
        G.add_edge(e["source"], e["target"], weight=e.get("weight", 1.0))

    print(f"    图构建完成：{G.number_of_nodes()} 个节点，{G.number_of_edges()} 条边")

    # ── 2. 度中心性（O(n)，极快）───────────────────────────────────────────
    print("[2/4] 计算度中心性（degree centrality）...")
    deg = nx.degree_centrality(G)

    # ── 3. 介数中心性（使用 k=500 采样近似，避免大图计算过慢）──────────────
    # 精确计算复杂度为 O(n*m)，对 4000 节点 / 3500 边的图约需 30s+
    # k=500 随机采样的误差在 0.01 以内，满足实际使用需求
    n = G.number_of_nodes()
    k_sample = min(500, n)
    print(f"[3/4] 计算介数中心性（betweenness centrality，采样 k={k_sample}）...")
    bet = nx.betweenness_centrality(G, k=k_sample, normalized=True, seed=42)

    # ── 4. 紧密中心性（O(n*(n+m))，适合 4000 节点规模）────────────────────
    print("[4/4] 计算紧密中心性（closeness centrality）...")
    clo = nx.closeness_centrality(G)

    # ── 5. 保存结果，键统一转字符串（JSON 不支持整数键）────────────────────
    result = {
        "degree":      {str(k): round(v, 6) for k, v in deg.items()},
        "betweenness": {str(k): round(v, 6) for k, v in bet.items()},
        "closeness":   {str(k): round(v, 6) for k, v in clo.items()},
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)

    # ── 6. 打印统计摘要 ─────────────────────────────────────────────────────
    print(f"\n[完成] 已保存中心性指标至 {OUTPUT}")
    print(f"  度中心性    范围：[{min(deg.values()):.4f}, {max(deg.values()):.4f}]")
    print(f"  介数中心性  范围：[{min(bet.values()):.4f}, {max(bet.values()):.4f}]")
    print(f"  紧密中心性  范围：[{min(clo.values()):.4f}, {max(clo.values()):.4f}]")

    # 找出各指标 Top-3 作者，便于快速验证结果合理性
    top_deg = sorted(deg.items(), key=lambda x: x[1], reverse=True)[:3]
    top_bet = sorted(bet.items(), key=lambda x: x[1], reverse=True)[:3]
    print(f"\n  度中心性    Top-3：{top_deg}")
    print(f"  介数中心性  Top-3：{top_bet}")


if __name__ == "__main__":
    main()
