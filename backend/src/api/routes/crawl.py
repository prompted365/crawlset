from fastapi import APIRouter

router = APIRouter()

from pydantic import BaseModel
from typing import Optional, Dict, Any
from ...parser.trafilatura_parser import parse_html
from ...extractors.requesty_client import RequestyClient, RequestyError

class CrawlRequest(BaseModel):
    url: str
    use_playwright: Optional[bool] = None
    # Optional structured extraction using JSON schema
    extract_schema: Optional[Dict[str, Any]] = None  # JSON Schema dict
    schema_name: Optional[str] = "PageExtract"
    model: Optional[str] = None  # Requesty model alias/name

@router.post("/")
async def crawl_and_extract(req: CrawlRequest):
    # Lazy import — playwright only available in worker images
    from ...crawler.browser import fetch_page
    html = await fetch_page(req.url, use_playwright=req.use_playwright)
    parsed = parse_html(req.url, html)

    if req.extract_schema:
        # Use Requesty Structured Outputs via response_format json_schema (OpenAI-compatible)
        try:
            client = RequestyClient()
        except RequestyError as e:
            # Return parsed content but note extraction unavailable
            return {"url": req.url, "parsed": parsed, "extraction_error": str(e)}

        system = (
            "You are an information extraction system. Produce JSON that strictly matches the provided JSON schema. "
            "If a field is unknown, use null or an empty list as appropriate."
        )
        user = (
            f"Extract structured data from this page. URL: {req.url}\n\n"
            f"CONTENT:\n{parsed.get('text','')}"
        )
        payload_extra = {
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": req.schema_name or "PageExtract",
                    "strict": True,
                    "schema": req.extract_schema,
                },
            }
        }
        resp = await client.chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            model=req.model,
            **payload_extra,
        )
        return {"url": req.url, "parsed": parsed, "extracted": resp}

    return {"url": req.url, "parsed": parsed}
