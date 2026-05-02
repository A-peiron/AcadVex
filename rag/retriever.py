"""
三阶段检索：向量 + BM25 + RRF 融合 + CrossEncoder 精排
  Stage 1a: ChromaDB 向量检索（语义相似）
  Stage 1b: BM25 关键词检索（精确匹配）
  Stage 2:  Reciprocal Rank Fusion 排序
  Stage 3:  CrossEncoder 精排（query-document 联合编码，重新打分）
"""

import os
# 强制离线模式：必须在导入 sentence_transformers 之前设置
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import pickle
from typing import Any
import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder

# 索引配置
CHROMA_DIR = "rag/chroma_db"
BM25_PATH  = "rag/bm25_index.pkl"
MODEL_NAME = "BAAI/bge-small-zh-v1.5"
COLLECTION = "acadvex_kb"
RERANKER_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# 全局变量（懒加载）
_model:      SentenceTransformer | None = None
_collection: Any = None
_bm25_data:  dict | None = None
_cross_encoder: CrossEncoder | None = None

# 供外部调用的检索接口，以及内部使用的工具函数都在这里实现
def _load():
    global _model, _collection, _bm25_data, _cross_encoder
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = client.get_collection(COLLECTION)
    if _bm25_data is None:
        with open(BM25_PATH, "rb") as f:
            _bm25_data = pickle.load(f)
    if _cross_encoder is None:
        _cross_encoder = CrossEncoder(RERANKER_NAME)


# 下面是检索实现：向量检索、BM25 检索、RRF 融合，以及主接口 retrieve()
def _tokenize(text: str) -> list[str]:
    for ch in "，。（）、：；！？「」【】":
        text = text.replace(ch, " ")
    return [t for t in text.split() if t]

# 向量检索和 BM25 检索都返回 list[dict]，每条 dict 包含 {id, text, metadata, score}，score 是相似度或 BM25 分数
def _vector_search(query: str, top_k: int) -> list[dict]:
    _load()
    emb = _model.encode([query]).tolist()
    res = _collection.query(query_embeddings=emb, n_results=top_k)
    return [
        {
            "id":       res["ids"][0][i],
            "text":     res["documents"][0][i],
            "metadata": res["metadatas"][0][i],
            "score":    1 - res["distances"][0][i],
        }
        for i in range(len(res["ids"][0]))
    ]

# BM25 检索：直接用预加载的 BM25 模型打分，返回 top_k 结果
def _bm25_search(query: str, top_k: int) -> list[dict]:
    _load()
    bm25      = _bm25_data["bm25"]
    ids       = _bm25_data["ids"]
    texts     = _bm25_data["texts"]
    metadatas = _bm25_data["metadatas"]

    scores = bm25.get_scores(_tokenize(query))
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [
        {"id": ids[i], "text": texts[i], "metadata": metadatas[i], "score": float(scores[i])}
        for i in ranked
    ]

# RRF 融合：对两个结果列表分别按排名计算 1/(k+rank)，求和后排序，返回融合后的结果列表
def _rrf_fusion(results_a: list[dict], results_b: list[dict], k: int = 60) -> list[dict]:
    """Reciprocal Rank Fusion：1/(k+rank) 求和，rank 从 1 开始"""
    scores: dict[str, float] = {}
    doc_map: dict[str, dict] = {}

    for rank, doc in enumerate(results_a, start=1):
        scores[doc["id"]] = scores.get(doc["id"], 0.0) + 1 / (k + rank)
        doc_map[doc["id"]] = doc
    for rank, doc in enumerate(results_b, start=1):
        scores[doc["id"]] = scores.get(doc["id"], 0.0) + 1 / (k + rank)
        doc_map[doc["id"]] = doc

    return [doc_map[did] for did in sorted(scores, key=scores.__getitem__, reverse=True)]


def _rerank(query: str, candidates: list[dict]) -> list[dict]:
    """Stage 3: CrossEncoder 对 RRF 候选重新打分并排序"""
    if not candidates:
        return candidates
    pairs = [(query, doc["text"]) for doc in candidates]
    scores = _cross_encoder.predict(pairs)
    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in ranked]


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    """主接口：向量 + BM25 → RRF → CrossEncoder 精排 → top_k 结果"""
    vec      = _vector_search(query, top_k=top_k * 2)
    bm25_res = _bm25_search(query,  top_k=top_k * 2)
    fused    = _rrf_fusion(vec, bm25_res)
    return _rerank(query, fused)[:top_k]

