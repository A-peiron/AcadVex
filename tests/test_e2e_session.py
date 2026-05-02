# tests/test_e2e_session.py
"""
L3-A 会话管理端到端测试（需后端运行在 localhost:8000）
运行方式：conda run -n acadvex pytest tests/test_e2e_session.py -v --tb=short
"""
import sys
import json
import time
import pytest
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:8000"


def _stream_post(message: str, session_id: str) -> str:
    """发送 SSE 请求，返回完整的 assistant 文本"""
    resp = requests.post(
        f"{BASE_URL}/api/chat/stream",
        json={"message": message, "session_id": session_id},
        stream=True,
        timeout=60,
    )
    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}"
    text = ""
    for line in resp.iter_lines():
        if not line:
            continue
        decoded = line.decode("utf-8") if isinstance(line, bytes) else line
        if not decoded.startswith("data: "):
            continue
        try:
            event = json.loads(decoded[6:])
            if event["type"] == "token":
                text += event["content"]
        except Exception:
            pass
    return text


@pytest.fixture(scope="module", autouse=True)
def check_server():
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code != 200:
            pytest.skip("后端服务未运行，跳过 L3 测试")
    except Exception:
        pytest.skip("后端服务未运行，跳过 L3 测试")


class TestSessionMemory:
    def test_remembers_context(self):
        """同一 session 第二轮应记住第一轮内容"""
        sid = f"test-mem-{int(time.time())}"
        _stream_post("我叫张三，研究推荐算法", sid)
        time.sleep(1)
        ans2 = _stream_post("你还记得我叫什么名字？", sid)
        assert "张三" in ans2, f"AI 应记住用户名字，实际回复: {ans2[:200]}"

    def test_session_isolation(self):
        """不同 session 互不干扰——验证会话历史不跨 session 泄漏"""
        ts = int(time.time())
        sid_a = f"session-A-{ts}"
        sid_b = f"session-B-{ts}"
        # 使用数据库中不存在的唯一名字
        _stream_post("我叫 Zxqwerty123", sid_a)
        _stream_post("我叫 Abcfoo456", sid_b)
        time.sleep(1)
        ans_a = _stream_post("你知道 Abcfoo456 吗？", sid_a)
        # 会话隔离验证：AI 不应"从会话历史中认出 Abcfoo456"
        # 合法回答：搜索数据库没找到（引用词在回答中属于正常），或明确表示不认识
        # 非法回答：AI 说"你在之前的对话中提到了 Abcfoo456"（说明会话B的历史泄漏到了会话A）
        assert "你之前" not in ans_a and "之前提到" not in ans_a and "上一轮" not in ans_a, \
            f"会话隔离失败，会话A不应有会话B的历史上下文: {ans_a[:300]}"

    def test_no_session_id(self):
        """不带 session_id 的请求不崩溃"""
        resp = requests.post(
            f"{BASE_URL}/api/chat/stream",
            json={"message": "网络有多少作者？"},
            stream=True,
            timeout=60,
        )
        assert resp.status_code == 200

    def test_history_length_limit(self):
        """发送 25 轮对话，系统不崩溃（历史被截断）"""
        sid = f"test-long-{int(time.time())}"
        for i in range(25):
            try:
                _stream_post(f"第{i+1}轮消息", sid)
            except Exception as e:
                pytest.fail(f"第{i+1}轮崩溃: {e}")
