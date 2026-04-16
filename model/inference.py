"""
model/inference.py
------------------
负责加载预计算的 embedding，对外提供打分和查询接口。
所有函数都是纯 CPU 操作，不依赖 GPU。
"""

import json
import torch
from pathlib import Path

# AcadVex/data/ 的根目录（相对于项目根，或绝对路径）
_DATA_ROOT = Path(__file__).parent.parent / 'data'

# 模块级缓存：只加载一次，避免重复 IO
_cache: dict = {}


def load_embeddings(dataset: str = 'dblp') -> dict:
    """
    加载指定数据集的 author/paper embedding 及元数据。
    结果缓存在模块变量中，多次调用只读磁盘一次。

    Returns:
        {
          'author_emb': Tensor[n_authors, 64],
          'paper_emb':  Tensor[n_papers,  64],
          'author_meta': dict,   # str(id) → {name, community_id, ...}
          'paper_meta':  dict,   # str(id) → {title, venue, ...}
          'community_meta': dict,
        }
    """
    if dataset in _cache:
        return _cache[dataset]

    emb_dir   = _DATA_ROOT / 'embeddings'   / dataset
    stats_dir = _DATA_ROOT / 'graph_stats'  / dataset

    data = {
        'author_emb':    torch.load(emb_dir / 'author_emb.pt', map_location='cpu'),
        'paper_emb':     torch.load(emb_dir / 'paper_emb.pt',  map_location='cpu'),
    }

    for name in ('author_meta', 'paper_meta', 'community_meta'):
        with open(stats_dir / f'{name}.json', encoding='utf-8') as f:
            data[name] = json.load(f)

    _cache[dataset] = data
    return data


def predict_collab_score(a_id: int, b_id: int,
                         dataset: str = 'dblp') -> float:
    """
    预测两位作者的合作潜力分数（越高越有可能合作）。
    使用 embedding 点积，与训练时的 BPR 目标函数一致。

    Args:
        a_id: 作者 A 的内部索引（0-based）
        b_id: 作者 B 的内部索引（0-based）

    Returns:
        float，未经归一化的原始点积分数
    """
    data = load_embeddings(dataset)
    emb  = data['author_emb']          # [n_authors, 64]

    n = emb.shape[0]
    if not (0 <= a_id < n and 0 <= b_id < n):
        raise ValueError(f'author id 超出范围 [0, {n-1}]，收到 a={a_id}, b={b_id}')

    score = torch.dot(emb[a_id], emb[b_id]).item()
    return score


def get_author_info(a_id: int, dataset: str = 'dblp') -> dict:
    """返回作者的完整元数据。"""
    data = load_embeddings(dataset)
    info = data['author_meta'].get(str(a_id))
    if info is None:
        raise ValueError(f'找不到 author_id={a_id}')
    return info


def get_paper_info(p_id: int, dataset: str = 'dblp') -> dict:
    """返回论文的元数据。"""
    data = load_embeddings(dataset)
    info = data['paper_meta'].get(str(p_id))
    if info is None:
        raise ValueError(f'找不到 paper_id={p_id}')
    return info


# ── 快速验证（直接运行此文件时执行）──────────────────────────────────────
if __name__ == '__main__':
    import os, sys
    # 把项目根加入 path，确保相对路径正确
    sys.path.insert(0, str(Path(__file__).parent.parent))

    score = predict_collab_score(42, 88)
    print(f'Author 42 × Author 88 合作分数: {score:.4f}')

    a42 = get_author_info(42)
    a88 = get_author_info(88)
    print(f'  {a42["name"]} ({a42["research_area"]})')
    print(f'  {a88["name"]} ({a88["research_area"]})')
