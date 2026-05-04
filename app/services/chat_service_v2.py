"""
Service unifié de chat qui orchestre NLP et handlers d'intent.
Remplace le gros chat_controller.py avec une architecture propre.
"""
import logging
import unicodedata
from typing import Any
from app.nlp.factory import NLPFactory
from app.nlp.base import NLPAnalyzer
from app.domain.chat import ChatQuery, IntentResult
from app.domain.intent import Intent, RANKING_INTENTS, TIME_FILTERED_INTENTS
from app.services.intent.base import IntentHandler
from app.services.intent.stock import StockHandler
from app.services.intent.machines import MachinesHandler
from app.services.intent.fournisseur import FournisseurHandler
from app.services.intent.lot_liste import LotListeHandler
from app.services.intent.machine import MachineHandler
from app.services.intent.lot_cycle_vie import LotCycleVieHandler
from app.services.intent.analyse_labo import AnalyseLaboHandler
from app.services.intent.comparaison import ComparaisonHandler
from app.services.intent.explication import ExplicationHandler
from app.services.intent.production import ProductionHandler
from app.services.intent.rendement import RendementHandler
from app.services.intent.prediction import PredictionHandler
from app.services.intent.qualite import QualiteHandler
from app.services.intent.diagnostic import DiagnosticHandler
from app.services.intent.campagne import CampagneHandler
from app.services.intent.reception import ReceptionHandler
from app.services.intent.mouvement_stock import MouvementStockHandler
from app.services.chatbot_service import ChatbotService
from app.nlp.normalizer import resolve_period

logger = logging.getLogger(__name__)


KNOWN_HUILERIES = (
    "zitouneya",
    "moulin sfax",
    "moulin sousse",
    "moulin artisanal",
)


class ChatService:
    """Service orchestrant NLP, validation, et dispatch d'intents."""
    
    def __init__(self, nlp_analyzer: NLPAnalyzer | None = None):
        self.nlp = nlp_analyzer or NLPFactory.get_instance()
        self.chatbot_service = ChatbotService()
        self._handlers = self._load_handlers()
    
    def _load_handlers(self) -> dict[Intent, IntentHandler]:
        """Charger les handlers disponibles."""
        return {
            Intent.STOCK: StockHandler(self.chatbot_service),
            Intent.MACHINES_UTILISEES: MachinesHandler(self.chatbot_service),
            Intent.FOURNISSEUR: FournisseurHandler(self.chatbot_service),
            Intent.LOT_LISTE: LotListeHandler(self.chatbot_service),
            Intent.MACHINE: MachineHandler(self.chatbot_service),
            Intent.LOT_CYCLE_VIE: LotCycleVieHandler(self.chatbot_service),
            Intent.ANALYSE_LABO: AnalyseLaboHandler(self.chatbot_service),
            Intent.PRODUCTION: ProductionHandler(self.chatbot_service),
            Intent.RENDEMENT: RendementHandler(self.chatbot_service),
            Intent.PREDICTION: PredictionHandler(),
            Intent.COMPARAISON: ComparaisonHandler(self.chatbot_service),
            Intent.EXPLICATION: ExplicationHandler(self.chatbot_service),
            Intent.QUALITE: QualiteHandler(self.chatbot_service),
            Intent.DIAGNOSTIC: DiagnosticHandler(self.chatbot_service),
            Intent.CAMPAGNE: CampagneHandler(self.chatbot_service),
            Intent.RECEPTION: ReceptionHandler(self.chatbot_service),
            Intent.MOUVEMENT_STOCK: MouvementStockHandler(self.chatbot_service),
            Intent.COMPARAISON: ComparaisonHandler(self.chatbot_service),
            Intent.EXPLICATION: ExplicationHandler(self.chatbot_service),
        }
    
    async def process_message(
        self,
        message: str,
        session_id: str,
        huilerie: str | None = None,
        enterprise_id: int | None = None,
        permissions: list[str] | None = None,
        user_is_admin: bool = False,
        extra_context: dict[str, Any] | None = None,
        auth_available: bool = True,
    ) -> dict:
        """
        Traiter un message de chat complet.
        
        Returns:
            Dict avec {intent, confidence, text, data, structured_payload, ...}
        """
        permissions = permissions or []
        
        # Step 1: NLP Analysis
        nlp_result = await self.nlp.analyze(message)
        intent = nlp_result.intention
        resolved_huilerie = nlp_result.huilerie or self._extract_huilerie_from_message(message) or huilerie
        
        logger.info(f"NLP result: intent={intent}, confidence={nlp_result.confiance}")
        
        # Step 2: Intent Override (basé sur keywords du message)
        intent = self._apply_intent_overrides(intent, message)
        
        # Step 3: RBAC Check
        from app.services.permission_service import is_intent_allowed
        if auth_available and not user_is_admin and not is_intent_allowed(intent.value, permissions):
            logger.warning(f"Permission denied for intent: {intent}")
            return {
                "intent": intent.value,
                "confidence": nlp_result.confiance,
                "text": "Accès refusé pour cet intent.",
                "data": None,
                "error": "permission_denied"
            }
        
        # Step 4: Determine period handling
        explicit_period = nlp_result.periode is not None or self._has_period_keyword(message)
        
        # Step 5: Resolve dates
        period_label = nlp_result.periode.value if nlp_result.periode else "aujourd_hui"
        start_date, end_date, period_text = resolve_period(period_label)
        
        # Step 6: Build ChatQuery
        query = ChatQuery.from_raw(
            message=message,
            session_id=session_id,
            intent=intent,
            confidence=nlp_result.confiance,
            huilerie=resolved_huilerie,
            enterprise_id=enterprise_id,
            permissions=permissions,
            period_label=period_label,
            explicit_period=explicit_period,
            start_date=start_date,
            end_date=end_date,
            extra_context=extra_context or {},
        )
        
        # Step 7: Dispatch to Handler
        try:
            handler = self._handlers.get(intent)
            if handler:
                result = await handler.handle(query)
            else:
                result = IntentResult(
                    text=f"Intent '{intent.value}' n'est pas encore implémenté.",
                    data=None
                )
        except Exception as error:
            logger.exception(f"Error handling intent {intent}: {error}")
            result = IntentResult(
                text="Une erreur s'est produite lors du traitement de votre requête.",
                data=None,
                structured_payload={"error": str(error)}
            )
        
        # Step 8: Build response
        # Exposer aussi les entités extraites par le NLP pour compatibilité
        entities = {
            "huilerie": resolved_huilerie,
            "periode": nlp_result.periode.value if nlp_result.periode else None,
            "period_label": period_label,
            "type_huile": nlp_result.type_huile,
            "variete": nlp_result.variete,
            "code_lot": nlp_result.code_lot,
            "reference_lot": nlp_result.reference_lot,
            "lot_reference": nlp_result.lot_reference,
            "campagne_annee": nlp_result.campagne_annee,
        }

        return {
            "intent": intent.value,
            "confidence": nlp_result.confiance,
            "text": result.text,
            "data": result.data,
            "structured_payload": result.structured_payload,
            "has_chart": result.has_chart(),
            "is_multi_item": result.is_multi_item(),
            "entities": entities,
        }
    
    @staticmethod
    def _apply_intent_overrides(intent: Intent, message: str) -> Intent:
        """Appliquer les overrides d'intent basés sur les keywords."""
        msg_lower = message.lower().strip()
        
        # Stock override
        stock_keywords = ["stock", "inventaire", "quantite disponible", "reserve d'olive"]
        lot_keywords = ["liste lot", "liste des lots", "lots non conformes", "tracabilite", "tous les lots"]
        
        has_stock = any(k in msg_lower for k in stock_keywords)
        has_lot = any(k in msg_lower for k in lot_keywords)
        
        if has_stock and not has_lot and intent != Intent.STOCK:
            logger.info(f"Intent override: {intent} → STOCK (stock keyword)")
            return Intent.STOCK
        
        # Lot_liste override
        lot_list_keywords = ["liste lot", "liste des lots", "tous les lots"]
        if any(k in msg_lower for k in lot_list_keywords) and intent not in (Intent.LOT_LISTE, Intent.LOT_CYCLE_VIE):
            logger.info(f"Intent override: {intent} → LOT_LISTE")
            return Intent.LOT_LISTE
        
        return intent
    
    @staticmethod
    def _has_period_keyword(message: str) -> bool:
        """Vérifier si le message mentionne explicitement une période."""
        period_keywords = [
            "aujourd", "hier", "cette semaine", "semaine derniere", 
            "ce mois", "mois dernier", "2025", "2026", "annee"
        ]
        msg_lower = message.lower()
        return any(k in msg_lower for k in period_keywords)

    @staticmethod
    def _extract_huilerie_from_message(message: str) -> str | None:
        """Reconnaître une huilerie explicitement citée dans le message."""
        normalized = unicodedata.normalize("NFD", message.lower())
        normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        normalized = " ".join(normalized.split())

        for huilerie_name in KNOWN_HUILERIES:
            if huilerie_name in normalized:
                return huilerie_name

        return None
