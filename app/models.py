from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    user_id: int = 1
    session_id: str = "demo-session"
    jwt_token: str | None = None
    token: str | None = None


class ChatResponse(BaseModel):
    intent: str
    confidence: float
    entities: dict
    response: str
    data: dict | list | None = None
    applied_scope: dict | None = None
    applied_permissions: list | None = None
