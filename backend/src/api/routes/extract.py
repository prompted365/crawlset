from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import json

from ...extractors.requesty_client import RequestyClient, RequestyError

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    # Optional Requesty/OpenAI-compatible params
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None

@router.post("/chat")
async def extract_chat(req: ChatRequest) -> Dict[str, Any]:
    try:
        client = RequestyClient()
        payload: Dict[str, Any] = {}
        if req.temperature is not None:
            payload["temperature"] = req.temperature
        if req.max_tokens is not None:
            payload["max_tokens"] = req.max_tokens
        if req.top_p is not None:
            payload["top_p"] = req.top_p
        resp = await client.chat_completion(
            messages=[m.model_dump() for m in req.messages],
            model=req.model,
            **payload,
        )
        return resp
    except RequestyError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/stream")
async def extract_chat_stream(req: ChatRequest):
    try:
        client = RequestyClient()
    except RequestyError as e:
        raise HTTPException(status_code=500, detail=str(e))

    async def event_generator():
        try:
            async for chunk in client.chat_completion_stream(
                messages=[m.model_dump() for m in req.messages],
                model=req.model,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                top_p=req.top_p,
            ):
                # Forward chunks as server-sent events
                yield f"data: {chunk}\n\n"
        except Exception as ex:  # noqa: BLE001
            # Send an error event
            err = json.dumps({"error": str(ex)})
            yield f"data: {err}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
