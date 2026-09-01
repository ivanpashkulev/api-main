from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = Field(default_factory=list)
