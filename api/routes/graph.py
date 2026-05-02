from fastapi import APIRouter, HTTPException, Query
import json
import os
from typing import List, Dict, Any

router = APIRouter()

# 全局缓存
_edges = None
_author_meta = None
_dataset = os.getenv("DATASET", "dblp")


def _load_graph_data():
    """加载图数据（启动时加载一次）"""
    global _edges, _author_meta

    if _edges is None:
        edges_path = f"data/graph_stats/{_dataset}/edges.json"
        with open(edges_path, "r", encoding="utf-8") as f:
            _edges = json.load(f)

    if _author_meta is None:
        meta_path = f"data/graph_stats/{_dataset}/author_meta.json"
        with open(meta_path, "r", encoding="utf-8") as f:
            _author_meta = json.load(f)

    return _edges, _author_meta


# 社群配色方案（4个社群）
COMMUNITY_COLORS = {
    0: "#5470c6",  # 蓝色
    1: "#91cc75",  # 绿色
    2: "#fac858",  # 黄色
    3: "#ee6666",  # 红色
}


@router.get("/graph")
def get_collaboration_graph(
    author_id: int = Query(..., description="中心作者ID"),
    max_nodes: int = Query(50, description="最大节点数（包含中心作者）")
):
    """
    获取作者合作网络图数据（ECharts 格式）

    Args:
        author_id: 中心作者ID
        max_nodes: 最大节点数，默认50（避免图过于密集）

    Returns:
        {
            "nodes": [{"id": 42, "name": "...", "symbolSize": 30, "itemStyle": {...}, ...}],
            "links": [{"source": 42, "target": 100, "value": 3.0}, ...]
        }
    """
    edges, author_meta = _load_graph_data()

    # 检查中心作者是否存在
    author_key = str(author_id)
    if author_key not in author_meta:
        raise HTTPException(status_code=404, detail=f"Author {author_id} not found")

    # 1. 找出中心作者的所有邻居
    neighbors = {}  # {neighbor_id: total_weight}
    center_edges = []  # 保存中心作者相关的边

    for edge in edges:
        source, target, weight = edge["source"], edge["target"], edge["weight"]

        if source == author_id:
            neighbors[target] = neighbors.get(target, 0) + weight
            center_edges.append(edge)
        elif target == author_id:
            neighbors[source] = neighbors.get(source, 0) + weight
            center_edges.append(edge)

    if not neighbors:
        # 孤立节点，只返回自己
        center_author = author_meta[author_key]
        return {
            "nodes": [{
                "id": author_id,
                "name": center_author["name"],
                "symbolSize": 40,
                "itemStyle": {"color": COMMUNITY_COLORS.get(center_author["community_id"], "#999")},
                "label": {"show": True},
                "community_id": center_author["community_id"],
                "research_area": center_author["research_area"],
                "paper_count": center_author["paper_count"],
            }],
            "links": []
        }

    # 2. 按权重排序，取 top (max_nodes - 1) 个邻居
    sorted_neighbors = sorted(neighbors.items(), key=lambda x: x[1], reverse=True)
    top_neighbors = sorted_neighbors[:max_nodes - 1]
    neighbor_ids = {nid for nid, _ in top_neighbors}

    # 3. 构建节点列表
    nodes = []

    # 中心节点（更大）
    center_author = author_meta[author_key]
    nodes.append({
        "id": author_id,
        "name": center_author["name"],
        "symbolSize": 50,  # 中心节点更大
        "itemStyle": {"color": COMMUNITY_COLORS.get(center_author["community_id"], "#999")},
        "label": {"show": True, "fontSize": 14, "fontWeight": "bold"},
        "community_id": center_author["community_id"],
        "research_area": center_author["research_area"],
        "paper_count": center_author["paper_count"],
        "degree": center_author["degree"],
    })

    # 邻居节点
    for neighbor_id, weight in top_neighbors:
        neighbor_key = str(neighbor_id)
        if neighbor_key not in author_meta:
            continue

        neighbor_author = author_meta[neighbor_key]
        nodes.append({
            "id": neighbor_id,
            "name": neighbor_author["name"],
            "symbolSize": min(20 + weight * 5, 40),  # 根据合作强度调整大小
            "itemStyle": {"color": COMMUNITY_COLORS.get(neighbor_author["community_id"], "#999")},
            "label": {"show": True, "fontSize": 12},
            "community_id": neighbor_author["community_id"],
            "research_area": neighbor_author["research_area"],
            "paper_count": neighbor_author["paper_count"],
            "degree": neighbor_author["degree"],
        })

    # 4. 构建边列表（只保留显示节点之间的边）
    links = []
    displayed_ids = {author_id} | neighbor_ids

    for edge in center_edges:
        source, target, weight = edge["source"], edge["target"], edge["weight"]
        if source in displayed_ids and target in displayed_ids:
            links.append({
                "source": source,
                "target": target,
                "value": weight,  # ECharts 用 value 表示边权重
                "lineStyle": {"width": min(1 + weight * 0.5, 5)}  # 根据权重调整线宽
            })

    return {
        "nodes": nodes,
        "links": links
    }


@router.get("/graph/full")
def get_full_graph():
    """
    返回全图数据（所有节点 + 所有边），适合 ForceGraph 全图模式。

    Returns:
        {
            "nodes": [{id, name, community_id, research_area, paper_count, degree}],
            "links": [{source, target, value}]
        }
    """
    edges, author_meta = _load_graph_data()

    nodes = [
        {
            "id": int(author_id),
            "name": meta["name"],
            "community_id": meta["community_id"],
            "research_area": meta["research_area"],
            "paper_count": meta["paper_count"],
            "degree": meta.get("degree", 0),
        }
        for author_id, meta in author_meta.items()
    ]

    links = [
        {
            "source": edge["source"],
            "target": edge["target"],
            "value": edge["weight"],
        }
        for edge in edges
    ]

    return {"nodes": nodes, "links": links}


@router.get("/graph/ego")
def get_ego_graph(
    author_id: int = Query(..., description="中心作者 ID"),
    hops: int = Query(1, description="展开跳数（1 或 2，默认 1）"),
    max_nodes: int = Query(80, description="最大节点数（防止过密）"),
):
    """
    返回指定作者的 N-hop Ego-network，格式与 /api/graph/full 一致。

    Args:
        author_id: 中心作者 ID
        hops: 1-hop（直接合作者）或 2-hop（合作者的合作者）
        max_nodes: 最大节点数上限

    Returns:
        ForceGraph 标准格式
    """
    edges, author_meta = _load_graph_data()

    author_key = str(author_id)
    if author_key not in author_meta:
        raise HTTPException(status_code=404, detail=f"Author {author_id} not found")

    # 构建邻接表（无向图）
    adj: dict[int, dict[int, float]] = {}
    for edge in edges:
        s, t, w = edge["source"], edge["target"], edge["weight"]
        adj.setdefault(s, {})[t] = w
        adj.setdefault(t, {})[s] = w

    # BFS 扩展到 hops 跳
    visited: set[int] = {author_id}
    frontier: set[int] = {author_id}
    for _ in range(min(hops, 2)):
        next_frontier: set[int] = set()
        for node in frontier:
            for neighbor in adj.get(node, {}):
                if neighbor not in visited:
                    next_frontier.add(neighbor)
                    visited.add(neighbor)
        frontier = next_frontier
        if len(visited) >= max_nodes:
            break

    # 超出 max_nodes 时按 degree 截断
    if len(visited) > max_nodes:
        sorted_visited = sorted(
            visited,
            key=lambda nid: (nid == author_id, author_meta.get(str(nid), {}).get("degree", 0)),
            reverse=True,
        )
        visited = set(sorted_visited[:max_nodes])

    # 构建返回数据
    nodes = []
    for nid in visited:
        meta = author_meta.get(str(nid))
        if meta is None:
            continue
        nodes.append({
            "id": nid,
            "name": meta["name"],
            "community_id": meta["community_id"],
            "research_area": meta["research_area"],
            "paper_count": meta["paper_count"],
            "degree": meta.get("degree", 0),
        })

    links = [
        {"source": edge["source"], "target": edge["target"], "value": edge["weight"]}
        for edge in edges
        if edge["source"] in visited and edge["target"] in visited
    ]

    return {"nodes": nodes, "links": links}
