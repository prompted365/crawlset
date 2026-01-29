from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import json

from ...extractors.requesty_client import RequestyClient, RequestyError

router = APIRouter()

class ToolDef(BaseModel):
    type: str
    function: Dict[str, Any]

class ToolChatRequest(BaseModel):
    messages: List[Dict[str, Any]]
    tools: Optional[List[ToolDef]] = None
    tool_choice: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None

@router.post("/stream")
async def tool_chat_stream(req: ToolChatRequest):
    try:
        client = RequestyClient()
    except RequestyError as e:
        raise HTTPException(status_code=500, detail=str(e))

    payload: Dict[str, Any] = {"stream": True}
    if req.tools is not None:
        payload["tools"] = [t.model_dump() for t in req.tools]
    if req.tool_choice is not None:
        payload["tool_choice"] = req.tool_choice
    if req.temperature is not None:
        payload["temperature"] = req.temperature
    if req.max_tokens is not None:
        payload["max_tokens"] = req.max_tokens
    if req.top_p is not None:
        payload["top_p"] = req.top_p

    async def event_generator():
        try:
            async for chunk in client.chat_completion_stream(
                messages=req.messages,
                model=req.model,
                **payload,
            ):
                yield f"data: {chunk}\n\n"
        except Exception as ex:  # noqa: BLE001
            err = json.dumps({"error": str(ex)})
            yield f"data: {err}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")