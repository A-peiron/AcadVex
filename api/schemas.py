from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any


class AuthorInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    name: str
    community_id: int
    research_area: str
    keywords: List[str]
    degree: int
    paper_count: int


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
