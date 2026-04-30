from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    message: str
    user_id: int = 1
    session_id: str = "demo-session"
    jwt_token: str | None = None
    token: str | None = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: str = "text"
    message: str
    intent: str
    confidence: float
    entities: dict
    response: str
    options: list[str] | None = None
    chart_type: str | None = None
    data: dict | list | None = None
    applied_scope: dict = Field(default_factory=dict)
    applied_permissions: list | None = None
    selected_option: str | None = None
    pending_choice: bool = False
