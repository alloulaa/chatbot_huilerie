"""
Analyse rule-based enrichie pour fallback (sans API Claude).
"""
from __future__ import annotations

from typing import Any
from datetime import datetime

from app.domain.oleiculture import _grade_huile, _get_variete_profil
from app.utils.lot_helpers import (
    _safe_float, _fmt, _parse_boolish,
    _latest_by, _first_by
)


def _rule_based_explanation(lot_data: dict, user_question: str) -> str:
    """
    Analyse causale enrichie par règles expertes — FORMAT NARRATIF.
    Génère une explication narrative : "La qualité du lot est [grade] parce que [raisons avec valeurs mesurées]"
    
    Args:
        lot_data: Dictionnaire contenant toutes les données collectées
        user_question: Question de l'utilisateur (non utilisée dans l'analyse rule-based)
    
    Returns:
        str : Explication narrative structurée
    """
    lot = lot_data.get("lot") or {}
    execs = lot_data.get("executions") or []
    analyses = lot_data.get("analyses") or []
    production_outputs = lot_data.get("production_outputs") or []
    benchmark = lot_data.get("benchmark") or {}

    lot_ref = lot.get("reference", "?")
    variete = lot.get("variete") or "variété inconnue"
    primary_execution = _first_by(execs, "date_debut") or (execs[0] if execs else None)
    latest_analysis = _latest_by(analyses, "date_analyse") or (analyses[0] if analyses else None)
    final_output = _latest_by(production_outputs, "date_production") or (production_outputs[0] if production_outputs else None)
    
    # Durée de stockage (gère plusieurs schémas de colonnes)
    duree_stockage = _safe_float(lot.get("duree_stockage_jours"))
    if duree_stockage == 0:
        duree_stockage = _safe_float(lot.get("duree_stockage_avant_broyage"))
    if duree_stockage == 0:
        heures_depuis_recolte = _safe_float(lot.get("temps_depuis_recolte_heures"))
        if heures_depuis_recolte > 0:
            duree_stockage = heures_depuis_recolte / 24.0
    if duree_stockage == 0 and lot.get("date_reception") and execs:
        try:
            dr = str(lot["date_reception"])[:10]
            dp = str(execs[0].get("date_debut", ""))[:10]
            if dr and dp:
                d1 = datetime.strptime(dr, "%Y-%m-%d")
                d2 = datetime.strptime(dp, "%Y-%m-%d")
                duree_stockage = abs((d2 - d1).days)
        except Exception:
            pass

    causal_reasons: list[str] = []
    points_positifs: list[str] = []
    qualite_judgement = "moyenne"
    grade = "Non déterminé"
    production_quality = None
    analytic_grade = None

    # ── Analyse des olives à la réception ─────────────────────────────────
    acidite_olive = _safe_float(lot.get("acidite_olives_pourcent"))
    if acidite_olive > 0:
        if acidite_olive > 3.0:
            causal_reasons.append(
                f"l'acidité des olives à la réception était critique ({_fmt(acidite_olive)} %), "
                f"ce qui indique des olives blessées ou trop mûres ayant déjà subi une dégradation enzymatique importante"
            )
        elif acidite_olive > 1.5:
            causal_reasons.append(
                f"l'acidité des olives à la réception était élevée ({_fmt(acidite_olive)} %), "
                f"ce qui a risqué de dégénérer en huile classée vierge ou lampante"
            )
        else:
            points_positifs.append("l'acidité des olives à la réception était acceptable")

    maturite = _safe_float(lot.get("indice_maturite") if lot.get("indice_maturite") is not None else lot.get("maturite"))
    if maturite > 0:
        if maturite >= 5:
            causal_reasons.append(
                f"les olives étaient sur-mûres (indice {_fmt(maturite, 1)}), "
                f"ce qui a fortement réduit la teneur en polyphénols et augmenté l'acidité"
            )
        elif maturite > 3.5:
            causal_reasons.append(
                f"les olives avaient une maturité avancée (indice {_fmt(maturite, 1)}), "
                f"ce qui a diminué les polyphénols bénéfiques"
            )
        elif 1.5 <= maturite <= 3.5:
            points_positifs.append("la maturité des olives était optimale")

    if duree_stockage > 0:
        if duree_stockage > 3:
            causal_reasons.append(
                f"le temps entre la récolte et l'exécution de production a été trop large ({int(duree_stockage)} jour(s)), "
                f"permettant aux enzymes lipolytiques de dégrader les triglycérides et augmenter l'acidité"
            )
        elif duree_stockage > 1:
            causal_reasons.append(
                f"le temps entre la récolte et l'exécution de production était de {int(duree_stockage)} jour(s), "
                f"ce qui a légèrement affecté la qualité"
            )
        else:
            points_positifs.append("la trituration a été effectuée rapidement après réception")

    taux_feuilles = _safe_float(lot.get("taux_feuilles_pourcent"))
    if taux_feuilles > 0:
        if taux_feuilles > 3:
            causal_reasons.append(
                f"le taux de feuilles ({_fmt(taux_feuilles, 1)} %) était élevé, "
                f"ce qui augmente les impuretés et accélère l'oxydation enzymatique"
            )
        elif taux_feuilles > 1:
            causal_reasons.append(
                f"le taux de feuilles était de {_fmt(taux_feuilles, 1)} %, "
                f"ce qui a légèrement augmenté la charge enzymatique"
            )

    temp_malax_primary = _safe_float(primary_execution.get("temperature_malaxage")) if primary_execution else 0.0
    duree_malax_primary = _safe_float(primary_execution.get("duree_malaxage_minutes")) if primary_execution else 0.0
    presence_eau_primary = primary_execution.get("presence_ajout_eau") if primary_execution else None
    qty_eau_primary = primary_execution.get("quantite_eau_ajoutee") if primary_execution else None
    controle_temp = primary_execution.get("controle_temperature") if primary_execution else None
    type_machine = primary_execution.get("type_machine") if primary_execution else None

    # Vérifier l'absence de contrôle température et son impact direct
    if controle_temp is not None and not _parse_boolish(controle_temp) and temp_malax_primary > 0:
        causal_reasons.insert(
            0,
            f"l'absence de contrôle température lors du malaxage a laissé la température monter à {_fmt(temp_malax_primary, 1)} °C sans intervention, "
            f"ce qui explique directement l'accélération de l'oxydation et la perte de polyphénols"
        )

    # Corréler machine traditionnelle + absence de contrôle température
    if type_machine and "traditionnel" in str(type_machine).lower() and not _parse_boolish(controle_temp) and temp_malax_primary > 0:
        causal_reasons.insert(
            0,
            f"l'utilisation d'une machine {type_machine} sans système de contrôle température rend très difficile "
            f"le maintien de la température optimale, d'où les {_fmt(temp_malax_primary, 1)} °C observés"
        )

    # Signaler l'absence de lavage des olives
    lavage_effectue = lot.get("lavage_effectue")
    if lavage_effectue is not None and not _parse_boolish(lavage_effectue):
        causal_reasons.append(
            f"l'absence de lavage des olives avant trituration a conservé les résidus microbiens et lipolytiques "
            f"à la surface, accélérant l'acidification et l'oxydation"
        )

    # Si une exécution est identifiée, exploiter ses conditions comme cause de production
    if primary_execution:
        temp_malax = temp_malax_primary
        duree_malax = duree_malax_primary
        presence_eau = presence_eau_primary
        qty_eau = qty_eau_primary

        if temp_malax > 0:
            if temp_malax >= 27:
                causal_reasons.append(
                    f"la température de malaxage a atteint {_fmt(temp_malax, 1)} °C, au-dessus de la zone de confort (18-24 °C), "
                    f"ce qui accélère l'oxydation et la dégradation des composés phénoliques"
                )
            elif temp_malax > 25:
                causal_reasons.append(
                    f"la température de malaxage était de {_fmt(temp_malax, 1)} °C, légèrement trop élevée pour préserver au mieux les arômes et les polyphénols"
                )

        if duree_malax > 0:
            if duree_malax >= 50:
                causal_reasons.append(
                    f"le malaxage a duré {int(duree_malax)} min, ce qui prolonge le contact avec l'oxygène et favorise l'oxydation"
                )
            elif duree_malax > 45:
                causal_reasons.append(
                    f"le malaxage a duré {int(duree_malax)} min, légèrement au-dessus de l'optimum habituel"
                )

        if _parse_boolish(presence_eau):
            causal_reasons.append(
                f"l'ajout d'eau au malaxage" + (f" ({qty_eau} L)" if qty_eau else "") +
                " a pu entraîner une perte de polyphénols hydrophiles et une baisse de qualité organoleptique"
            )

    # Si la chaîne produit_final est connue, l'utiliser comme vérité de production
    if final_output and final_output.get("qualite"):
        production_quality = str(final_output.get("qualite")).strip()
        if production_quality:
            production_quality_low = production_quality.lower()
            if any(tok in production_quality_low for tok in ("lamp", "non comestible", "lampante")):
                qualite_judgement = "mauvaise"
                grade = "lampante"
            elif any(tok in production_quality_low for tok in ("vierge extra", "extra")):
                qualite_judgement = "bonne"
                grade = "Vierge Extra"
            elif "vierge" in production_quality_low:
                qualite_judgement = "moyenne"
                grade = "Vierge"

    methode_recolte = lot.get("methode_recolte") or lot.get("mode_recolte") or "non renseignée"
    if methode_recolte and methode_recolte.lower() not in ("non renseignée", ""):
        if any(m in methode_recolte.lower() for m in ["gaulage", "baton", "bâton", "abscission"]):
            causal_reasons.append(
                f"la récolte par {methode_recolte} a traumatisé les olives, "
                f"ce qui a activé les lipases et accéléré l'acidification"
            )

    # ── Conditions de trituration ──────────────────────────────────────────
    for ep in execs:
        etat_machine = ep.get("etat_machine", "")
        if etat_machine and "maintenance" in str(etat_machine).lower():
            causal_reasons.append(
                f"la machine utilisée était en maintenance, ce qui a compromis la qualité de la trituration"
            )

        temp_malax = _safe_float(ep.get("temperature_malaxage"))
        if temp_malax > 0:
            if temp_malax > 27:
                causal_reasons.append(
                    f"la température de malaxage était élevée ({_fmt(temp_malax, 1)} °C, dépassant le seuil critique), "
                    f"ce qui a activé les enzymes oxydatives et détruit les polyphénols bénéfiques"
                )
            elif temp_malax > 25:
                causal_reasons.append(
                    f"la température de malaxage était de {_fmt(temp_malax, 1)} °C, légèrement au-dessus de l'optimum (18-24°C)"
                )
            else:
                points_positifs.append("la température de malaxage était optimale")

        duree_malax = _safe_float(ep.get("duree_malaxage_minutes"))
        if duree_malax > 0:
            if duree_malax > 60:
                causal_reasons.append(
                    f"le malaxage a duré {int(duree_malax)} minutes, beaucoup trop long, "
                    f"ce qui a exposé l'huile trop longtemps à l'oxygène et favorisé l'oxydation"
                )
            elif duree_malax > 45:
                causal_reasons.append(
                    f"le malaxage a duré {int(duree_malax)} minutes, légèrement au-delà de l'optimum (20-45 min)"
                )
            else:
                points_positifs.append("la durée de malaxage était correcte")

        presence_eau = ep.get("presence_ajout_eau")
        if presence_eau in (1, True, "1", "oui", "yes", "true"):
            qty_eau = ep.get("quantite_eau_ajoutee")
            causal_reasons.append(
                f"l'ajout d'eau lors du malaxage" + (f" ({qty_eau} L)" if qty_eau else "")
                + " a dilué les polyphénols hydrophiles et réduit la qualité organoleptique"
            )

    # ── Analyses laboratoire ───────────────────────────────────────────────
    if analyses:
        a = analyses[0]
        acid = _safe_float(a.get("acidite_huile_pourcent"))
        perox = _safe_float(a.get("indice_peroxyde_meq_o2_kg"))
        k270 = _safe_float(a.get("k270"))
        poly = _safe_float(a.get("polphenols_mg_kg"))
        analytic_grade = _grade_huile(acid, perox, k270)
        # Déterminer le jugement sur la qualité du produit final
        if not production_quality:
            grade = analytic_grade
            if "Lampante" in grade or "lampante" in grade:
                qualite_judgement = "mauvaise"
            elif "Vierge" in grade and "Extra" not in grade:
                qualite_judgement = "moyenne"
            elif "Extra" in grade or "Vierge Extra" in grade:
                qualite_judgement = "bonne"
            else:
                qualite_judgement = "moyenne"

        if acid > 0.8:
            causal_reasons.append(
                f"l'acidité mesurée de l'huile ({_fmt(acid)} %, seuil vierge extra ≤ 0,8 %) "
                f"reflète la dégradation des triglycérides durant la production"
            )
        else:
            points_positifs.append("l'acidité de l'huile était conforme vierge extra")

        if perox > 20:
            causal_reasons.append(
                f"l'indice de peroxyde ({_fmt(perox, 1)} meq O₂/kg, seuil ≤ 20) indique une oxydation primaire, "
                f"causée par une exposition excessive à l'air ou une température de malaxage trop élevée"
            )
        else:
            points_positifs.append("le peroxyde était conforme")

        if k270 > 0.22:
            causal_reasons.append(
                f"le K270 ({_fmt(k270, 3)}, seuil ≤ 0,22) montre une oxydation secondaire "
                f"due à un malaxage trop chaud ou un stockage inadéquat"
            )

        k232 = _safe_float(a.get("k232"))
        if k232 > 0:
            if k232 > 2.5:
                causal_reasons.append(
                    f"le K232 ({_fmt(k232, 3)}) dépasse le seuil COI de 2,50, indiquant une oxydation secondaire avancée, "
                    f"causée par le malaxage prolongé à température excessive et la perte d'antioxydants"
                )
            elif k232 < 1.5:
                points_positifs.append(f"le K232 ({_fmt(k232, 3)}) était en dessous du seuil minimum, conforme")

        if poly > 0:
            if poly < 100:
                causal_reasons.append(
                    f"les polyphénols sont très faibles ({_fmt(poly, 0)} mg/kg, référence 100-800), "
                    f"ce qui signifie que l'huile a perdu ses antioxydants naturels"
                )
            elif poly < 200:
                causal_reasons.append(
                    f"les polyphénols sont faibles ({_fmt(poly, 0)} mg/kg), ce qui réduit la durée de conservation"
                )
            else:
                points_positifs.append(f"les polyphénols étaient élevés ({_fmt(poly, 0)} mg/kg)")

    # ── Croisement final : production vs analytique ───────────────────────
    mismatch_detected = False
    mismatch_note = ""
    if final_output:
        pf_ref = final_output.get("reference", "?")
        pf_id = final_output.get("id_produit", "?")
        pf_date = final_output.get("date_production", "?")
        pf_qual = (final_output.get("qualite") or "").strip()

        if pf_qual:
            pf_qual_low = pf_qual.lower()
            if any(tok in pf_qual_low for tok in ("lamp", "non comestible", "inadmissible")):
                if latest_analysis:
                    acid = _safe_float(latest_analysis.get("acidite_huile_pourcent"))
                    perox = _safe_float(latest_analysis.get("indice_peroxyde_meq_o2_kg"))
                    k270 = _safe_float(latest_analysis.get("k270"))
                    poly = _safe_float(latest_analysis.get("polphenols_mg_kg"))
                    analytic_grade = _grade_huile(acid, perox, k270)
                    if analytic_grade != "Lampante (non comestible brut)":
                        mismatch_detected = True
                        mismatch_note = (
                            f"Si les analyses labo montrent un grade différent ({analytic_grade}) "
                            f"avec acidité {_fmt(acid)} %, K270 {_fmt(k270, 3)} et polyphénols {_fmt(poly, 0)} mg/kg, "
                            f"il faut suspecter un problème de traçabilité, d'échantillonnage ou de saisie."
                        )
                    else:
                        causal_reasons.insert(
                            0,
                            f"Le produit final est enregistré comme « {pf_qual} » (réf {pf_ref}, id {pf_id}, date {pf_date}) et l'analyse labo confirme un grade lampante ; la cause la plus probable est la combinaison du délai de {_fmt(duree_stockage, 0)} jour(s), de la récolte traumatisante, du malaxage défavorable et de la faible teneur en polyphénols."
                        )
                else:
                    causal_reasons.insert(
                        0,
                        f"Le produit final est enregistré comme « {pf_qual} » (réf {pf_ref}, id {pf_id}, date {pf_date}), mais aucune analyse récente n'est disponible pour confirmer ou infirmer ce classement."
                    )
            elif any(tok in pf_qual_low for tok in ("vierge extra", "extra")):
                causal_reasons.insert(
                    0,
                    f"Le produit final est enregistré comme « {pf_qual} » (réf {pf_ref}, id {pf_id}, date {pf_date}) ; il faut vérifier que les conditions de production et l'analyse labo sont cohérentes avec ce classement."
                )

    # Si aucune cause forte n'a été trouvée, remettre la plus probable en tête
    if production_quality:
        if any(tok in production_quality.lower() for tok in ("lamp", "non comestible", "lampante")):
            qualite_judgement = "mauvaise"
            grade = "lampante"

    if causal_reasons:
        strong_markers = ("délai", "température", "malaxage", "eau", "gaulage", "acidité", "polyphénols", "lampante")
        causal_reasons.sort(key=lambda reason: 0 if any(marker in reason.lower() for marker in strong_markers) else 1)

    # ── Construction de la narration causale finale ────────────────────────
    narration_lines: list[str] = []

    # Paragraphe synthèse exigé pour le cas qualité mauvaise
    summary_line = ""
    if qualite_judgement == "mauvaise":
        factors: list[str] = []
        if duree_stockage > 0:
            factors.append(f"un délai de {int(round(duree_stockage))} jour(s) entre la récolte et l'extraction")
        if methode_recolte and methode_recolte.lower() not in ("non renseignée", ""):
            factors.append(f"une récolte par {methode_recolte}")
        if acidite_olive > 0:
            factors.append(f"une acidité des olives à la réception de {_fmt(acidite_olive)} %")
        if temp_malax_primary > 0:
            factors.append(f"une température de malaxage de {_fmt(temp_malax_primary, 1)} °C")
        if duree_malax_primary > 0:
            factors.append(f"un malaxage de {int(duree_malax_primary)} min")
        if _parse_boolish(presence_eau_primary):
            factors.append(f"un ajout de {qty_eau_primary or 0} L d'eau")

        if latest_analysis:
            acid_l = _safe_float(latest_analysis.get("acidite_huile_pourcent"))
            k270_l = _safe_float(latest_analysis.get("k270"))
            poly_l = _safe_float(latest_analysis.get("polphenols_mg_kg"))
            confirmation = (
                f"Ces conditions ont favorisé la dégradation des triglycérides et l'oxydation, "
                f"ce que confirment l'acidité de l'huile à {_fmt(acid_l)} %, "
                f"le K270 à {_fmt(k270_l, 3)} et des polyphénols à {_fmt(poly_l, 0)} mg/kg."
            )
        else:
            confirmation = "Ces conditions ont favorisé la dégradation des triglycérides et l'oxydation."

        if factors:
            summary_line = (
                f"Le lot {lot_ref} est enregistré comme lampante. La cause la plus probable est "
                + ", ".join(factors)
                + ". "
                + confirmation
            )
        else:
            summary_line = (
                f"Le lot {lot_ref} est enregistré comme lampante et la cause la plus probable est "
                f"une combinaison de facteurs de récolte et de trituration défavorables. "
                + confirmation
            )

        if mismatch_detected and mismatch_note:
            summary_line += " " + mismatch_note
    
    # Ligne d'ouverture
    narration_lines.append(
        f"La qualité du produit final extrait à partir du lot {lot_ref} est {qualite_judgement} ({grade}) parce que :"
    )
    narration_lines.append("")

    if summary_line:
        narration_lines.append(summary_line)
        narration_lines.append("")
    
    # Énumérer les raisons causales
    filtered_reasons = [
        reason for reason in causal_reasons
        if "incohérence de données" not in reason.lower()
    ]
    if filtered_reasons:
        for reason in filtered_reasons:
            narration_lines.append(f"• {reason},")
    else:
        narration_lines.append("• données insuffisantes pour identifier les causes spécifiques.")
    
    narration_lines.append("")
    
    # Résumé des points positifs s'il y en a
    if points_positifs:
        narration_lines.append("Cependant, quelques points positifs :")
        for point in points_positifs:
            narration_lines.append(f"• {point}")
        narration_lines.append("")
    
    # Recommandations
    narration_lines.append("Recommandations pour améliorer la qualité :")
    recs = []
    
    causal_str = " ".join(causal_reasons)
    if "délai" in causal_str or "temps" in causal_str:
        recs.append("• Réduire le temps entre la récolte et l'exécution de production à moins de 24h")
    if "température" in causal_str and "malaxage" in causal_str:
        recs.append("• Ramener la température de malaxage à 18-24°C pour préserver les polyphénols")
    if "malaxage" in causal_str and ("long" in causal_str or "prolongé" in causal_str):
        recs.append("• Limiter la durée de malaxage à 25-35 minutes")
    if "eau" in causal_str:
        recs.append("• Réduire ou éliminer l'ajout d'eau lors du malaxage")
    if "machine" in causal_str and "maintenance" in causal_str:
        recs.append("• Vérifier et entretenir les machines avant la prochaine campagne")
    if "acidité des olives" in causal_str or "maturité" in causal_str or "récolte" in causal_str:
        methode_lower = str(methode_recolte or "").lower()
        if any(m in methode_lower for m in ("gaulage", "baton", "bâton")):
            recs.append("• Améliorer la qualité à la récolte : éviter le gaulage, trier les olives abîmées")
        else:
            recs.append("• Renforcer le tri à la récolte et limiter les olives abîmées avant trituration")
    
    if recs:
        for rec in recs[:3]:  # Top 3 recommendations
            narration_lines.append(rec)
    else:
        narration_lines.append("• Maintenir les pratiques actuelles qui donnent de bons résultats")

    return "\n".join(narration_lines)
