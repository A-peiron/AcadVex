# agent/graph.py
import os
import json
from typing import TypedDict, Generator
from openai import OpenAI
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langfuse import Langfuse

from agent.prompts import SYSTEM_PROMPT
from agent.tools import get_openai_schemas, dispatch_tool
from agent.utils.logger import logger

load_dotenv()

_client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

_langfuse = Langfuse(
    public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
    secret_key=os.environ["LANGFUSE_SECRET_KEY"],
    host=os.environ["LANGFUSE_BASE_URL"],
)

MAX_ITER = 8


# ── State 定义 ──────────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: list      # OpenAI 格式消息列表（plain dict，JSON 可序列化）
    skill: str          # 当前激活的 Skill
    iter_count: int     # 已迭代次数，防止死循环


# ── 节点定义 ────────────────────────────────────────────────────────────

def skill_router_node(state: AgentState) -> dict:
    from agent.skills import route_skill
    last_user_msg = next(
        (m["content"] for m in reversed(state["messages"]) if m["role"] == "user"),
        "",
    )
    return {"skill": route_skill(last_user_msg)}


def llm_node(state: AgentState) -> dict:
    from agent.skills import get_skill_tools, get_skill_prompt
    tools = get_skill_tools(state["skill"])

    # 用 Skill 专属 system prompt 替换通用 prompt
    skill_messages = [
        {"role": "system", "content": get_skill_prompt(state["skill"])},
        *[m for m in state["messages"] if m["role"] != "system"],
    ]

    generation = _langfuse.trace(name="llm_node").generation(
        name=f"llm_call_{state['iter_count']}",
        model="deepseek-chat",
        input=skill_messages,
    )

    try:
        response = _client.chat.completions.create(
            model="deepseek-chat",
            messages=skill_messages,
            tools=tools,
            timeout=30.0,
        )
    except Exception as e:
        logger.error("llm_failed", error=str(e))
        generation.end(output=f"error: {e}")
        raise

    msg = response.choices[0].message
    generation.end(
        output=msg.content or str(msg.tool_calls),
        usage={"input": response.usage.prompt_tokens, "output": response.usage.completion_tokens},
    )

    msg_dict: dict = {"role": "assistant", "content": msg.content}
    if msg.tool_calls:
        msg_dict["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]

    return {
        "messages": state["messages"] + [msg_dict],
        "iter_count": state["iter_count"] + 1,
    }


def tool_node(state: AgentState) -> dict:
    """工具执行节点：执行 messages 最后一条 assistant 消息里的所有 tool_calls"""
    last_msg = state["messages"][-1]
    tool_results = []
    trace = _langfuse.trace(name="tool_node")
    for tc in last_msg.get("tool_calls", []):
        fn_name = tc["function"]["name"]
        fn_args = tc["function"]["arguments"]
        span = trace.span(name=f"tool_{fn_name}", input=fn_args)
        logger.info("tool_call", tool=fn_name)
        try:
            result = dispatch_tool(fn_name, fn_args)
            logger.info("tool_success", tool=fn_name)
        except Exception as e:
            logger.error("tool_failed", tool=fn_name, error=str(e))
            result = json.dumps({"error": str(e)}, ensure_ascii=False)
        span.end(output=result)
        tool_results.append({
            "role": "tool",
            "tool_call_id": tc["id"],
            "content": result,
        })
    return {"messages": state["messages"] + tool_results}


# ── 条件边 ──────────────────────────────────────────────────────────────

def should_continue(state: AgentState) -> str:
    """判断是继续工具调用还是结束"""
    if state["iter_count"] >= MAX_ITER:
        return "end"
    last_msg = state["messages"][-1]
    if last_msg.get("tool_calls"):
        return "continue"
    return "end"


# ── 图构建与编译 ─────────────────────────────────────────────────────────

def _build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    g.add_node("skill_router", skill_router_node)
    g.add_node("llm",          llm_node)
    g.add_node("tools",        tool_node)

    g.set_entry_point("skill_router")
    g.add_edge("skill_router", "llm")
    g.add_conditional_edges(
        "llm",
        should_continue,
        {"continue": "tools", "end": END},
    )
    g.add_edge("tools", "llm")

    return g


# 模块级别编译，全局复用（SqliteSaver 保存到 memory/ 目录）
_checkpointer = SqliteSaver.from_conn_string("memory/checkpoints.sqlite")
_app = _build_graph().compile(checkpointer=_checkpointer)


# ── 对外接口 ─────────────────────────────────────────────────────────────

def _make_state(user_message: str, session_id: str) -> AgentState:
    """读取 checkpoint 历史，追加新 user 消息，返回完整 state。"""
    config = {"configurable": {"thread_id": session_id}}
    checkpoint = _checkpointer.get(config)

    if checkpoint and checkpoint.get("channel_values", {}).get("messages"):
        # 已有历史：在原有 messages 基础上追加新 user 消息
        history = checkpoint["channel_values"]["messages"]
        # 过滤掉旧的 system prompt，重新插入最新版本
        history_no_system = [m for m in history if m.get("role") != "system"]
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history_no_system,
            {"role": "user", "content": user_message},
        ]
        skill = checkpoint["channel_values"].get("skill", "")
    else:
        # 首次对话
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ]
        skill = ""

    return AgentState(messages=messages, skill=skill, iter_count=0)


def run_agent_graph(user_message: str, session_id: str = "default") -> str:
    """LangGraph 版 ReAct 循环（非流式）"""
    config = {"configurable": {"thread_id": session_id}}
    state = _make_state(user_message, session_id)

    logger.info("agent_start", message=user_message, session_id=session_id)
    try:
        result = _app.invoke(state, config)
        last = result["messages"][-1]
        answer = last.get("content") or "抱歉，处理超时，请重新提问。"
        logger.info("agent_complete", session_id=session_id)
        return answer
    except Exception as e:
        logger.error("agent_failed", error=str(e), session_id=session_id)
        return f"系统错误：{e}"


def run_agent_graph_stream(user_message: str, session_id: str = "default") -> Generator:
    """LangGraph 版 ReAct 循环（流式），yield SSE 事件 dict"""
    config = {"configurable": {"thread_id": session_id}}
    state = _make_state(user_message, session_id)

    logger.info("agent_stream_start", message=user_message, session_id=session_id)
    try:
        # 记录上一个 llm 节点输出的 tool_calls，供 tools 节点使用
        _pending_tool_names: list[str] = []

        for chunk in _app.stream(state, config, stream_mode="updates"):
            for node_name, state_update in chunk.items():

                if node_name == "llm":
                    messages = state_update.get("messages", [])
                    if not messages:
                        continue
                    last_msg = messages[-1]
                    if last_msg.get("role") != "assistant":
                        continue

                    tool_calls = last_msg.get("tool_calls")
                    if tool_calls:
                        # 有工具调用，通知前端并缓存工具名
                        _pending_tool_names = [tc["function"]["name"] for tc in tool_calls]
                        for name in _pending_tool_names:
                            yield {"type": "tool_call", "name": name}
                    else:
                        # 纯文本回复，逐字符模拟流式输出
                        content = last_msg.get("content") or ""
                        for char in content:
                            yield {"type": "token", "content": char}
                        _pending_tool_names = []

                elif node_name == "tools":
                    # tool 执行完毕，用缓存的工具名再通知一次（可选，让前端知道工具完成）
                    # 这里不额外 yield，避免重复；_pending_tool_names 已在 llm 节点通知过
                    _pending_tool_names = []

        yield {"type": "done"}
        logger.info("agent_stream_complete", session_id=session_id)

    except Exception as e:
        logger.error("agent_stream_failed", error=str(e), session_id=session_id)
        yield {"type": "error", "content": f"系统错误：{e}"}
        yield {"type": "done"}


if __name__ == "__main__":
    import sys
    question = " ".join(sys.argv[1:]) or "Author 42 和 Author 88 的合作潜力是多少？"
    print(f"\n问题：{question}\n")
    answer = run_agent_graph(question)
    print(f"回答：{answer}\n")
