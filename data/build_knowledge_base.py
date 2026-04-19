"""
data/build_knowledge_base.py
----------------------------
从图统计量生成 RAG 知识库。
输出：rag/data/knowledge_base.json
格式：[{"id": "...", "text": "...", "metadata": {...}}, ...]
"""

import json
from pathlib import Path

# ── 路径配置 ──────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent
DATA_DIR   = BASE_DIR / "data" / "graph_stats" / "dblp"
OUTPUT_DIR = BASE_DIR / "rag" / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_json(filename: str) -> dict:
    return json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))


def build_knowledge_base() -> list[dict]:
    author_meta   = load_json("author_meta.json")
    community_meta = load_json("community_meta.json")
    paper_meta    = load_json("paper_meta.json")
    venue_names   = load_json("venue_names.json")

    docs = []

    # ── 1. 系统概述 ───────────────────────────────────────────────────
    n_authors = len(author_meta)
    n_papers  = len(paper_meta)
    n_venues  = len(venue_names)
    docs.append({
        "id": "overview",
        "text": (
            f"AcadVex 是基于 FPGCL 模型的学术合作网络智能分析平台。"
            f"数据集来自 DBLP，包含 {n_authors} 位作者、{n_papers} 篇论文、"
            f"{n_venues} 个学术会议。"
            f"系统使用图神经网络（GNN）学习作者 embedding，通过点积计算合作潜力分数。"
        ),
        "metadata": {"type": "overview"},
    })

    # ── 2. FPGCL 模型说明 ─────────────────────────────────────────────
    docs.append({
        "id": "model_fpgcl",
        "text": (
            "FPGCL（Feature-enhanced Parallel Graph Contrastive Learning）是本系统的核心模型。"
            "它融合了 HAEGNN（异构注意力图神经网络）和 IHGCL（意图引导异构图对比学习）两个组件。"
            "HAEGNN 包含 SCL（语义卷积层）和 CAL（内容注意力层），并行提取结构特征和语义特征。"
            "IHGCL 通过对比学习优化 embedding 质量。"
            "模型在 DBLP 数据集上的链接预测 Recall@20 达到 0.5835，社群挖掘 NMI 达到 0.4125。"
        ),
        "metadata": {"type": "model"},
    })

    # ── 3. 合作潜力预测说明 ───────────────────────────────────────────
    docs.append({
        "id": "collab_prediction",
        "text": (
            "合作潜力预测通过计算两位作者 embedding 向量的点积得到分数。"
            "分数越高表示两位作者合作的可能性越大。"
            "点积能捕捉 embedding 空间中两个向量的方向相似性，"
            "经过 FPGCL 训练后，合作过的作者 embedding 在空间中更接近。"
            "预测时不需要重新运行模型，直接读取预计算的 embedding 文件进行点积运算。"
        ),
        "metadata": {"type": "feature"},
    })

    # ── 4. 各研究社群 ─────────────────────────────────────────────────
    for cid, c in community_meta.items():
        # 取 top5 成员姓名
        top_names = []
        for aid in c["top_members"][:5]:
            info = author_meta.get(str(aid), {})
            top_names.append(info.get("name", f"ID={aid}"))

        docs.append({
            "id": f"community_{cid}",
            "text": (
                f"{c['name']} 社群（ID={cid}）共有 {c['size']} 位作者，"
                f"是 DBLP 数据集中的四大研究社群之一。"
                f"该社群核心成员包括：{', '.join(top_names)}等。"
                f"社群通过 K-Means 聚类作者 embedding 得到，"
                f"同社群作者在研究方向和合作网络上具有较高相似性。"
            ),
            "metadata": {"type": "community", "community_id": int(cid), "name": c["name"]},
        })

    # ── 5. 技术架构说明 ───────────────────────────────────────────────
    docs.append({
        "id": "tech_stack",
        "text": (
            "AcadVex 系统架构分为五层："
            "模型层使用预训练的 FPGCL 模型提供 embedding；"
            "推理层通过 model/inference.py 进行点积打分和元数据查询；"
            "Agent 层使用手写 ReAct 循环（后迁移至 LangGraph）实现工具调用和多轮推理；"
            "API 层使用 FastAPI 提供 REST 接口，支持 SSE 流式输出；"
            "RAG 层使用 ChromaDB + BM25 + CrossEncoder 三阶段检索增强生成。"
        ),
        "metadata": {"type": "architecture"},
    })

    # ── 6. 数据集说明 ─────────────────────────────────────────────────
    docs.append({
        "id": "dataset_dblp",
        "text": (
            f"DBLP 数据集包含计算机科学领域的学术合作网络数据。"
            f"本系统使用的子集共有 {n_authors} 位作者和 {n_papers} 篇论文，"
            f"涵盖 {n_venues} 个顶级学术会议，分为四个研究社群："
            f"Database（数据库）、Data Mining（数据挖掘）、"
            f"Artificial Intelligence（人工智能）、Information Retrieval（信息检索）。"
            f"作者的真实姓名来自 MAGNN 原始数据集。"
        ),
        "metadata": {"type": "dataset"},
    })

    # ── 7. 高影响力作者（top degree，每社群取前3）────────────────────
    from collections import defaultdict
    community_authors = defaultdict(list)
    for aid, info in author_meta.items():
        community_authors[info["community_id"]].append(info)

    for cid, authors in community_authors.items():
        top3 = sorted(authors, key=lambda x: x["paper_count"], reverse=True)[:3]
        names_info = [
            f"{a['name']}（{a['paper_count']}篇论文，ID={a['id']}）"
            for a in top3
        ]
        comm_name = community_meta[str(cid)]["name"]
        docs.append({
            "id": f"top_authors_community_{cid}",
            "text": (
                f"{comm_name} 社群中论文数量最多的作者包括："
                f"{', '.join(names_info)}。"
            ),
            "metadata": {"type": "top_authors", "community_id": cid},
        })

    return docs


if __name__ == "__main__":
    docs = build_knowledge_base()
    output_path = OUTPUT_DIR / "knowledge_base.json"
    output_path.write_text(
        json.dumps(docs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✅ 生成完成：{output_path}")
    print(f"   共 {len(docs)} 条知识文档")
    for doc in docs:
        print(f"   [{doc['id']}] {doc['text'][:50]}...")
