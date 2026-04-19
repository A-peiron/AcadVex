# agent/graph.py
import os
from typing import TypedDict
from openai import OpenAI
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from agent.prompts import SYSTEM_PROMPT
from agent.tools import get_openai_schemas, dispatch_tool

load_dotenv()

_client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

MAX_ITER = 5


# ── State 定义 ──────────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: list      # OpenAI 格式消息列表（plain dict，JSON 可序列化）
    skill: str          # 当前激活的 Skill（Day 8 填充，这里暂时写死）
    iter_count: int     # 已迭代次数，防止死循环


# ── 节点定义 ────────────────────────────────────────────────────────────

def skill_router_node(state: AgentState) -> dict:
    from agent.skills import route_skill
    last_user_msg = next(
        (m["content"] for m in reversed(state["messages"]) if m["role"] == "user"),
        "",
    )
    return {"skill": route_skill(last_user_msg)}


# def llm_node(state: AgentState) -> dict:
#     """LLM 推理节点：调 DeepSeek，把响应追加到 messages"""
#     tools = get_openai_schemas()
#     response = _client.chat.completions.create(
#         model="deepseek-chat",
#         messages=state["messages"],
#         tools=tools,
#     )
#     msg = response.choices[0].message

#     # ChatCompletionMessage 对象 → plain dict（SqliteSaver 要求 JSON 可序列化）
#     msg_dict: dict = {"role": "assistant", "content": msg.content}
#     if msg.tool_calls:
#         msg_dict["tool_calls"] = [
#             {
#                 "id": tc.id,
#                 "type": "function",
#                 "function": {
#                     "name": tc.function.name,
#                     "arguments": tc.function.arguments,
#                 },
#             }
#             for tc in msg.tool_calls
#         ]

#     return {
#         "messages": state["messages"] + [msg_dict],
#         "iter_count": state["iter_count"] + 1,
#     }

def llm_node(state: AgentState) -> dict:
    from agent.skills import get_skill_tools, get_skill_prompt
    tools = get_skill_tools(state["skill"])
    # print(f"[DEBUG] skill={state['skill']}, tools={[t['function']['name'] for t in tools]}")

    # 用 Skill 专属 system prompt 替换通用 prompt
    skill_messages = [
        {"role": "system", "content": get_skill_prompt(state["skill"])},
        *[m for m in state["messages"] if m["role"] != "system"],
    ]

    response = _client.chat.completions.create(
        model="deepseek-chat",
        messages=skill_messages,
        tools=tools,
    )
    msg = response.choices[0].message

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
    for tc in last_msg.get("tool_calls", []):
        result = dispatch_tool(tc["function"]["name"], tc["function"]["arguments"])
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
    g.add_edge("tools", "llm")   # 工具执行完，回到 llm_node 继续

    return g


# 模块级别编译，全局复用（SqliteSaver 保存到 memory/ 目录）
_checkpointer = SqliteSaver.from_conn_string("memory/checkpoints.sqlite")
_app = _build_graph().compile(checkpointer=_checkpointer)


# ── 对外接口 ─────────────────────────────────────────────────────────────

def run_agent_graph(user_message: str, session_id: str = "default") -> str:
    """LangGraph 版 ReAct 循环，接口与 run_agent() 一致"""
    initial_state: AgentState = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        "skill":      "",
        "iter_count": 0,
    }
    config = {"configurable": {"thread_id": session_id}}
    result = _app.invoke(initial_state, config)

    last = result["messages"][-1]
    return last.get("content") or "抱歉，处理超时，请重新提问。"


if __name__ == "__main__":
    import sys
    question = " ".join(sys.argv[1:]) or "Author 42 和 Author 88 的合作潜力是多少？"
    print(f"\n问题：{question}\n")
    answer = run_agent_graph(question)
    print(f"回答：{answer}\n")
