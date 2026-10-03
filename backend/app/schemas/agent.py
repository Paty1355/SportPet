from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.questionnaire import QuestionOut


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class AgentResponse(BaseModel):
    reply: str
    memories_used: list[str] = []
    question: QuestionOut | None = None  # set while the training questionnaire is in progress


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    content: str
    created_at: datetime
