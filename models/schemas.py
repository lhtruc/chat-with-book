from typing import List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    book_id: str
    query: str
    llm_provider: Optional[str] = "deepseek"



class SourceCitation(BaseModel):
    chapter_number: Optional[int] = None
    chunk_id: Optional[str] = None
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceCitation] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
