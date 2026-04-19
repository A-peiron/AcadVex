from pydantic import BaseModel
from typing import List


class AuthorInfo(BaseModel):
    id: int
    name: str
    community_id: int
    research_area: str
    keywords: List[str]
    degree: int
    paper_count: int


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
