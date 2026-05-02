"""
Routes API principales - implémentation propre avec ChatService.
Remplace le monolithe chat_controller.py.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
import logging

from app.core.db import get_db_connection
from app.services.auth_service import verify_token
from app.services.chat_service_v2 import ChatService
from app.repositories.user_repository import UserRepository
from app.repositories.huilerie_repository import HuilerieRepository

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    message: str
    huilerie: str | None = None


class ChatResponse(BaseModel):
    intent: str
    confidence: float
    text: str
    data: list | None = None
    structured_payload: dict | None = None
    has_chart: bool = False
    is_multi_item: bool = False


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: Request,
    body: ChatMessage,
):
    """
    Endpoint principal de chat.
    
    Valide les permissions, analyse le message via NLP, 
    dispatch au handler approprié, retourne le résultat.
    """
    try:
        # Step 1: Auth
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        user = verify_token(token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Step 2: Get user context
        db = get_db_connection()
        user_repo = UserRepository(db)
        huilerie_repo = HuilerieRepository(db)
        
        user_data = user_repo.get_by_email(user["email"])
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user_data.get("id_user")
        user_huilerie = user_data.get("huilerie")
        user_is_admin = user_data.get("is_admin", False)
        enterprise_id = user_data.get("entreprise_id")
        permissions = user_data.get("permissions") or []
        
        # Step 3: Validate huilerie belongs to user's enterprise
        requested_huilerie = body.huilerie or user_huilerie
        if requested_huilerie:
            huilerie_data = huilerie_repo.get_by_name(requested_huilerie)
            if not huilerie_data:
                raise HTTPException(status_code=404, detail=f"Huilerie '{requested_huilerie}' not found")
            
            h_enterprise = huilerie_data.get("entreprise_id")
            if h_enterprise != enterprise_id:
                logger.warning(
                    f"User {user_id} attempted access to huilerie {requested_huilerie} "
                    f"from enterprise {h_enterprise}, but belongs to {enterprise_id}"
                )
                raise HTTPException(status_code=403, detail="Access denied to this huilerie")
        
        # Step 4: Process message via ChatService
        chat_service = ChatService()
        session_id = request.headers.get("X-Session-ID", "default")
        
        result = await chat_service.process_message(
            message=body.message,
            session_id=session_id,
            huilerie=requested_huilerie,
            enterprise_id=enterprise_id,
            permissions=permissions,
            user_is_admin=user_is_admin,
        )
        
        return ChatResponse(
            intent=result["intent"],
            confidence=result["confidence"],
            text=result["text"],
            data=result.get("data"),
            structured_payload=result.get("structured_payload"),
            has_chart=result.get("has_chart", False),
            is_multi_item=result.get("is_multi_item", False),
        )
        
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Chat endpoint error")
        raise HTTPException(status_code=500, detail="Internal server error") from error
