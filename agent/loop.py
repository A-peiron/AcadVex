# AcadVex/agent/loop.py

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

from agent.prompts import SYSTEM_PROMPT
from agent.tools import get_openai_schemas, dispatch_tool

load_dotenv()

_client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

from langfuse import Langfuse

_langfuse = Langfuse(
    public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
    secret_key=os.environ["LANGFUSE_SECRET_KEY"],
    host=os.environ["LANGFUSE_BASE_URL"],
)


MAX_ITER = 5


def run_agent(user_message: str) -> str:
    """
    ReAct 主循环。
    输入用户自然语言，输出 Agent 最终回答。
    """
    trace = _langfuse.trace(
        name="chat_request",
        input={"message": user_message},
    )

    messages = [
        {"role": "system",  "content": SYSTEM_PROMPT},
        {"role": "user",    "content": user_message},
    ]
    tools = get_openai_schemas()

    for i in range(MAX_ITER):
        generation = trace.generation(
            name=f"llm_call_{i}",
            model="deepseek-chat",
            input=messages,
        )

        response = _client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
        )
        msg = response.choices[0].message

        generation.end(
            output=msg.content or str(msg.tool_calls),
            usage={
                "input":  response.usage.prompt_tokens,
                "output": response.usage.completion_tokens,
            },
        )

        messages.append(msg)

        if not msg.tool_calls:
            trace.update(output=msg.content)
            return msg.content

        for call in msg.tool_calls:
            span = trace.span(
                name=f"tool_{call.function.name}",
                input=call.function.arguments,
            )
            result = dispatch_tool(call.function.name, call.function.arguments)
            span.end(output=result)

            messages.append({
                "role":         "tool",
                "tool_call_id": call.id,
                "content":      result,
            })

    trace.update(output="超时")
    return "抱歉，处理超时，请重新提问或换一种描述方式。"


def run_agent_stream(user_message: str):
    """
    ReAct 流式版本，返回生成器。
    每次 yield 一个 dict，类型有三种：
      {"type": "tool_call", "name": "工具名"}
      {"type": "token",     "content": "文字片段"}
      {"type": "done"}
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_message},
    ]
    tools = get_openai_schemas()

    for _ in range(MAX_ITER):
        # ── 非流式跑工具调用阶段 ──────────────────────────────────────
        # 工具调用的 arguments 是完整 JSON，流式拼接容易出错，这里用非流式
        response = _client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
        )
        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            # 没有工具调用：进入流式最终回答阶段
            break

        # 有工具调用：yield 状态消息，执行工具，继续循环
        for call in msg.tool_calls:
            yield {"type": "tool_call", "name": call.function.name}
            result = dispatch_tool(call.function.name, call.function.arguments)
            messages.append({
                "role":         "tool",
                "tool_call_id": call.id,
                "content":      result,
            })
    else:
        # 超过 MAX_ITER 还没结束
        yield {"type": "token", "content": "抱歉，处理超时，请重新提问。"}
        yield {"type": "done"}
        return

    # ── 流式最终回答阶段 ──────────────────────────────────────────────
    # 重新发一次请求，这次开启 stream=True
    stream = _client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield {"type": "token", "content": delta.content}

    yield {"type": "done"}


if __name__ == "__main__":
    import sys
    question = " ".join(sys.argv[1:]) or "Author 42 和 Author 88 的合作潜力是多少？"
    print(f"\n问题：{question}\n")
    answer = run_agent(question)
    print(f"回答：{answer}\n")
