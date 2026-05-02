"""
scripts/build_author_vectordb.py
---------------------------------
构建作者向量数据库（ChromaDB + BM25 混合检索），用于非库内用户的冷启动推荐。

企业级方案：
  1. ChromaDB 语义搜索（sentence-transformers）
  2. BM25 关键词匹配
  3. 混合检索（RRF 融合）
  4. CrossEncoder 重排序（可选）

数据来源：
  - data/graph_stats/dblp/author_meta.json

输出：
  - data/vector_stores/author_vectordb/  — ChromaDB 持久化目录
  - data/vector_stores/author_bm25.pkl   — BM25 索引
"""

import json
import pickle
import sys
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb

# 添加项目根目录到 sys.path
_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


def _tokenize(text: str) -> list[str]:
    """简单分词：按空格 + 常见标点切分"""
    for ch in "，。（）、：；！？「」【】":
        text = text.replace(ch, " ")
    return [t.lower() for t in text.split() if t]


def build_author_vectordb(dataset: str = "dblp"):
    """构建作者向量数据库"""

    # 路径配置
    author_meta_path = _PROJECT_ROOT / "data" / "graph_stats" / dataset / "author_meta.json"
    output_dir = _PROJECT_ROOT / "data" / "vector_stores" / "author_vectordb"
    bm25_path = _PROJECT_ROOT / "data" / "vector_stores" / "author_bm25.pkl"

    print(f"[1/5] 加载作者元数据：{author_meta_path}")
    with open(author_meta_path, encoding="utf-8") as f:
        author_meta = json.load(f)

    print(f"      共 {len(author_meta)} 位作者")

    # 构建文档列表
    print("[2/5] 构建文档列表...")
    ids = []
    documents = []
    metadatas = []
    corpus_for_bm25 = []

    for author_id_str, info in author_meta.items():
        # 文档内容：姓名 | 研究方向 | 关键词（用于语义搜索）
        keywords_str = ", ".join(info.get("keywords", []))
        research_area = info.get("research_area", "")
        doc_text = f"{info['name']} | {research_area} | {keywords_str}"

        ids.append(author_id_str)
        documents.append(doc_text)
        metadatas.append({
            "author_id": int(author_id_str),
            "name": info["name"],
            "community_id": info.get("community_id", -1),
            "research_area": research_area,
            "keywords": keywords_str,
            "degree": info.get("degree", 0),
            "paper_count": info.get("paper_count", 0),
        })

        # BM25 语料（分词后）
        corpus_for_bm25.append(_tokenize(doc_text))

    print(f"      构建了 {len(documents)} 个文档")

    # 初始化 embedding 模型
    print("[3/5] 初始化 embedding 模型（BAAI/bge-small-zh-v1.5）...")
    print("      使用本地缓存模型...")

    # 设置环境变量禁用 HuggingFace 在线检查
    import os
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
    embeddings = model.encode(documents, show_progress_bar=True, batch_size=32).tolist()

    # 构建 ChromaDB
    print(f"[4/5] 构建 ChromaDB 向量库：{output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(output_dir))

    # 删除旧集合（如果存在）
    try:
        client.delete_collection("authors")
    except Exception:
        pass

    collection = client.create_collection(
        name="authors",
        metadata={"hnsw:space": "cosine"},  # 余弦相似度
    )

    # 批量插入（避免内存溢出）
    batch_size = 500
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i+batch_size]
        batch_embeddings = embeddings[i:i+batch_size]
        batch_documents = documents[i:i+batch_size]
        batch_metadatas = metadatas[i:i+batch_size]

        collection.add(
            ids=batch_ids,
            embeddings=batch_embeddings,
            documents=batch_documents,
            metadatas=batch_metadatas,
        )
        print(f"      已插入 {min(i+batch_size, len(ids))}/{len(ids)} 条记录")

    print(f"ChromaDB 构建完成！")

    # 构建 BM25 索引
    print(f"[5/5] 构建 BM25 索引：{bm25_path}")
    from rank_bm25 import BM25Okapi
    bm25 = BM25Okapi(corpus_for_bm25)

    bm25_path.parent.mkdir(parents=True, exist_ok=True)
    with open(bm25_path, "wb") as f:
        pickle.dump({
            "bm25": bm25,
            "ids": ids,
            "documents": documents,
            "metadatas": metadatas,
        }, f)

    print(f"BM25 索引保存完成！")
    print(f"\n全部完成！")
    print(f"  - ChromaDB：{output_dir}")
    print(f"  - BM25：{bm25_path}")
    print(f"  - 文档数：{len(documents)}")

    # 测试查询
    print("\n[测试] 混合检索示例：")
    query = "graph neural network deep learning"
    print(f"  查询：{query}")

    # ChromaDB 语义搜索
    query_embedding = model.encode([query])[0].tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3,
    )
    print(f"  语义搜索 Top-3：")
    for i, (doc_id, metadata) in enumerate(zip(results["ids"][0], results["metadatas"][0]), 1):
        print(f"    {i}. {metadata['name']} ({metadata['research_area']})")

    # BM25 关键词匹配
    query_tokens = _tokenize(query)
    bm25_scores = bm25.get_scores(query_tokens)
    top_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:3]
    print(f"  BM25 Top-3：")
    for i, idx in enumerate(top_indices, 1):
        metadata = metadatas[idx]
        print(f"    {i}. {metadata['name']} ({metadata['research_area']})")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="构建作者向量数据库")
    parser.add_argument("--dataset", default="dblp", choices=["dblp", "acm"], help="数据集名称")
    args = parser.parse_args()

    build_author_vectordb(args.dataset)
