"""
Helper pour extraire et valider l'authentification.
"""
from dataclasses import dataclass
from typing import Any

from app.services.permission_service import (
    get_user_enterprise_id,
    get_user_huilerie,
    get_user_permissions,
    is_admin,
)


@dataclass
class AuthContext:
    """Contexte d'authentification extrait et validé."""
    jwt_token: str | None = None
    is_admin: bool = False
    huilerie: str | None = None
    enterprise_id: int | None = None
    permissions: list[str] | None = None
    auth_available: bool = False
    error: str | None = None


def resolve_auth(jwt: str | None) -> AuthContext:
    """
    Extraire et valider le contexte d'authentification.
    
    Args:
        jwt: Token JWT optionnel
        
    Returns:
        AuthContext avec les données d'auth ou les erreurs
    """
    if not jwt:
        return AuthContext(auth_available=False)
    
    # Valider le JWT
    auth_data = get_user_permissions(jwt)
    if auth_data is None:
        return AuthContext(
            jwt_token=jwt,
            auth_available=False,
            error="Token invalide ou expiré."
        )
    
    # Extraire les champs
    user_is_admin = is_admin(auth_data)
    user_huilerie = get_user_huilerie(auth_data, jwt)
    user_enterprise_id = get_user_enterprise_id(auth_data)
    applied_perms = auth_data.get("permissions", [])
    
    return AuthContext(
        jwt_token=jwt,
        is_admin=user_is_admin,
        huilerie=user_huilerie,
        enterprise_id=user_enterprise_id,
        permissions=applied_perms,
        auth_available=True,
    )
