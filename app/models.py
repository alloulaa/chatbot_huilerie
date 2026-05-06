from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    user_id: int = Field(1, alias="userId")
    session_id: str = Field("demo-session", alias="sessionId")
    jwt_token: str | None = Field(None, alias="jwtToken")
    token: str | None = None
    prediction_payload: dict | None = Field(None, alias="predictionPayload")


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
