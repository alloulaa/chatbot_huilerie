import logging
import os
import unicodedata
from typing import Any

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - defensive startup guard
    httpx = None

from app.database import get_db_connection

logger = logging.getLogger(__name__)


INTENT_MODULE_MAP = {
    "stock": "STOCK",
    "production": "GUIDE_PRODUCTION",
    "machine": "MACHINES",
    "machines_utilisees": "MACHINES",
    "rendement": "GUIDE_PRODUCTION",
    "prediction": "GUIDE_PRODUCTION",
    "qualite": "LOTS_TRAÇABILITE",
    "diagnostic": "LOTS_TRAÇABILITE",
    "fournisseur": "LOTS_TRAÇABILITE",
    "lot_cycle_vie": "LOTS_TRAÇABILITE",
    "lot_liste": "LOTS_TRAÇABILITE",
    "analyse_labo": "LOTS_TRAÇABILITE",
    "mouvement_stock": "STOCK_MOUVEMENT",
    "reception": "RECEPTION",
    "campagne": "CAMPAGNE_OLIVES",
    "comparaison": "CAMPAGNE_OLIVES",
    "explication": "LOTS_TRAÇABILITE",
}


def _backend_base_urls() -> list[str]:
    custom = os.getenv("JAVA_BACKEND_URL")
    urls = []
    if custom:
        urls.append(custom.rstrip("/"))
    urls.append("http://localhost:8000")
    # Preserve order and remove duplicates.
    return list(dict.fromkeys(urls))


def get_user_permissions(jwt_token: str) -> dict[str, Any] | None:
    if httpx is None:
        logger.warning("httpx is not installed. RBAC backend calls are skipped.")
        return {
            "utilisateur": {},
            "permissions": [],
            "_auth_unavailable": True,
        }

    headers = {"Authorization": f"Bearer {jwt_token}"}

    for base_url in _backend_base_urls():
        endpoint = f"{base_url}/api/auth/me"
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(endpoint, headers=headers)

            if response.status_code == 200:
                payload = response.json()
                if isinstance(payload, dict):
                    payload["_auth_source"] = base_url
                return payload

            if response.status_code in {401, 403}:
                logger.info("JWT rejected by backend on %s", endpoint)
                return None

            logger.warning("Auth backend returned status %s on %s", response.status_code, endpoint)
        except Exception as exc:
            logger.warning("Auth backend unreachable on %s: %s", endpoint, exc)

    # Backend unavailable: do not block chatbot.
    return {
        "utilisateur": {},
        "permissions": [],
        "_auth_unavailable": True,
    }


def is_admin(auth_data: dict[str, Any] | None) -> bool:
    if not auth_data:
        return False
    user = auth_data.get("utilisateur") or {}
    profil = str(user.get("profil") or "")
    return profil.lower() == "admin"


def is_intent_allowed(intent: str, permissions: list[dict[str, Any]] | None) -> bool:
    module = INTENT_MODULE_MAP.get(intent)
    if module is None:
        return True

    def _normalize(value: str) -> str:
        decomposed = unicodedata.normalize("NFD", value)
        without_marks = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
        return without_marks.lower()

    for perm in permissions or []:
        perm_module = str(perm.get("module") or "")
        if _normalize(perm_module) == _normalize(module):
            return bool(perm.get("canRead") if perm.get("canRead") is not None else perm.get("can_read"))

    return False


def is_huilerie_allowed(
    huilerie_name: str | None, 
    enterprise_id: int | None,
    jwt_token: str | None = None
) -> bool:
    """Check if a huilerie name belongs to a given enterprise by querying the database.
    
    Returns True if:
    - No huilerie specified (no restriction)
    - No enterprise_id provided (cannot validate)
    - Huilerie found and belongs to enterprise
    
    Returns False if:
    - Huilerie explicitly does NOT belong to enterprise
    """
    if not huilerie_name or not enterprise_id:
        return True
    
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Query: check if huilerie with given name belongs to the enterprise
        query = """
            SELECT h.id_huilerie, h.entreprise_id
            FROM huilerie h
            WHERE LOWER(h.nom) = LOWER(%s)
            LIMIT 1
        """
        cursor.execute(query, (huilerie_name,))
        row = cursor.fetchone()
        
        if not row:
            # Huilerie not found in database
            logger.warning("Huilerie '%s' not found in database", huilerie_name)
            return False
        
        huilerie_enterprise_id = row.get("entreprise_id")
        if huilerie_enterprise_id != enterprise_id:
            # Huilerie found but belongs to different enterprise
            logger.warning(
                "Huilerie '%s' (enterprise %s) access denied for user in enterprise %s",
                huilerie_name, huilerie_enterprise_id, enterprise_id
            )
            return False
        
        # Huilerie belongs to user's enterprise
        return True
        
    except Exception as exc:
        logger.exception("Error validating huilerie '%s' against enterprise %s: %s", 
                         huilerie_name, enterprise_id, exc)
        # On error, allow the query to proceed (fail open for robustness)
        return True
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def get_user_huilerie(auth_data: dict[str, Any] | None, jwt_token: str | None = None) -> str | None:
    if httpx is None:
        logger.warning("httpx is not installed. Huilerie lookup is skipped.")
        return None

    if not auth_data:
        return None

    if is_admin(auth_data):
        user = auth_data.get("utilisateur") or {}
        if user.get("huilerieId") is None:
            return None

    user = auth_data.get("utilisateur") or {}
    huilerie_id = user.get("huilerieId")
    if huilerie_id is None:
        return None

    headers = {}
    if jwt_token:
        headers["Authorization"] = f"Bearer {jwt_token}"

    for base_url in _backend_base_urls():
        endpoint = f"{base_url}/api/huileries/{huilerie_id}"
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(endpoint, headers=headers)
            if response.status_code == 200:
                payload = response.json()
                if isinstance(payload, dict):
                    return payload.get("nom") or payload.get("name") or payload.get("libelle")
            logger.warning("Huilerie endpoint status %s on %s", response.status_code, endpoint)
        except Exception as exc:
            logger.warning("Failed to fetch huilerie name on %s: %s", endpoint, exc)

    return None


def get_user_enterprise_id(auth_data: dict[str, Any] | None) -> int | None:
    if not auth_data:
        return None

    user = auth_data.get("utilisateur") or {}
    candidates = [
        user.get("entrepriseId"),
        user.get("entreprise_id"),
        user.get("companyId"),
        user.get("societeId"),
    ]

    for value in candidates:
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue

    return None