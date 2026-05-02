# tests/test_e2e_tools.py
"""
L3-B 工具调用链端到端测试（需后端运行在 localhost:8000）
运行方式：conda run -n acadvex pytest tests/test_e2e_tools.py -v --tb=short
"""
import sys
import json
import time
import re
import pytest
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:8000"


def _stream_full(message: str, session_id: str = None) -> tuple[str, list[str]]:
    """
    发送 SSE 请求，返回 (assistant文本, tool_call_names列表)
    """
    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id
    resp = requests.post(
        f"{BASE_URL}/api/chat/stream",
        json=payload,
        stream=True,
        timeout=90,
    )
    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}"
    text = ""
    tools_called = []
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
            elif event["type"] == "tool_call":
                tools_called.append(event.get("name", ""))
        except Exception:
            pass
    return text, tools_called


@pytest.fixture(scope="module", autouse=True)
def check_server():
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code != 200:
            pytest.skip("后端服务未运行，跳过 L3 测试")
    except Exception:
        pytest.skip("后端服务未运行，跳过 L3 测试")


class TestSingleToolCall:
    def test_author_influence(self):
        """Author 42 的影响力 → 触发 get_author_influence 工具"""
        text, tools = _stream_full("Author 42 的影响力如何？")
        assert len(text) > 0, "回复不应为空"
        assert any(k in text for k in ["度中心性", "Degree", "degree", "betweenness", "Betweenness", "影响力"]), \
            f"回复应包含影响力指标: {text[:200]}"

    def test_network_stats(self):
        """网络规模 → 触发 get_network_stats 或 get_network_overview"""
        text, tools = _stream_full("这个学术网络有多少作者？")
        assert "4057" in text or "4,057" in text, f"应包含作者数4057: {text[:200]}"

    def test_community_analysis(self):
        """分析 AI 社群 → 触发 analyze_community 工具"""
        text, tools = _stream_full("分析一下 AI 社群的概况")
        assert len(text) > 50, f"回复过短: {text[:200]}"


class TestToolChain:
    def test_search_then_influence(self):
        """搜索 Jiawei Han 并分析影响力 → 多工具链"""
        text, tools = _stream_full("帮我找 Jiawei Han，并分析他的影响力")
        assert "Jiawei" in text or "Han" in text or "1015" in text, \
            f"应识别出 Jiawei Han: {text[:200]}"
        # 工具调用顺序：search_author 应在 get_author_influence 之前
        if "search_author" in tools and "get_author_influence" in tools:
            assert tools.index("search_author") < tools.index("get_author_influence"), \
                f"工具调用顺序错误: {tools}"


class TestErrorRecovery:
    def test_nonexistent_author(self):
        """不存在的作者 → 返回友好提示，系统不崩溃"""
        text, tools = _stream_full("Author 999999 的影响力如何？")
        assert len(text) > 0, "系统不应崩溃"
        assert any(k in text for k in ["不存在", "找不到", "没有", "无法", "错误", "未找到"]), \
            f"应返回友好错误提示: {text[:200]}"

    def test_recovery_after_error(self):
        """错误恢复后系统仍正常工作"""
        sid = f"recovery-{int(time.time())}"
        _stream_full("Author 999999 的影响力？", session_id=sid)
        time.sleep(1)
        text, _ = _stream_full("网络有多少作者？", session_id=sid)
        assert "4057" in text or "4,057" in text, f"错误后系统应恢复正常: {text[:200]}"


class TestStreamCompleteness:
    def test_response_not_truncated(self):
        """回复应完整，不被截断（修复 Bug: 流式 tool_calls）"""
        text, tools = _stream_full("希望有更详细的使用示例")
        assert len(text) > 100, f"回复过短，可能被截断: {text[:200]}"
        # 不应以冒号结尾（截断标志）
        stripped = text.strip()
        assert not stripped.endswith("：") and not stripped.endswith(":"), \
            f"回复疑似被截断（以冒号结尾）: {stripped[-50:]}"

    def test_tool_call_result_included(self):
        """工具调用结果应包含在最终回复中"""
        text, tools = _stream_full("帮我找做图神经网络的学者")
        if tools:  # 如果触发了工具调用
            assert len(text) > 50, f"触发工具调用后，回复应包含工具结果: {text[:200]}"
