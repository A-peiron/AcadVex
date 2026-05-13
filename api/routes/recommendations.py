"""
api/routes/recommendations.py
------------------------------
非库内用户推荐端点：基于关键词/研究方向匹配作者（企业级混合检索方案）。

POST /api/recommendations/by-keywords
  输入：{ "keywords": ["graph neural network", "deep learning"], "research_area": "AI" }
  输出：Top-K 匹配作者列表

企业级方案：
  1. ChromaDB 语义搜索（sentence-transformers）
  2. BM25 关键词匹配
  3. RRF（Reciprocal Rank Fusion）融合
  4. CrossEncoder 重排序（可选，性能优化时启用）
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import pickle
import sys
from pathlib import Path
from typing import Optional
import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder

# 将项目根目录加入 sys.path
_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

router = APIRouter()

# 路径配置
_VECTOR_STORE_DIR = _PROJECT_ROOT / "data" / "vector_stores" / "author_vectordb"
_BM25_PATH = _PROJECT_ROOT / "data" / "vector_stores" / "author_bm25.pkl"
_RERANKER_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# 惰性加载缓存
_chroma_client: Optional[chromadb.PersistentClient] = None
_chroma_collection = None
_embedding_model: Optional[SentenceTransformer] = None
_bm25_data: Optional[dict] = None
_cross_encoder: Optional[CrossEncoder] = None


def _tokenize(text: str) -> list[str]:
    """简单分词：按空格 + 常见标点切分"""
    for ch in "，。（）、：；！？「」【】":
        text = text.replace(ch, " ")
    return [t.lower() for t in text.split() if t]


def _load_chroma():
    """加载 ChromaDB 客户端和集合"""
    global _chroma_client, _chroma_collection
    if _chroma_collection is not None:
        return _chroma_collection

    if not _VECTOR_STORE_DIR.exists():
        raise HTTPException(
            status_code=503,
            detail=f"向量库未构建，请先运行：python scripts/build_author_vectordb.py"
        )

    _chroma_client = chromadb.PersistentClient(path=str(_VECTOR_STORE_DIR))
    _chroma_collection = _chroma_client.get_collection("authors")
    return _chroma_collection


def _load_embedding_model():
    """加载 embedding 模型（使用本地缓存）"""
    global _embedding_model
    if _embedding_model is None:
        # 设置环境变量禁用 HuggingFace 在线检查（大陆环境）
        import os
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        _embedding_model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
    return _embedding_model


def _load_bm25():
    """加载 BM25 索引"""
    global _bm25_data
    if _bm25_data is not None:
        return _bm25_data

    if not _BM25_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=f"BM25 索引未构建，请先运行：python scripts/build_author_vectordb.py"
        )

    with open(_BM25_PATH, "rb") as f:
        _bm25_data = pickle.load(f)
    return _bm25_data


def _load_cross_encoder() -> CrossEncoder:
    """加载 CrossEncoder 重排序模型（懒加载，首次调用约10秒）"""
    global _cross_encoder
    if _cross_encoder is None:
        import os
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        _cross_encoder = CrossEncoder(_RERANKER_NAME)
    return _cross_encoder


def _rrf_fusion(chroma_results: list, bm25_results: list, k: int = 60) -> list:
    """
    RRF（Reciprocal Rank Fusion）融合算法。

    公式：score(doc) = Σ 1 / (k + rank_i)
    其中 rank_i 是文档在第 i 个检索器中的排名（从 1 开始）

    参数：
      - chroma_results: [(author_id, distance), ...]（ChromaDB 返回，distance 越小越相似）
      - bm25_results: [(author_id, score), ...]（BM25 返回，score 越大越相似）
      - k: RRF 常数（默认 60，Google 论文推荐值）

    返回：
      - [(author_id, rrf_score), ...]（按 rrf_score 降序）
    """
    rrf_scores = {}

    # ChromaDB 结果（distance 越小越好，转换为排名）
    for rank, (author_id, distance) in enumerate(chroma_results, start=1):
        rrf_scores[author_id] = rrf_scores.get(author_id, 0) + 1 / (k + rank)

    # BM25 结果（score 越大越好，已按降序排列）
    for rank, (author_id, score) in enumerate(bm25_results, start=1):
        rrf_scores[author_id] = rrf_scores.get(author_id, 0) + 1 / (k + rank)

    # 按 RRF 分数降序排序
    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/recommendations/by-keywords
# ═══════════════════════════════════════════════════════════════════════════════

class KeywordRecommendationRequest(BaseModel):
    keywords: list[str] = Field(..., description="关键词列表（如 ['graph neural network', 'deep learning']）")
    research_area: str = Field("", description="研究方向（可选，如 'Artificial Intelligence'）")
    top_k: int = Field(10, ge=1, le=50, description="返回推荐数量")
    use_rerank: bool = Field(False, description="是否使用 CrossEncoder 重排序（更准确但更慢）")


@router.post("/recommendations/by-keywords")
def recommend_by_keywords(req: KeywordRecommendationRequest):
    """
    基于关键词/研究方向推荐作者（非库内用户冷启动）。

    企业级混合检索方案：
      1. ChromaDB 语义搜索（Top-50）
      2. BM25 关键词匹配（Top-50）
      3. RRF 融合排序
      4. 返回 Top-K

    返回格式：
        [
            {
                "id": 42,
                "name": "Wei Chen",
                "score": 0.0234,
                "community_id": 1,
                "research_area": "Data Mining",
                "keywords": ["clustering", "classification"],
                "degree": 8,
                "paper_count": 15
            },
            ...
        ]
    """
    # 构建查询文本
    query_text = f"{req.research_area} {' '.join(req.keywords)}".strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="关键词不能为空")

    # ── 1. ChromaDB 语义搜索 ────────────────────────────────────────────
    collection = _load_chroma()
    model = _load_embedding_model()

    query_embedding = model.encode([query_text])[0].tolist()
    chroma_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=50,  # 召回 Top-50
    )

    # 转换为 [(author_id, distance), ...]
    chroma_candidates = []
    for doc_id, distance in zip(chroma_results["ids"][0], chroma_results["distances"][0]):
        chroma_candidates.append((int(doc_id), distance))

    # ── 2. BM25 关键词匹配 ──────────────────────────────────────────────
    bm25_data = _load_bm25()
    bm25 = bm25_data["bm25"]
    ids = bm25_data["ids"]

    query_tokens = _tokenize(query_text)
    bm25_scores = bm25.get_scores(query_tokens)

    # 转换为 [(author_id, score), ...]，按分数降序，取 Top-50
    bm25_candidates = []
    for idx, score in enumerate(bm25_scores):
        if score > 0:  # 只保留有匹配的
            bm25_candidates.append((int(ids[idx]), score))
    bm25_candidates.sort(key=lambda x: x[1], reverse=True)
    bm25_candidates = bm25_candidates[:50]

    # ── 3. RRF 融合 ─────────────────────────────────────────────────────
    rrf_results = _rrf_fusion(chroma_candidates, bm25_candidates, k=60)

    # ── 4. CrossEncoder 重排序（可选）────────────────────────────────────
    metadatas = bm25_data["metadatas"]
    id_to_metadata = {int(m["author_id"]): m for m in metadatas}

    if req.use_rerank:
        # 取 top_k*3 候选构建重排序输入
        rerank_pool = rrf_results[:req.top_k * 3]
        pairs = []
        valid_ids = []
        for author_id, _ in rerank_pool:
            meta = id_to_metadata.get(author_id)
            if meta:
                doc_text = (
                    f"Author: {meta.get('name', '')}. "
                    f"Research area: {meta.get('research_area', '')}. "
                    f"Keywords: {meta.get('keywords', '')}. "
                    f"Papers: {meta.get('paper_count', 0)}. "
                    f"Degree: {meta.get('degree', 0)}."
                )
                pairs.append((query_text, doc_text))
                valid_ids.append(author_id)

        if pairs:
            ce = _load_cross_encoder()
            ce_scores = ce.predict(pairs)
            reranked = sorted(zip(valid_ids, ce_scores), key=lambda x: x[1], reverse=True)
            final_ids_scores = [(aid, float(s)) for aid, s in reranked[:req.top_k]]
        else:
            final_ids_scores = [(aid, float(s)) for aid, s in rrf_results[:req.top_k]]
    else:
        final_ids_scores = [(aid, float(s)) for aid, s in rrf_results[:req.top_k]]

    # ── 5. 构建返回结果 ─────────────────────────────────────────────────
    results = []
    for author_id, score in final_ids_scores:
        metadata = id_to_metadata.get(author_id)
        if metadata:
            results.append({
                "id": author_id,
                "name": metadata["name"],
                "score": round(score, 6),
                "community_id": metadata["community_id"],
                "research_area": metadata["research_area"],
                "keywords": metadata["keywords"].split(", ") if metadata["keywords"] else [],
                "degree": metadata["degree"],
                "paper_count": metadata["paper_count"],
            })

    return results
