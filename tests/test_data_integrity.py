# tests/test_data_integrity.py
"""
L1-B 数据层完整性测试（无需服务运行）
运行方式：conda run -n acadvex pytest tests/test_data_integrity.py -v --tb=short
"""
import sys
import json
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DATA_ROOT = Path(__file__).parent.parent / "data"


class TestDataFiles:
    def test_author_meta_exists(self):
        p = DATA_ROOT / "graph_stats/dblp/author_meta.json"
        assert p.exists(), f"author_meta.json 不存在: {p}"

    def test_author_meta_count(self):
        p = DATA_ROOT / "graph_stats/dblp/author_meta.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        assert len(data) == 4057, f"作者数应为4057，实际: {len(data)}"

    def test_author_meta_fields(self):
        p = DATA_ROOT / "graph_stats/dblp/author_meta.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        sample = next(iter(data.values()))
        for field in ["id", "name", "community_id", "keywords"]:
            assert field in sample, f"author_meta 缺少字段: {field}"

    def test_community_id_range(self):
        p = DATA_ROOT / "graph_stats/dblp/author_meta.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        ids = {v["community_id"] for v in data.values()}
        assert ids == {0, 1, 2, 3}, f"community_id 值域应为{{0,1,2,3}}，实际: {ids}"

    def test_centrality_exists(self):
        p = DATA_ROOT / "precomputed/centrality.json"
        assert p.exists(), f"centrality.json 不存在: {p}"

    def test_centrality_keys(self):
        p = DATA_ROOT / "precomputed/centrality.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        for key in ["degree", "betweenness", "closeness"]:
            assert key in data, f"centrality.json 缺少字段: {key}"

    def test_centrality_author_ids_valid(self):
        meta_path = DATA_ROOT / "graph_stats/dblp/author_meta.json"
        cent_path = DATA_ROOT / "precomputed/centrality.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        cent = json.loads(cent_path.read_text(encoding="utf-8"))
        # 抽查 degree 中的 ID 都在 author_meta 中
        for aid in list(cent["degree"].keys())[:100]:
            assert aid in meta, f"centrality 中的 ID {aid} 不在 author_meta 中"

    def test_edges_exists(self):
        p = DATA_ROOT / "graph_stats/dblp/edges.json"
        assert p.exists(), f"edges.json 不存在: {p}"

    def test_edges_format(self):
        p = DATA_ROOT / "graph_stats/dblp/edges.json"
        edges = json.loads(p.read_text(encoding="utf-8"))
        assert len(edges) > 0, "edges.json 不应为空"
        sample = edges[0]
        assert "source" in sample and "target" in sample, \
            f"边应有 source/target 字段: {sample}"

    def test_author_emb_exists(self):
        p = DATA_ROOT / "embeddings/dblp/author_emb.pt"
        assert p.exists(), f"author_emb.pt 不存在: {p}"

    def test_author_emb_shape(self):
        import torch
        p = DATA_ROOT / "embeddings/dblp/author_emb.pt"
        emb = torch.load(str(p), map_location="cpu")
        assert emb.shape[0] == 4057, f"embedding 行数应为4057，实际: {emb.shape[0]}"
        assert emb.shape[1] > 0, "embedding 维度应 > 0"

    def test_community_topics_exists(self):
        p = DATA_ROOT / "precomputed/community_topics.json"
        assert p.exists(), f"community_topics.json 不存在: {p}"

    def test_community_topics_count(self):
        p = DATA_ROOT / "precomputed/community_topics.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        assert len(data) == 4, f"应有4个社群的topics，实际: {len(data)}"
