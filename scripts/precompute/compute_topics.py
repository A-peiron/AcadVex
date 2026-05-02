"""
预计算每个社群的 TF-IDF 关键词。

读取：data/graph_stats/dblp/author_meta.json
输出：data/precomputed/community_topics.json

输出格式：
{
    "0": {
        "name": "Database",
        "top_keywords": [
            {"word": "data management", "score": 0.42},
            {"word": "query optimization", "score": 0.38},
            ...  共 20 个
        ]
    },
    "1": {...},
    ...
}

算法说明：
  TF-IDF（词频-逆文档频率）
  - TF：某关键词在该社群所有作者 keywords 中出现的频率
  - IDF：log(社群总数 / 包含该关键词的社群数 + 1)，抑制所有社群共有的泛化词
  - 最终分数 = TF × IDF，取 Top-20

运行方式（在 AcadVex 项目根目录）：
    /d/Anaconda_envs/envs/acadvex/python.exe scripts/precompute/compute_topics.py
"""

import json
import math
import os
from collections import Counter, defaultdict

# ── 路径配置 ─────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AUTHORS_IN  = os.path.join(BASE_DIR, "data", "graph_stats", "dblp", "author_meta.json")
COMM_IN     = os.path.join(BASE_DIR, "data", "graph_stats", "dblp", "community_meta.json")
OUTPUT      = os.path.join(BASE_DIR, "data", "precomputed", "community_topics.json")

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

TOP_K = 20   # 每个社群保留前 20 个关键词


def main():
    # ── 1. 加载数据 ─────────────────────────────────────────────────────────
    print("[1/4] 加载作者元数据 ...")
    with open(AUTHORS_IN, encoding="utf-8") as f:
        authors = json.load(f)    # {"0": {"id":0, "keywords":["ml","gnn",...], "community_id":2, ...}, ...}

    with open(COMM_IN, encoding="utf-8") as f:
        comm_meta = json.load(f)  # {"0": {"name":"Database", ...}, ...}

    num_communities = len(comm_meta)
    print(f"    共 {len(authors)} 位作者，{num_communities} 个社群")

    # ── 2. 统计每个社群的关键词词频（TF 部分）──────────────────────────────
    print("[2/4] 统计各社群关键词词频（TF）...")
    # community_kw_counts[comm_id][word] = 出现次数
    community_kw_counts: dict[str, Counter] = defaultdict(Counter)

    for author in authors.values():
        comm_id = str(author["community_id"])
        keywords = author.get("keywords", [])
        for kw in keywords:
            community_kw_counts[comm_id][kw.strip().lower()] += 1

    # ── 3. 计算 IDF：统计每个词出现在多少个社群中 ───────────────────────────
    print("[3/4] 计算逆文档频率（IDF）...")
    # doc_freq[word] = 包含该词的社群数量
    doc_freq: Counter = Counter()
    for comm_id, counter in community_kw_counts.items():
        for word in counter:
            doc_freq[word] += 1

    def idf(word: str) -> float:
        # 平滑 IDF：log((N + 1) / (df + 1)) + 1
        # N = 社群总数，df = 包含该词的社群数
        return math.log((num_communities + 1) / (doc_freq[word] + 1)) + 1

    # ── 4. 计算 TF-IDF，取 Top-K ─────────────────────────────────────────
    print(f"[4/4] 计算 TF-IDF 得分，每个社群保留 Top-{TOP_K} 关键词 ...")
    result = {}

    for comm_id, counter in sorted(community_kw_counts.items()):
        # TF 归一化：该词在本社群的词频 / 本社群总词频
        total_count = sum(counter.values())
        scored = []
        for word, count in counter.items():
            tf = count / total_count
            tfidf_score = tf * idf(word)
            scored.append({"word": word, "score": round(tfidf_score, 6)})

        # 按分数降序，取 Top-K
        top_keywords = sorted(scored, key=lambda x: x["score"], reverse=True)[:TOP_K]
        comm_name = comm_meta.get(comm_id, {}).get("name", f"Community {comm_id}")

        result[comm_id] = {
            "name":         comm_name,
            "top_keywords": top_keywords,
        }

        print(f"    社群 {comm_id}（{comm_name}）Top-5：{[k['word'] for k in top_keywords[:5]]}")

    # ── 5. 保存结果 ──────────────────────────────────────────────────────────
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[完成] 已保存社群主题至 {OUTPUT}")


if __name__ == "__main__":
    main()
