# tests/test_api.py
"""
L2-A API 端点完整性测试（pytest + TestClient，无需服务运行）
运行方式：conda run -n acadvex pytest tests/test_api.py -v --tb=short
"""
import sys
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="module")
def client():
    from api.main import app
    return TestClient(app)


def _reset_limiter():
    from api.middleware.rate_limit import limiter
    storage = limiter._storage
    if hasattr(storage, '_storage'):
        storage._storage.clear()
    elif hasattr(storage, 'storage'):
        storage.storage.clear()


# ─── /health ──────────────────────────────────────────────────────────────────

class TestHealth:
    def test_healthy(self, client):
        with patch("pathlib.Path.exists", return_value=True):
            r = client.get("/health")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "healthy"
        assert d["data_files"] == "ok"
        assert d["centrality"] == "ok"

    def test_degraded(self, client):
        with patch("pathlib.Path.exists", return_value=False):
            r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "degraded"


# ─── /api/authors/search ──────────────────────────────────────────────────────

class TestAuthorSearch:
    def test_normal(self, client):
        r = client.get("/api/authors/search?q=Han&limit=5")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) <= 5
        if data:
            assert "id" in data[0] and "name" in data[0]

    def test_not_found(self, client):
        r = client.get("/api/authors/search?q=ZZNOTEXIST999")
        assert r.status_code == 200
        assert r.json() == []

    def test_missing_q_param(self, client):
        r = client.get("/api/authors/search")
        assert r.status_code == 422

    def test_limit_zero(self, client):
        # limit 有 ge=1 约束，0 应返回 422
        r = client.get("/api/authors/search?q=Han&limit=0")
        assert r.status_code == 422

    def test_large_limit(self, client):
        # limit 有 le=50 约束，1000 应返回 422
        r = client.get("/api/authors/search?q=a&limit=1000")
        assert r.status_code == 422


# ─── /api/authors/{id} ────────────────────────────────────────────────────────

class TestAuthorDetail:
    def test_existing_author(self, client):
        r = client.get("/api/authors/42")
        assert r.status_code == 200
        d = r.json()
        assert "id" in d and "name" in d and "community_id" in d

    def test_nonexistent_author(self, client):
        r = client.get("/api/authors/999999")
        assert r.status_code == 404

    def test_invalid_id(self, client):
        r = client.get("/api/authors/abc")
        assert r.status_code == 422

    def test_negative_id(self, client):
        r = client.get("/api/authors/-1")
        assert r.status_code in [404, 422]


# ─── /api/authors/{id}/recommendations ───────────────────────────────────────

class TestAuthorRecommendations:
    def test_normal(self, client):
        r = client.get("/api/authors/42/recommendations")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_score_range(self, client):
        r = client.get("/api/authors/42/recommendations?top_k=5")
        assert r.status_code == 200
        for item in r.json():
            assert "score" in item, f"推荐项应含 score 字段: {item}"
            assert isinstance(item["score"], (int, float)), f"score 应为数字: {item['score']}"

    def test_no_self_recommendation(self, client):
        r = client.get("/api/authors/42/recommendations?top_k=10")
        assert r.status_code == 200
        ids = [item.get("id") for item in r.json()]
        assert 42 not in ids, "推荐列表不应包含查询作者自身"

    def test_nonexistent_author(self, client):
        r = client.get("/api/authors/999999/recommendations")
        assert r.status_code == 404

    def test_top_k_zero(self, client):
        # top_k 有 ge=1 约束，0 应返回 422
        r = client.get("/api/authors/42/recommendations?top_k=0")
        assert r.status_code == 422


# ─── /api/authors/{id}/papers ─────────────────────────────────────────────────

class TestAuthorPapers:
    def test_normal(self, client):
        r = client.get("/api/authors/42/papers")
        assert r.status_code == 200
        d = r.json()
        # 返回分页对象 {page, page_size, papers, total}
        assert "papers" in d and isinstance(d["papers"], list)

    def test_nonexistent_author(self, client):
        r = client.get("/api/authors/999999/papers")
        assert r.status_code in [404, 200]


# ─── /api/authors/{id}/influence ─────────────────────────────────────────────

class TestAuthorInfluence:
    def test_normal(self, client):
        r = client.get("/api/authors/42/influence")
        assert r.status_code == 200
        d = r.json()
        assert any(k in d for k in ["degree", "degree_centrality"]), \
            f"应包含 degree 字段: {d}"

    def test_nonexistent_author(self, client):
        r = client.get("/api/authors/999999/influence")
        assert r.status_code == 404


# ─── /api/graph ───────────────────────────────────────────────────────────────

class TestGraph:
    def test_graph_with_author(self, client):
        r = client.get("/api/graph?author_id=42")
        assert r.status_code == 200
        d = r.json()
        assert "nodes" in d and "links" in d

    def test_graph_max_nodes(self, client):
        r = client.get("/api/graph?author_id=42&max_nodes=5")
        assert r.status_code == 200
        d = r.json()
        assert len(d.get("nodes", [])) <= 5 + 1  # 中心节点 + 邻居

    def test_graph_nonexistent_author(self, client):
        r = client.get("/api/graph?author_id=999999")
        assert r.status_code in [404, 200]

    def test_graph_full(self, client):
        r = client.get("/api/graph/full")
        assert r.status_code == 200
        d = r.json()
        assert "nodes" in d
        assert len(d["nodes"]) == 4057, f"全图应有4057个节点，实际: {len(d['nodes'])}"


# ─── /api/chat ────────────────────────────────────────────────────────────────

class TestChat:
    @patch("api.routes.chat.run_agent", return_value="测试回复")
    def test_normal(self, mock, client):
        _reset_limiter()
        r = client.post("/api/chat", json={"message": "测试"})
        assert r.status_code == 200
        assert r.json()["answer"] == "测试回复"

    def test_missing_message(self, client):
        _reset_limiter()
        r = client.post("/api/chat", json={"wrong": "field"})
        assert r.status_code == 422

    def test_invalid_json(self, client):
        _reset_limiter()
        r = client.post("/api/chat", content=b"not json", headers={"Content-Type": "application/json"})
        assert r.status_code == 422

    def test_oversized_message(self, client):
        _reset_limiter()
        r = client.post("/api/chat", json={"message": "A" * 2001})
        assert r.status_code == 413


# ─── 限流 ─────────────────────────────────────────────────────────────────────

class TestRateLimiting:
    @patch("api.routes.chat.run_agent", return_value="ok")
    def test_rate_limit_triggered(self, mock):
        from api.main import app
        _reset_limiter()
        c = TestClient(app)
        hit_429 = False
        for i in range(25):
            r = c.post("/api/chat", json={"message": f"test {i}"})
            if r.status_code == 429:
                hit_429 = True
                break
        assert hit_429, "25次请求后应触发429限流"


# ─── 全局异常处理 ──────────────────────────────────────────────────────────────

class TestGlobalExceptionHandler:
    def test_500_handler(self):
        from api.main import app
        _reset_limiter()
        with patch("api.routes.chat.run_agent", side_effect=Exception("模拟错误")):
            c = TestClient(app, raise_server_exceptions=False)
            r = c.post("/api/chat", json={"message": "触发错误"})
        assert r.status_code == 500
        assert r.json()["error"] == "服务器内部错误"
