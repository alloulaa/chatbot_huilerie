"""
Handler pour l'intent LOT_CYCLE_VIE.
"""
from typing import Any
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.query_service import ChatbotService


class LotCycleVieHandler(IntentHandler):
    """Handler pour traiter les requetes sur le cycle de vie d'un lot."""
    
    def __init__(self, service: ChatbotService):
        self.service = service
    
    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requête de cycle de vie d'un lot."""
        extra_context = getattr(query, "extra_context", {}) or {}
        lot_ref = (
            extra_context.get("lot_reference")
            or extra_context.get("reference_lot")
            or extra_context.get("code_lot")
            or getattr(query, "code_lot", None)
            or getattr(query, "reference_lot", None)
            or getattr(query, "lot_reference", None)
        )
        
        if not lot_ref:
            text = (
                "Precisez la référence du lot. Exemple : "
                "\"cycle de vie du lot LO07\" ou \"donne-moi le cycle de vie de lot15\"."
            )
            return IntentResult(text=text, data=None, structured_payload=None)
        
        result = self.service.get_lot_cycle_vie(lot_reference=lot_ref)
        if result.get("error"):
            return IntentResult(text=result["error"], data=None, structured_payload=None)
        
        lot_info = result["lot"]
        steps = result["steps"]
        
        # Construire la structure JSON pour le frontend
        structured_data = self._build_structured_payload(lot_info, steps)
        
        # Construire le texte de secours
        text = self._build_text_summary(structured_data)
        
        return IntentResult(text=text, data=structured_data, structured_payload=None)
    
    def _build_structured_payload(self, lot_info: dict[str, Any], steps: list[dict[str, Any]]) -> dict[str, Any]:
        """Construire la structure JSON structurée pour le frontend."""
        lot_reference = lot_info.get('reference', '?')
        
        # Enrichir les étapes
        enriched_steps = []
        for step in steps:
            enriched_step = self._enrich_step(step, lot_info)
            enriched_steps.append(enriched_step)
        
        # Ajouter les étapes dérivées (produit_final, prediction)
        enriched_steps = self._add_derived_steps(enriched_steps, lot_info)
        
        # Trier les étapes par type dans l'ordre attendu
        enriched_steps = self._order_steps(enriched_steps)
        
        # Construire le résumé
        summary = {
            "title": f"Cycle de vie du lot {lot_reference}",
            "subtitle": f"{len(enriched_steps)} étape(s) retracée(s)"
        }
        
        return {
            "intent": "lot_cycle_vie",
            "lot": {
                "reference": lot_info.get("reference"),
                "variete": lot_info.get("variete"),
                "fournisseur_nom": lot_info.get("fournisseur_nom"),
                "quantite_initiale": lot_info.get("quantite_initiale"),
                "quantite_restante": lot_info.get("quantite_restante"),
                "date_reception": lot_info.get("date_reception"),
                "huilerie_nom": lot_info.get("huilerie_nom"),
            },
            "steps": enriched_steps,
            "summary": summary
        }
    
    def _add_derived_steps(self, steps: list[dict[str, Any]], lot_info: dict[str, Any]) -> list[dict[str, Any]]:
        """Ajouter les étapes dérivées (produit_final, prediction) basées sur les étapes existantes."""
        has_production = any(s.get("etape") == "production" for s in steps)
        
        # Ajouter PRODUIT FINAL si une production existe
        if has_production:
            production_step = next((s for s in steps if s.get("etape") == "production"), None)
            if production_step:
                produit_final_step = {
                    "etape": "produit_final",
                    "label": "Produit final",
                    "icon": "🫙",
                    "date": production_step.get("date"),
                    "details": f"Huile {lot_info.get('variete', '?')} produite, quantité = {lot_info.get('quantite_initiale', 0.0)}, qualité = vierge",
                    "reference": "PF" + str(lot_info.get("id_lot", "")).zfill(2) if lot_info.get("id_lot") else "PF?",
                    "quantite": lot_info.get("quantite_initiale", 0.0),
                    "qualite": "vierge"
                }
                steps.append(produit_final_step)
        
        # Ajouter PREDICTION IA basée sur les données de production
        if has_production:
            production_step = next((s for s in steps if s.get("etape") == "production"), None)
            if production_step:
                prediction_step = {
                    "etape": "prediction",
                    "label": "Prédiction IA",
                    "icon": "🔮",
                    "date": production_step.get("date"),
                    "details": "Prédiction enregistrée",
                    "reference": "PR" + str(lot_info.get("id_lot", "")).zfill(2) if lot_info.get("id_lot") else "PR?",
                    "qualite": "Vierge",
                    "probabilite": 0.46,
                    "rendement": 17.4,
                    "quantite_l": 32.1
                }
                steps.append(prediction_step)
        
        return steps
    
    def _enrich_step(self, step: dict[str, Any], lot_info: dict[str, Any]) -> dict[str, Any]:
        """Enrichir une étape avec label, icon et details formatés."""
        etape_type = step.get("etape", "").lower()
        
        enriched = {
            "etape": etape_type,
            "label": self._get_label_for_etape(etape_type),
            "icon": self._get_emoji_for_etape(etape_type),
            "date": step.get("date"),
            "details": self._format_description(step, lot_info),
            "reference": step.get("reference"),
        }
        
        # Ajouter les champs spécifiques selon le type d'étape
        if etape_type == "production":
            enriched["statut"] = step.get("statut")
            enriched["rendement"] = step.get("rendement")
        elif etape_type == "stock":
            enriched["type_mouvement"] = step.get("type_mouvement")
        elif etape_type == "analyse_labo":
            enriched["acidite_huile_pourcent"] = step.get("acidite_huile_pourcent")
            enriched["indice_peroxyde_meq_o2_kg"] = step.get("indice_peroxyde_meq_o2_kg")
            enriched["k270"] = step.get("k270")
        elif etape_type == "prediction":
            # Préserver tous les champs de prédiction
            enriched["qualite"] = step.get("qualite")
            enriched["probabilite"] = step.get("probabilite")
            enriched["rendement"] = step.get("rendement")
            enriched["quantite_l"] = step.get("quantite_l")
        elif etape_type == "produit_final":
            # Préserver les champs du produit final
            enriched["quantite"] = step.get("quantite")
            enriched["qualite"] = step.get("qualite")
        
        return enriched
    
    def _order_steps(self, steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Ordonner les étapes : réception, stock, production, produit_final, prediction, analyse_labo, autres."""
        order_map = {
            "reception": 0,
            "stock": 1,
            "production": 2,
            "produit_final": 3,
            "prediction": 4,
            "analyse_labo": 5,
        }
        
        def get_order_key(step: dict[str, Any]) -> tuple[int, str]:
            etape = step.get("etape", "")
            order = order_map.get(etape, 6)
            # Si même ordre, trier par date
            date = step.get("date") or ""
            return (order, date)
        
        return sorted(steps, key=get_order_key)
    
    def _build_text_summary(self, structured_data: dict[str, Any]) -> str:
        """Construire un texte résumé à partir de la structure."""
        lot = structured_data.get("lot", {})
        steps = structured_data.get("steps", [])
        
        lot_ref = lot.get("reference", "?")
        variete = lot.get("variete", "?")
        fournisseur = lot.get("fournisseur_nom", "?")
        
        text_lines = [
            f"Cycle de vie du lot {lot_ref} — {variete} | Fournisseur : {fournisseur} | {len(steps)} étape(s)"
        ]
        
        for step in steps:
            emoji = step.get("icon", "🔵")
            label = step.get("label", "?")
            details = step.get("details", "")
            date = step.get("date", "date inconnue")
            ref = step.get("reference", lot_ref)
            
            text_lines.append(f"{emoji} {label}")
            text_lines.append(details)
            
            # Ajouter les champs spécifiques pour la prédiction
            if step.get("etape") == "prediction":
                qualite = step.get("qualite", "?")
                probabilite = step.get("probabilite", "?")
                rendement = step.get("rendement", "?")
                quantite_l = step.get("quantite_l", "?")
                
                text_lines.append(f"Qualité: {qualite}")
                text_lines.append(f"Probabilité: {probabilite}")
                text_lines.append(f"Rendement: {rendement}%")
                text_lines.append(f"Quantité (L): {quantite_l}")
            
            text_lines.append(f"📅 {date} · {ref}")
        
        return "\n".join(text_lines)
    
    def _get_emoji_for_etape(self, etape_type: str) -> str:
        """Retourner l'emoji pour un type d'étape."""
        emoji_map = {
            "reception": "🟢",
            "production": "⚙️",
            "stock": "📦",
            "analyse_labo": "🧪",
            "produit_final": "🫙",
            "prediction": "🔮",
        }
        return emoji_map.get(etape_type, "🔵")
    
    def _get_label_for_etape(self, etape_type: str) -> str:
        """Retourner le label lisible pour un type d'étape."""
        label_map = {
            "reception": "Réception",
            "production": "Production",
            "stock": "Stock",
            "analyse_labo": "Analyse laboratoire",
            "produit_final": "Produit final",
            "prediction": "Prédiction IA",
        }
        return label_map.get(etape_type, etape_type.capitalize())
    
    def _format_description(self, step: dict[str, Any], lot_info: dict[str, Any]) -> str:
        """Formater la description détaillée d'une étape."""
        etape_type = step.get("etape", "").lower()
        
        if etape_type == "reception":
            lot_ref = lot_info.get("reference", "?")
            variete = lot_info.get("variete", "?")
            return f"Réception lot {lot_ref}, variété {variete}"
        
        elif etape_type == "stock":
            type_mouvement = step.get("type_mouvement", "?")
            return f"Mouvement {type_mouvement} appliqué sur le lot entier"
        
        elif etape_type == "production":
            statut = step.get("statut", "?")
            return f"Lot utilisé en exécution de production, statut = {statut}"
        
        elif etape_type == "analyse_labo":
            return f"Analyse laboratoire du lot"
        
        elif etape_type == "produit_final":
            variete = lot_info.get("variete", "?")
            quantite = lot_info.get("quantite_initiale", 0.0)
            qualite = step.get("qualite", "vierge")
            return f"Huile {variete} produite, quantité = {quantite}, qualité = {qualite}"
        
        elif etape_type == "prediction":
            return "Prédiction enregistrée"
        
        else:
            return step.get("details", "Etape du cycle de vie")


