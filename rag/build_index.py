"""
一次性脚本：读取 knowledge_base.json → 嵌入 → 写入 ChromaDB + BM25
运行方式：cd AcadVex && python -m rag.build_index
"""
import json
import pickle
from sentence_transformers import SentenceTransformer
import chromadb
from rank_bm25 import BM25Okapi

KB_PATH    = "rag/data/knowledge_base.json"
CHROMA_DIR = "rag/chroma_db"
BM25_PATH  = "rag/bm25_index.pkl"
MODEL_NAME = "BAAI/bge-small-zh-v1.5"
COLLECTION = "acadvex_kb"


def _tokenize(text: str) -> list[str]:
    """简单分词：按空格 + 常见标点切分"""
    for ch in "，。（）、：；！？「」【】":
        text = text.replace(ch, " ")
    return [t for t in text.split() if t]


def build():
    with open(KB_PATH, encoding="utf-8") as f:
        docs = json.load(f)
    print(f"读取到 {len(docs)} 条文档")

    ids       = [d["id"]       for d in docs]
    texts     = [d["text"]     for d in docs]
    metadatas = [d["metadata"] for d in docs]

    # ── 1. ChromaDB 向量索引 ────────────────────────────────────────────
    print(f"加载模型：{MODEL_NAME}（首次运行会下载，约 100MB）")
    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(texts, show_progress_bar=True).tolist()

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(COLLECTION)   # 重建时清除旧数据
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    print(f"ChromaDB 写入完成 → {CHROMA_DIR}")

    # ── 2. BM25 索引 ────────────────────────────────────────────────────
    tokenized = [_tokenize(t) for t in texts]
    bm25 = BM25Okapi(tokenized)
    with open(BM25_PATH, "wb") as f:
        pickle.dump({"bm25": bm25, "ids": ids, "texts": texts, "metadatas": metadatas}, f)
    print(f"BM25 索引保存 → {BM25_PATH}")
    print("全部完成！")


if __name__ == "__main__":
    build()
