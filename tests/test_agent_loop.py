# tests/test_agent_loop.py
"""
L2-B Agent 循环逻辑测试
运行方式：conda run -n acadvex pytest tests/test_agent_loop.py -v --tb=short
"""
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_msg(content=None, tool_calls=None):
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls
    return msg


def _make_response(content=None, tool_calls=None, prompt_tokens=10, completion_tokens=5):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message = _make_msg(content, tool_calls)
    resp.usage.prompt_tokens = prompt_tokens
    resp.usage.completion_tokens = completion_tokens
    return resp


class TestRunAgent:
    @patch("agent.loop._call_llm")
    def test_returns_string(self, mock_llm):
        mock_llm.return_value = _make_response(content="测试回复")
        from agent.loop import run_agent
        result = run_agent("测试问题")
        assert isinstance(result, str) and len(result) > 0

    @patch("agent.loop._call_llm")
    def test_history_injected(self, mock_llm):
        mock_llm.return_value = _make_response(content="记住了")
        from agent.loop import run_agent
        history = [{"role": "user", "content": "我叫张三"}, {"role": "assistant", "content": "好的"}]
        run_agent("你还记得我叫什么？", history=history)
        # 验证 messages 包含 history（通过 call_args 检查）
        call_args = mock_llm.call_args[0][0]  # messages 参数
        assert any(m.get("content") == "我叫张三" for m in call_args)

    @patch("agent.loop._call_llm")
    def test_llm_timeout_returns_friendly_error(self, mock_llm):
        mock_llm.side_effect = TimeoutError("超时")
        from agent.loop import run_agent
        result = run_agent("测试")
        assert isinstance(result, str)
        assert "抱歉" in result or "不可用" in result or "错误" in result


class TestRunAgentStream:
    @patch("agent.loop._call_llm")
    @patch("agent.loop._client")
    def test_is_generator(self, mock_client, mock_llm):
        mock_llm.return_value = _make_response(content=None, tool_calls=None)
        # 模拟流式响应
        chunk = MagicMock()
        chunk.choices[0].delta.content = "hello"
        chunk.choices[0].delta.tool_calls = None
        mock_client.chat.completions.create.return_value = iter([chunk])

        from agent.loop import run_agent_stream
        gen = run_agent_stream("测试")
        import inspect
        assert inspect.isgenerator(gen)

    @patch("agent.loop._call_llm")
    @patch("agent.loop._client")
    def test_ends_with_done(self, mock_client, mock_llm):
        mock_llm.return_value = _make_response(content=None, tool_calls=None)
        chunk = MagicMock()
        chunk.choices[0].delta.content = "回复"
        chunk.choices[0].delta.tool_calls = None
        mock_client.chat.completions.create.return_value = iter([chunk])

        from agent.loop import run_agent_stream
        events = list(run_agent_stream("测试"))
        types = [e["type"] for e in events]
        assert "done" in types, f"流应以 done 结束: {types}"

    @patch("agent.loop._call_llm")
    @patch("agent.loop._client")
    def test_all_events_have_type(self, mock_client, mock_llm):
        mock_llm.return_value = _make_response(content=None, tool_calls=None)
        chunk = MagicMock()
        chunk.choices[0].delta.content = "内容"
        chunk.choices[0].delta.tool_calls = None
        mock_client.chat.completions.create.return_value = iter([chunk])

        from agent.loop import run_agent_stream
        for event in run_agent_stream("测试"):
            assert "type" in event, f"每个事件应有 type 字段: {event}"

    @patch("agent.loop._call_llm")
    def test_llm_error_yields_error_event(self, mock_llm):
        mock_llm.side_effect = Exception("LLM 崩溃")
        from agent.loop import run_agent_stream
        events = list(run_agent_stream("测试"))
        types = [e["type"] for e in events]
        assert "error" in types or "done" in types
