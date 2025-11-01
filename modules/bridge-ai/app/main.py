from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Bridge AI", version="1.1.1")


class MessageRequest(BaseModel):
    text: str
    metadata: dict[str, Any] | None = None


class MessageResponse(BaseModel):
    reply: str


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/reply", response_model=MessageResponse)
def reply(payload: MessageRequest) -> MessageResponse:
    prompt = payload.text.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Message text must not be empty")

    default_response = os.getenv("BRIDGE_AI_DEFAULT_RESPONSE", "AI: Hello from AI")
    logger.info("Generated AI response for prompt '%s'", prompt)
    return MessageResponse(reply=default_response)
