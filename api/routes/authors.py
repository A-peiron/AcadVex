"""
api/routes/authors.py
----------------------
作者相关 API 端点：

  GET /api/authors/search?q=Wei&limit=10            — 按姓名模糊搜索作者
  GET /api/authors/{author_id}                      — 查询单个作者详情
  GET /api/authors/{author_id}/recommendations      — 推荐潜力合作者 Top-K
  GET /api/authors/{author_id}/papers               — 返回作者论文列表
  GET /api/authors/{author_id}/influence            — 返回作者网络影响力指标

⚠️  路由注册顺序说明：
    /authors/search 必须在 /authors/{author_id} 之前注册。
    FastAPI 按注册顺序匹配路由；若路径参数路由先注册，
    字符串 "search" 会被尝试解析为整数 author_id，导致 422 错误。

数据来源：
  - data/graph_stats/{dataset}/author_meta.json     — 作者元数据
  - data/graph_stats/{dataset}/author_names.json    — {id: name} 字典（用于快速搜索）
  - data/graph_stats/{dataset}/paper_meta.json      — 论文元数据 {paper_id: {id, title, venue}}
  - data/precomputed/centrality.json                — 预计算中心性指标
  - data/processed/{dataset}/train.txt + test.txt   — author-paper 映射表（每行: author_id paper_id ...）
  - model/inference.py                              — predict_collab_score（FPGCL 点积打分）
"""

from fastapi import APIRouter, HTTPException, Query
import json
import os
import sys
from pathlib import Path
from typing import Optional

from api.schemas import AuthorInfo

# ── 将项目根目录加入 sys.path，供 model.inference 导入 ──────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

router = APIRouter()

# ── 环境配置 ─────────────────────────────────────────────────────────────────
_dataset = os.getenv("DATASET", "dblp")
_GRAPH_STATS = _PROJECT_ROOT / "data" / "graph_stats" / _dataset
_PRECOMPUTED = _PROJECT_ROOT / "data" / "precomputed"

# ── 惰性加载缓存（模块级别，进程内只读一次）──────────────────────────────────

_author_meta: Optional[dict] = None          # {str(id): AuthorMeta}
_author_names: Optional[dict] = None         # {str(id): name}
_paper_meta: Optional[dict] = None           # {str(paper_id): {id, title, venue}}
_centrality: Optional[dict] = None           # {degree: {...}, betweenness: {...}, closeness: {...}}
_author_papers: Optional[dict] = None        # {int(author_id): [paper_id, ...]}
_edge_set: Optional[set] = None              # {(min_id, max_id), ...}  无向边集合


def _load_author_meta() -> dict:
    global _author_meta
    if _author_meta is None:
        path = _GRAPH_STATS / "author_meta.json"
        with open(path, encoding="utf-8") as f:
            _author_meta = json.load(f)
    return _author_meta


def _load_author_names() -> dict:
    global _author_names
    if _author_names is None:
        path = _GRAPH_STATS / "author_names.json"
        with open(path, encoding="utf-8") as f:
            _author_names = json.load(f)   # {str(id): name}
    return _author_names


def _load_paper_meta() -> dict:
    global _paper_meta
    if _paper_meta is None:
        path = _GRAPH_STATS / "paper_meta.json"
        with open(path, encoding="utf-8") as f:
            _paper_meta = json.load(f)
    return _paper_meta


def _load_centrality() -> dict:
    global _centrality
    if _centrality is None:
        path = _PRECOMPUTED / "centrality.json"
        with open(path, encoding="utf-8") as f:
            _centrality = json.load(f)
    return _centrality


def _load_author_papers() -> dict:
    """
    从 IHGCL 的 train.txt 和 test.txt 构建 author -> [paper_ids] 映射。
    文件格式：每行 "author_id paper_id1 paper_id2 ..."
    两个文件合并，确保包含所有作者-论文关系。
    """
    global _author_papers
    if _author_papers is None:
        mapping: dict[int, list[int]] = {}
        for fname in ["train.txt", "test.txt"]:
            fpath = _PROJECT_ROOT / "data" / "processed" / _dataset / fname
            if not fpath.exists():
                continue
            with open(fpath, encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if not parts:
                        continue
                    author_id = int(parts[0])
                    paper_ids = [int(p) for p in parts[1:]]
                    if author_id not in mapping:
                        mapping[author_id] = []
                    mapping[author_id].extend(paper_ids)
        _author_papers = mapping
    return _author_papers


def _load_edges() -> set:
    """加载合作边集合，用于过滤已有合作的推荐（无向图，(min, max) 规范化）。"""
    global _edge_set
    if _edge_set is None:
        path = _GRAPH_STATS / "edges.json"
        with open(path, encoding="utf-8") as f:
            edges = json.load(f)
        _edge_set = set()
        for e in edges:
            u, v = int(e["source"]), int(e["target"])
            _edge_set.add((min(u, v), max(u, v)))
    return _edge_set


def _has_edge(a: int, b: int) -> bool:
    return (min(a, b), max(a, b)) in _load_edges()


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/authors/search   —  按姓名模糊搜索作者
# ⚠️  必须注册在 /authors/{author_id} 之前！
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/authors/search")
def search_authors(
    q: str = Query(..., description="搜索关键词（姓名子串，大小写不敏感）"),
    limit: int = Query(10, ge=1, le=50, description="最多返回条数"),
):
    """
    按姓名模糊搜索作者，大小写不敏感。

    返回格式：
        [
            {
                "id": 42,
                "name": "Wei Chen",
                "community_id": 1,
                "research_area": "Data Mining",
                "paper_count": 15,
                "degree": 8
            },
            ...
        ]
    """
    if not q.strip():
        return []

    query = q.strip().lower()
    author_names = _load_author_names()  # {str(id): name}
    author_meta = _load_author_meta()

    matches = []
    for id_str, name in author_names.items():
        if query in name.lower():
            meta = author_meta.get(id_str, {})
            matches.append({
                "id": int(id_str),
                "name": name,
                "community_id": meta.get("community_id", -1),
                "research_area": meta.get("research_area", ""),
                "paper_count": meta.get("paper_count", 0),
                "degree": meta.get("degree", 0),
            })

    # 按名称长度升序（更短的名字往往是更精确的匹配），再按 ID 升序
    matches.sort(key=lambda x: (len(x["name"]), x["id"]))
    return matches[:limit]


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/authors/{author_id}   —  查询单个作者详情
# ⚠️  必须注册在 /authors/search 之后！
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/authors/{author_id}", response_model=AuthorInfo)
def get_author_info(author_id: int):
    """
    查询作者详细信息（姓名、社群、研究方向、关键词、合作者数、论文数）。
    """
    meta = _load_author_meta()
    author_key = str(author_id)
    if author_key not in meta:
        raise HTTPException(status_code=404, detail=f"Author {author_id} not found")
    return AuthorInfo(**meta[author_key])


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/authors/{author_id}/recommendations   —  推荐潜力合作者
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/authors/{author_id}/recommendations")
def get_author_recommendations(
    author_id: int,
    top_k: int = Query(10, ge=1, le=50, description="返回推荐数量"),
):
    """
    基于 FPGCL 点积相似度，为指定作者推荐 Top-K 潜力合作者。
    过滤已有合作关系的作者（只推荐尚未合作的候选人）。

    返回格式：
        [
            {
                "id": 123,
                "name": "Alice Wang",
                "score": 2.314,
                "community_id": 1,
                "research_area": "Data Mining",
                "paper_count": 10,
                "degree": 5,
                "common_keywords": ["deep learning", "graph"]
            },
            ...
        ]
    """
    author_meta = _load_author_meta()
    author_key = str(author_id)

    if author_key not in author_meta:
        raise HTTPException(status_code=404, detail=f"Author {author_id} not found")

    # 惰性导入（避免启动时加载全部 torch 模型）
    try:
        from model.inference import load_embeddings, predict_collab_score
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"推理模块加载失败：{e}")

    load_embeddings()   # 确保模型已加载（结果缓存在 inference.py 内部）
    me = author_meta[author_key]
    my_keywords = set(me.get("keywords", []))

    # 对所有其他作者计算点积分数，过滤已合作者
    candidates = []
    for cid_str, cinfo in author_meta.items():
        cid = int(cid_str)
        if cid == author_id:
            continue
        if _has_edge(author_id, cid):
            continue

        score = predict_collab_score(author_id, cid)
        common_kw = list(my_keywords & set(cinfo.get("keywords", [])))

        candidates.append({
            "id": cid,
            "name": cinfo["name"],
            "score": round(float(score), 4),
            "community_id": cinfo.get("community_id", -1),
            "research_area": cinfo.get("research_area", ""),
            "paper_count": cinfo.get("paper_count", 0),
            "degree": cinfo.get("degree", 0),
            "common_keywords": common_kw[:5],   # 最多返回 5 个共同关键词
        })

    # 按分数降序
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:top_k]


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/authors/{author_id}/papers   —  作者论文列表
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/authors/{author_id}/papers")
def get_author_papers(
    author_id: int,
    page: int = Query(1, ge=1, description="页码（从 1 开始）"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """
    返回指定作者的论文列表，支持分页。
    数据来源：IHGCL train.txt + test.txt（作者-论文映射）+ paper_meta.json（论文详情）。

    返回格式：
        {
            "total": 15,
            "page": 1,
            "page_size": 20,
            "papers": [
                {"id": 2364, "title": "...", "venue": "CVPR"},
                ...
            ]
        }
    """
    author_meta = _load_author_meta()
    author_key = str(author_id)

    if author_key not in author_meta:
        raise HTTPException(status_code=404, detail=f"Author {author_id} not found")

    # 获取该作者的论文 ID 列表
    author_papers_map = _load_author_papers()
    paper_ids = author_papers_map.get(author_id, [])

    # 从 paper_meta 取详情
    paper_meta = _load_paper_meta()
    papers = []
    for pid in paper_ids:
        p = paper_meta.get(str(pid))
        if p:
            papers.append({
                "id": p["id"],
                "title": p.get("title", ""),
                "venue": p.get("venue", ""),
            })

    # 按 venue + id 排序（同会议的论文相邻）
    papers.sort(key=lambda x: (x["venue"], x["id"]))

    total = len(papers)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "papers": papers[start:end],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/authors/{author_id}/influence   —  网络影响力指标
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/authors/{author_id}/influence")
def get_author_influence(author_id: int):
    """
    返回指定作者的网络影响力指标（预计算中心性）。

    返回格式：
        {
            "author_id": 42,
            "name": "Wei Chen",
            "degree_centrality": 0.0123,
            "betweenness_centrality": 0.0045,
            "closeness_centrality": 0.2341,
            "degree": 8,
            "paper_count": 15,
            "activity_level": "中度活跃",
            "bridge_role": "一定桥梁作用"
        }
    """
    author_meta = _load_author_meta()
    author_key = str(author_id)

    if author_key not in author_meta:
        raise HTTPException(status_code=404, detail=f"Author {author_id} not found")

    info = author_meta[author_key]
    centrality = _load_centrality()

    deg_c = float(centrality["degree"].get(author_key, 0.0))
    bet_c = float(centrality["betweenness"].get(author_key, 0.0))
    clo_c = float(centrality["closeness"].get(author_key, 0.0))

    # 定性评级（与 agent/tools/author_tools.py 保持一致）
    activity_level = (
        "高度活跃" if deg_c > 0.01 else
        "中度活跃" if deg_c > 0.003 else
        "较少合作"
    )
    bridge_role = (
        "关键桥梁" if bet_c > 0.02 else
        "一定桥梁作用" if bet_c > 0.005 else
        "局部连接"
    )

    return {
        "author_id": author_id,
        "name": info["name"],
        "degree_centrality": round(deg_c, 6),
        "betweenness_centrality": round(bet_c, 6),
        "closeness_centrality": round(clo_c, 6),
        "degree": info.get("degree", 0),
        "paper_count": info.get("paper_count", 0),
        "activity_level": activity_level,
        "bridge_role": bridge_role,
    }
