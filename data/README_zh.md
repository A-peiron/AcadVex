# data/ — 预计算数据目录

> [English](README.md)

本目录存放 AcadVex 运行时所需的全部预计算数据。**大型二进制文件不提交到 git**（见根目录 `.gitignore`），使用前需自行生成或从配套仓库导出。

---

## 目录结构

```
data/
├── embeddings/dblp/          ← FPGCL 模型输出（git-ignored，*.pt）
│   ├── author_emb.pt         ← (4057 × 64) float32 张量，每行对应一个作者
│   └── paper_emb.pt          ← (14328 × 64) float32 张量，每行对应一篇论文
│
├── graph_stats/dblp/         ← 预计算图元数据（git-ignored）
│   ├── author_meta.json      ← {id, name, community_id, keywords, ...} × 4057
│   ├── author_names.json     ← {author_id: name} 查找表
│   ├── paper_meta.json       ← {id, title, venue_id, year, author_ids}
│   ├── paper_titles.json     ← {paper_id: title} 查找表
│   ├── edges.json            ← [[src, dst], ...] 合作边列表
│   ├── community_meta.json   ← {community_id: {name, color, ...}} × 4
│   └── venue_names.json      ← {venue_id: name} × 20
│
├── precomputed/              ← 小型派生文件（已提交到 git）
│   ├── centrality.json       ← {author_id: {degree, betweenness, closeness}}
│   └── community_topics.json ← {community_id: [关键词列表]}
│
├── vector_stores/            ← RAG 索引（git-ignored，大型二进制）
│   ├── author_vectordb/      ← ChromaDB 作者语义检索集合
│   └── author_bm25.pkl       ← BM25 关键词检索索引
│
└── build_knowledge_base.py   ← 从头重建 vector_stores/ 的脚本
```

---

## 再生成方法

### Embeddings（`embeddings/dblp/`）

在配套 FPGCL 仓库中导出：

```bash
# 在 FPGCL 仓库中执行
python export_for_app.py --dataset dblp --out /path/to/AcadVex/data/
```

预期形状：`author_emb.pt` → `(4057, 64)`，`paper_emb.pt` → `(14328, 64)`。

### 图元数据（`graph_stats/dblp/`）

由上方 FPGCL 导出脚本同步生成。

### 预计算中心性与社群主题

```bash
cd AcadVex
python scripts/precompute/compute_centrality.py
python scripts/precompute/compute_topics.py
```

### 向量索引（`vector_stores/`）

```bash
python scripts/build_author_vectordb.py
```

使用 `bge-small-zh-v1.5` 对所有作者做嵌入，写入 ChromaDB 集合并构建 BM25 索引。需先确保 `data/graph_stats/dblp/` 存在。

---

## 数据集统计（DBLP）

| 指标 | 数值 |
|------|------|
| 作者数量 | 4,057 |
| 论文数量 | 14,328 |
| 社群数量 | 4 |
| 学术会议数量 | 20 |
| Embedding 维度 | 64 |
