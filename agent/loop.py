# AcadVex/agent/loop.py

import os
import json
from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from agent.prompts import SYSTEM_PROMPT
from agent.tools import get_openai_schemas, dispatch_tool
from agent.utils.logger import logger

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

MAX_ITER = 10


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    before_sleep=lambda s: logger.warning(
        "llm_retry", attempt=s.attempt_number, error=str(s.outcome.exception())
    ),
)
def _call_llm(messages, tools):
    return _client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
        timeout=30.0,
    )


def run_agent(user_message: str, history: list = None) -> str:
    logger.info("agent_start", message=user_message)
    trace = _langfuse.trace(name="chat_request", input={"message": user_message})
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    tools = get_openai_schemas()

    try:
        for i in range(MAX_ITER):
            logger.info("llm_call", iteration=i)
            generation = trace.generation(name=f"llm_call_{i}", model="deepseek-chat", input=messages)
            try:
                response = _call_llm(messages, tools)
            except Exception as e:
                logger.error("llm_failed", iteration=i, error=str(e))
                generation.end(output=f"error: {e}")
                trace.update(output=f"error: {e}")
                return f"抱歉，AI 服务暂时不可用：{e}"

            msg = response.choices[0].message
            generation.end(
                output=msg.content or str(msg.tool_calls),
                usage={"input": response.usage.prompt_tokens, "output": response.usage.completion_tokens},
            )
            messages.append(msg)

            if not msg.tool_calls:
                logger.info("agent_complete", iterations=i+1)
                trace.update(output=msg.content)
                return msg.content

            for call in msg.tool_calls:
                logger.info("tool_call", tool=call.function.name, args=call.function.arguments)
                span = trace.span(name=f"tool_{call.function.name}", input=call.function.arguments)
                try:
                    result = dispatch_tool(call.function.name, call.function.arguments)
                    logger.info("tool_success", tool=call.function.name)
                except Exception as e:
                    logger.error("tool_failed", tool=call.function.name, error=str(e))
                    result = json.dumps({"error": str(e)}, ensure_ascii=False)
                span.end(output=result)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

        logger.warning("agent_timeout", iterations=MAX_ITER)
        trace.update(output="超时")
        return "抱歉，处理超时，请重新提问或换一种描述方式。"

    except Exception as e:
        logger.error("agent_failed", error=str(e))
        trace.update(output=f"error: {e}")
        return f"系统错误：{e}"


def run_agent_stream(user_message: str, history: list = None):
    trace = _langfuse.trace(name="chat_stream_request", input={"message": user_message})
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 添加历史对话
    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": user_message})
    tools = get_openai_schemas()

    try:
        for i in range(MAX_ITER):
            generation = trace.generation(name=f"llm_call_{i}", model="deepseek-chat", input=messages)
            try:
                response = _call_llm(messages, tools)
            except Exception as e:
                logger.error("llm_failed", iteration=i, error=str(e))
                generation.end(output=f"error: {e}")
                yield {"type": "error", "content": f"AI 服务暂时不可用：{e}"}
                yield {"type": "done"}
                return

            msg = response.choices[0].message
            generation.end(
                output=msg.content or str(msg.tool_calls),
                usage={"input": response.usage.prompt_tokens, "output": response.usage.completion_tokens},
            )
            messages.append(msg)

            if not msg.tool_calls:
                messages.pop()
                stream_generation = trace.generation(name=f"llm_stream_{i}", model="deepseek-chat", input=messages)
                try:
                    stream = _client.chat.completions.create(
                        model="deepseek-chat",
                        messages=messages,
                        tools=tools,
                        stream=True,
                        timeout=60.0,
                    )
                    full_content = ""
                    total_tokens = 0
                    # 按 index 合并流式 tool_call 片段
                    tool_calls_map: dict = {}
                    for chunk in stream:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            full_content += delta.content
                            total_tokens += 1
                            yield {"type": "token", "content": delta.content}
                        if delta.tool_calls:
                            for tc in delta.tool_calls:
                                idx = tc.index
                                if idx not in tool_calls_map:
                                    tool_calls_map[idx] = {
                                        "id": tc.id or "",
                                        "type": "function",
                                        "function": {"name": tc.function.name or "", "arguments": ""},
                                    }
                                if tc.id:
                                    tool_calls_map[idx]["id"] = tc.id
                                if tc.function.name:
                                    tool_calls_map[idx]["function"]["name"] = tc.function.name
                                if tc.function.arguments:
                                    tool_calls_map[idx]["function"]["arguments"] += tc.function.arguments
                    collected_tool_calls = [tool_calls_map[k] for k in sorted(tool_calls_map)]
                except Exception as e:
                    logger.error("stream_failed", error=str(e))
                    yield {"type": "error", "content": f"生成回复时出错：{e}"}
                    yield {"type": "done"}
                    return

                stream_generation.end(
                    output=full_content or str(collected_tool_calls),
                    usage={"input": response.usage.prompt_tokens, "output": total_tokens},
                )

                # 如果流式阶段出现了 tool_calls，继续 ReAct 循环
                if collected_tool_calls:
                    messages.append({
                        "role": "assistant",
                        "content": full_content or None,
                        "tool_calls": collected_tool_calls,
                    })
                    # 处理工具调用
                    for call in collected_tool_calls:
                        fn = call["function"]
                        yield {"type": "tool_call", "name": fn["name"]}
                        span = trace.span(name=f"tool_{fn['name']}", input=fn["arguments"])
                        try:
                            result = dispatch_tool(fn["name"], fn["arguments"])
                        except Exception as e:
                            logger.error("tool_failed", tool=fn["name"], error=str(e))
                            result = json.dumps({"error": str(e)}, ensure_ascii=False)
                        span.end(output=result)
                        messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
                    # 不 return，继续下一轮循环生成最终回复
                    continue
                else:
                    # 纯文本回复，结束
                    messages.append({"role": "assistant", "content": full_content})
                    trace.update(output=full_content)
                    yield {"type": "done"}
                    return

            if not msg.tool_calls:
                continue
            for call in msg.tool_calls:
                yield {"type": "tool_call", "name": call.function.name}
                span = trace.span(name=f"tool_{call.function.name}", input=call.function.arguments)
                try:
                    result = dispatch_tool(call.function.name, call.function.arguments)
                except Exception as e:
                    logger.error("tool_failed", tool=call.function.name, error=str(e))
                    result = json.dumps({"error": str(e)}, ensure_ascii=False)
                span.end(output=result)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

        trace.update(output="超时")
        yield {"type": "error", "content": "抱歉，处理超时，请重新提问。"}
        yield {"type": "done"}

    except Exception as e:
        logger.error("agent_failed", error=str(e))
        trace.update(output=f"error: {e}")
        yield {"type": "error", "content": f"系统错误：{e}"}
        yield {"type": "done"}


if __name__ == "__main__":
    import sys
    question = " ".join(sys.argv[1:]) or "Author 42 和 Author 88 的合作潜力是多少？"
    print(f"\n问题：{question}\n")
    answer = run_agent(question)
    print(f"回答：{answer}\n")
