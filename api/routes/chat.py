import asyncio
from fastapi import APIRouter
from api.schemas import ChatRequest, ChatResponse
from agent.loop import run_agent

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(None, run_agent, req.message)
    return ChatResponse(answer=answer)


import json
from fastapi.responses import StreamingResponse
from agent.loop import run_agent_stream


@router.post("/chat/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    # 把 run_agent_stream 生成器包装成 SSE 格式
    def event_generator():
        for event in run_agent_stream(req.message):
            # 每个 event 是 dict，序列化成 JSON 字符串放进 SSE data 字段
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",       # 禁止缓存，确保实时推送
            "X-Accel-Buffering": "no",         # 禁止 Nginx 缓冲（生产环境必须）
        },
    )
