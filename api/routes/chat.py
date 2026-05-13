import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from api.schemas import ChatRequest, ChatResponse
from agent.graph import run_agent_graph, run_agent_graph_stream
from api.middleware.rate_limit import limiter

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(request: Request, req: ChatRequest) -> ChatResponse:
    import asyncio
    session_id = req.session_id or "default"
    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(None, run_agent_graph, req.message, session_id)
    return ChatResponse(answer=answer)


@router.post("/chat/stream")
@limiter.limit("20/minute")
def chat_stream(request: Request, req: ChatRequest) -> StreamingResponse:
    session_id = req.session_id or "default"

    def event_generator():
        for event in run_agent_graph_stream(req.message, session_id):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
