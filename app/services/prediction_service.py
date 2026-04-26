from app.repositories.production_repository import ProductionRepository


class PredictionService:
    def __init__(self):
        self.repo = ProductionRepository()

    def predict_quality(self, lot_code: str):
        row = self.repo.lot_features(lot_code)
        if not row:
            return {"text": f"Je ne trouve pas le lot {lot_code} pour lancer une prédiction.", "data": None}
        humidite = row["humidite"]
        rendement = row["rendement"]
        if humidite <= 42 and rendement >= 18.5:
            pred = "vierge extra"
            confidence = 0.88
        elif humidite <= 46 and rendement >= 17.5:
            pred = "vierge"
            confidence = 0.79
        else:
            pred = "lampante"
            confidence = 0.72
        return {
            "text": f"La qualité prédite pour le lot {lot_code} est '{pred}' avec une confiance estimée à {round(confidence*100)} %.",
            "data": {"lot_code": lot_code, "prediction": pred, "confidence": confidence},
        }

    def predict_quantity(self, lot_code: str):
        row = self.repo.lot_features(lot_code)
        if not row:
            return {"text": f"Je ne trouve pas le lot {lot_code} pour estimer la quantité.", "data": None}
        estimate = round(row["quantite_litres"] * (1.03 if row["humidite"] < 43 else 0.97), 2)
        return {
            "text": f"La quantité estimée pour le lot {lot_code} est de {estimate} litres.",
            "data": {"lot_code": lot_code, "quantite_estimee": estimate},
        }

    def explain_prediction(self, lot_code: str):
        row = self.repo.lot_features(lot_code)
        if not row:
            return {"text": f"Je ne trouve pas le lot {lot_code} pour expliquer la prédiction.", "data": None}
        reasons = []
        if row["humidite"] >= 46:
            reasons.append("humidité élevée")
        elif row["humidite"] <= 42:
            reasons.append("humidité maîtrisée")
        if row["rendement"] >= 18.5:
            reasons.append("bon rendement")
        else:
            reasons.append("rendement moyen à faible")
        if row["qualite_classe"] == "lampante":
            reasons.append("historique réel défavorable pour des lots similaires")
        text = ", ".join(reasons)
        return {
            "text": f"La prédiction pour le lot {lot_code} est principalement influencée par : {text}.",
            "data": {"lot_code": lot_code, "factors": reasons},
        }
