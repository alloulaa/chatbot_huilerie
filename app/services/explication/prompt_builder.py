"""
Construction du prompt expert pour Claude basé sur les données collectées.
"""
from __future__ import annotations

from typing import Any

from app.domain.oleiculture import _grade_huile, _get_variete_profil
from app.utils.lot_helpers import _safe_float, _fmt, _parse_boolish


def _build_expert_prompt(lot_data: dict, user_question: str) -> str:
    """
    Construit un prompt expert détaillé pour Claude basé sur toutes les données du lot.
    
    Args:
        lot_data: Dictionnaire contenant toutes les données collectées
        user_question: Question de l'utilisateur
    
    Returns:
        str : Prompt formaté prêt pour l'API Anthropic
    """
    lot = lot_data.get("lot") or {}
    execs = lot_data.get("executions") or []
    execution_steps = lot_data.get("execution_steps") or []
    production_outputs = lot_data.get("production_outputs") or []
    analyses = lot_data.get("analyses") or []
    movements = lot_data.get("stock_movements") or []
    benchmark = lot_data.get("benchmark") or {}
    huilerie_info = lot_data.get("huilerie_info") or {}

    variete = lot.get("variete") or "inconnue"
    variete_profil = _get_variete_profil(variete)

    # Calcul du grade COI
    grade = "Non déterminé"
    if analyses:
        a = analyses[0]
        grade = _grade_huile(
            _safe_float(a.get("acidite_huile_pourcent")),
            _safe_float(a.get("indice_peroxyde_meq_o2_kg")),
            _safe_float(a.get("k270"))
        )

    # Durée de stockage estimée (gère plusieurs schémas de colonnes)
    duree_stockage = _safe_float(lot.get("duree_stockage_jours"))
    if duree_stockage == 0:
        duree_stockage = _safe_float(lot.get("duree_stockage_avant_broyage"))
    if duree_stockage == 0:
        heures_depuis_recolte = _safe_float(lot.get("temps_depuis_recolte_heures"))
        if heures_depuis_recolte > 0:
            duree_stockage = heures_depuis_recolte / 24.0
    if duree_stockage == 0 and lot.get("date_reception") and execs:
        try:
            from datetime import datetime
            dr = str(lot["date_reception"])[:10]
            dp = str(execs[0].get("date_debut", ""))[:10]
            if dr and dp:
                d1 = datetime.strptime(dr, "%Y-%m-%d")
                d2 = datetime.strptime(dp, "%Y-%m-%d")
                duree_stockage = abs((d2 - d1).days)
        except Exception:
            pass

    lines = [
        "Tu es un expert en oléiculture et en technologie d'extraction d'huile d'olive.",
        "Tu dois analyser TOUTES les données disponibles sur ce lot et produire une explication",
        "causale complète, intelligente et pédagogique en français.",
        "Ne recopie pas les informations brutes du lot en ouverture : va directement à l'analyse,",
        "avec un langage humain, naturel et concret.",
        "",
        f"## Question de l'utilisateur\n{user_question}",
        "",
        "## Données collectées",
        "",
        "### 1. Informations du lot",
        f"- Référence : {lot.get('reference', '?')}",
        f"- Variété d'olive : {variete}",
        f"- Fournisseur : {lot.get('fournisseur_nom', 'inconnu')}",
        f"- Huilerie : {lot.get('huilerie_nom', 'inconnue')}",
        f"- Région fournisseur : {lot.get('fournisseur_region') or lot.get('region') or 'non renseignée'}",
        f"- Région du lot/verger : {lot.get('region') or lot.get('zone') or lot.get('localite') or lot.get('gouvernorat') or 'non renseignée'}",
        f"- Type de sol : {lot.get('type_sol') or lot.get('sol') or 'non renseigné'}",
        f"- Altitude : {lot.get('altitude') or 'non renseignée'}",
        f"- Méthode de récolte : {lot.get('methode_recolte') or lot.get('mode_recolte') or 'non renseignée'}",
        f"- Date de récolte : {lot.get('date_recolte') or 'non renseignée'}",
        f"- Date de réception à l'huilerie : {lot.get('date_reception') or 'non renseignée'}",
        f"- Délai récolte→trituration estimé : {int(round(duree_stockage))} jour(s)" if duree_stockage else "- Délai récolte→trituration : non calculable",
        f"- Quantité initiale : {_fmt(lot.get('quantite_initiale'), 0)} kg",
        f"- Quantité restante : {_fmt(lot.get('quantite_restante'), 0)} kg",
        f"- Acidité des olives à la réception : {_fmt(lot.get('acidite_olives_pourcent'), 2)} %" if lot.get('acidite_olives_pourcent') else "- Acidité des olives à la réception : non renseignée",
        f"- Indice de maturité : {_fmt(lot.get('indice_maturite') or lot.get('maturite'), 1)}" if (lot.get('indice_maturite') or lot.get('maturite')) else "- Indice de maturité : non renseigné",
        f"- Humidité des olives : {_fmt(lot.get('humidite_olives') or lot.get('humidite_pourcent'), 1)} %" if (lot.get('humidite_olives') or lot.get('humidite_pourcent')) else "",
        f"- Temps depuis récolte : {_fmt(lot.get('temps_depuis_recolte_heures'), 0)} h" if lot.get('temps_depuis_recolte_heures') else "",
        f"- Lavage effectué : {'Oui' if lot.get('lavage_effectue') else 'Non'}" if lot.get('lavage_effectue') is not None else "",
        f"- Taux de feuilles : {_fmt(lot.get('taux_feuilles_pourcent'), 1)} %" if lot.get('taux_feuilles_pourcent') else "",
        f"- Taux d'impuretés : {_fmt(lot.get('taux_impuretes'), 2)} %" if lot.get('taux_impuretes') else "",
        f"- Température de stockage avant trituration : {_fmt(lot.get('temperature_stockage'), 1)} °C" if lot.get('temperature_stockage') else "",
        f"- Observations sur le lot : {lot.get('notes') or lot.get('observations') or 'aucune'}",
    ]

    # Profil variétal
    if variete_profil:
        lines += [
            "",
            f"### 2. Profil agronomique de la variété {variete}",
            f"- Acidité naturelle caractéristique : {variete_profil.get('acidite_naturelle', 'inconnue')}",
            f"- Teneur en polyphénols caractéristique : {variete_profil.get('polyphenols', 'inconnue')}",
            f"- Sensibilité au gel : {variete_profil.get('sensibilite_gel', 'inconnue')}",
            f"- Époque de maturité optimale : {variete_profil.get('maturite_optimale', 'inconnue')}",
        ]

    # Étapes de production
    if execs:
        lines += ["", "### 3. Étapes de production / Conditions de trituration"]
        for i, ep in enumerate(execs, 1):
            lines.append(f"\n**Exécution {i} — {ep.get('reference', '?')}**")
            lines.append(f"- Statut : {ep.get('statut', 'inconnu')}")
            lines.append(f"- Date début : {ep.get('date_debut', '?')}")
            lines.append(f"- Date fin : {ep.get('date_fin_reelle', '?') or 'en cours'}")
            if ep.get("controle_temperature") is not None:
                lines.append(f"- Contrôle température : {'Oui' if ep.get('controle_temperature') else 'Non'}")
            rend = ep.get("rendement")
            if rend is not None:
                lines.append(f"- Rendement obtenu : {_fmt(rend, 2)} %")
            if ep.get("nom_machine"):
                lines.append(f"- Machine(s) utilisée(s) : {ep.get('nom_machine')}")
            if ep.get("categorie_machine"):
                lines.append(f"- Catégorie machine : {ep.get('categorie_machine')}")
            if ep.get("etat_machine"):
                lines.append(f"- État de la machine : {ep.get('etat_machine')}")
            if ep.get("machine_marque"):
                lines.append(f"- Marque machine : {ep.get('machine_marque')} ({ep.get('machine_annee', '?')})")
            if ep.get("temperature_malaxage") is not None:
                lines.append(f"- Température de malaxage : {_fmt(ep.get('temperature_malaxage'), 1)} °C")
            if ep.get("duree_malaxage_minutes") is not None:
                lines.append(f"- Durée de malaxage : {int(_safe_float(ep.get('duree_malaxage_minutes')))} min")
            if ep.get("vitesse_malaxage") is not None:
                lines.append(f"- Vitesse de malaxage : {ep.get('vitesse_malaxage')} tr/min")
            presence_eau = ep.get("presence_ajout_eau")
            if presence_eau is not None:
                ajout_str = "Oui" if presence_eau in (1, True, "1", "oui", "yes", "true") else "Non"
                lines.append(f"- Ajout d'eau : {ajout_str}")
                if ep.get("quantite_eau_ajoutee"):
                    lines.append(f"  → Quantité eau : {ep.get('quantite_eau_ajoutee')} L")
            if ep.get("pression_centrifugation") is not None:
                lines.append(f"- Pression centrifugation : {ep.get('pression_centrifugation')}")
            if ep.get("temperature_centrifugation") is not None:
                lines.append(f"- Température centrifugation : {_fmt(ep.get('temperature_centrifugation'), 1)} °C")
            if ep.get("perte_extraction") is not None:
                lines.append(f"- Perte extraction : {_fmt(ep.get('perte_extraction'), 2)} %")
            if ep.get("notes") or ep.get("observations") or ep.get("commentaires"):
                lines.append(f"- Notes : {ep.get('notes') or ep.get('observations') or ep.get('commentaires')}")
        if execution_steps:
            lines += ["", "- Détail des étapes de l'exécution :"]
            for step in execution_steps:
                step_name = step.get("etape_nom") or step.get("code_etape") or "Étape inconnue"
                lines.append(
                    f"  • {step.get('etape_ordre', '?')}. {step_name}"
                    + (f" — {step.get('etape_description')}" if step.get("etape_description") else "")
                )
                if step.get("nom_machine"):
                    lines.append(f"    → Machine : {step.get('nom_machine')}")
                if step.get("categorie_machine"):
                    lines.append(f"    → Catégorie : {step.get('categorie_machine')}")
                if step.get("etat_machine"):
                    lines.append(f"    → État machine : {step.get('etat_machine')}")
        if production_outputs:
            lines += ["", "- Produit final obtenu :"]
            for pf in production_outputs:
                lines.append(
                    f"  • {pf.get('reference', '?')} : {pf.get('nom_produit') or 'Produit final'}"
                    f" | qualité = {pf.get('qualite') or 'N/D'}"
                    f" | quantité = {_fmt(pf.get('quantite_produite'), 1)} L"
                )
                if pf.get("qualite"):
                    lines.append(
                        f"    → En clair, la qualité finale est {pf.get('qualite')}, donc la chaîne de production a dégradé l'huile malgré un grade labo plus favorable."
                    )
    else:
        lines += ["", "### 3. Étapes de production", "Aucune exécution de production enregistrée."]

    # Analyses laboratoire
    if analyses:
        lines += ["", "### 4. Résultats laboratoire"]
        for i, al in enumerate(analyses, 1):
            lines.append(f"\n**Analyse {i} — {al.get('date_analyse', '?')}**")
            acid = _safe_float(al.get("acidite_huile_pourcent"))
            perox = _safe_float(al.get("indice_peroxyde_meq_o2_kg"))
            k270 = _safe_float(al.get("k270"))
            k232 = _safe_float(al.get("k232"))
            poly = _safe_float(al.get("polphenols_mg_kg"))

            # Grade calculé
            g = _grade_huile(acid, perox, k270)
            lines.append(f"- **Grade COI calculé : {g}**")
            lines.append("- Interprétation : le grade COI est calculé à partir des paramètres de l'huile analysée (acidité, peroxyde, K270), pas à partir de l'acidité des olives à la réception.")
            lines.append(f"- Acidité libre : {_fmt(acid)} % (seuil vierge extra ≤ 0,8 %)")
            lines.append(f"- Indice de peroxyde : {_fmt(perox, 1)} meq O₂/kg (seuil ≤ 20)")
            lines.append(f"- K270 : {_fmt(k270, 3)} (seuil ≤ 0,22)")
            if k232 > 0:
                lines.append(f"- K232 : {_fmt(k232, 3)} (seuil 1,5-2,50)")
            if poly > 0:
                lines.append(f"- Polyphénols : {_fmt(poly, 0)} mg/kg (référence 100-800, idéal >200)")
            for extra_f in ["delta_k", "humidite_huile", "impuretes_huile", "couleur", "odeur",
                             "gout", "saveur", "amertume", "ardence", "defauts",
                             "panel_test_score", "classification_panel", "tocopherols"]:
                if al.get(extra_f) is not None and al.get(extra_f) != 0:
                    lines.append(f"- {extra_f.replace('_', ' ').capitalize()} : {al.get(extra_f)}")
    else:
        lines += ["", "### 4. Résultats laboratoire", "Aucune analyse enregistrée."]

    # Benchmark
    if benchmark and benchmark.get("nb_lots_total", 0) > 0:
        lines += [
            "", "### 5. Comparaison avec les autres lots de l'huilerie",
            f"(Basé sur {benchmark['nb_lots_total']} autre(s) lot(s))",
            f"- Acidité moyenne de l'huilerie : {_fmt(benchmark.get('avg_acidite', 0))} %",
            f"- Peroxyde moyen : {_fmt(benchmark.get('avg_peroxyde', 0), 1)}",
            f"- K270 moyen : {_fmt(benchmark.get('avg_k270', 0), 3)}",
        ]
        if benchmark.get("avg_polyphenols", 0) > 0:
            lines.append(f"- Polyphénols moyens : {_fmt(benchmark.get('avg_polyphenols', 0), 0)} mg/kg")
        if benchmark.get("avg_rendement", 0) > 0:
            lines.append(f"- Rendement moyen de l'huilerie : {_fmt(benchmark.get('avg_rendement', 0), 1)} %")

    # Huilerie
    if huilerie_info:
        region_h = huilerie_info.get("region") or huilerie_info.get("gouvernorat") or huilerie_info.get("zone")
        if region_h:
            lines += ["", f"### 6. Région de l'huilerie : {region_h}"]
        for f in ["capacite_traitement", "type_presse", "systeme_extraction", "nb_centrifugeuses"]:
            if huilerie_info.get(f):
                lines.append(f"- {f.replace('_', ' ').capitalize()} : {huilerie_info[f]}")

    # Mouvements stock
    if movements:
        lines += ["", "### 7. Mouvements de stock liés au lot"]
        for mv in movements[:5]:
            lines.append(
                f"- {mv.get('type_mouvement', '?')} le {mv.get('date_mouvement', '?')}"
                + (f" — {mv.get('commentaire', '')}" if mv.get("commentaire") else "")
            )

    lines += [
        "",
        "## Instructions pour ta réponse",
        "",
        "Génère une analyse experte, structurée en sections claires avec des titres markdown (##, ###).",
        "Utilise des emojis indicateurs (🔴 critique, 🟡 attention, 🟢 ok, ✅ conforme, ❌ non conforme).",
        "",
        "Tu DOIS obligatoirement :",
        "1. **Identifier et expliquer TOUS les facteurs** qui influencent la qualité, le rendement et la quantité,",
        "   en croisant les données : conditions des olives × paramètres de trituration × résultats labo × comparaison benchmark.",
        "2. **Expliquer les mécanismes biochimiques/physiques** : pourquoi ce paramètre affecte cette caractéristique.",
        "3. **Quantifier l'écart au benchmark** quand les données le permettent.",
        "4. **Contextualiser selon la variété** si le profil variétal est connu.",
        "5. **Donner des recommandations concrètes** pour améliorer la qualité au prochain lot.",
        "6. Terminer par une **conclusion synthétique** avec les 3 leviers d'amélioration prioritaires.",
        "",
        "Si une donnée manque, signale-la brièvement mais ne t'y attarde pas.",
        "Réponds UNIQUEMENT en français, de façon experte mais accessible.",
    ]

    return "\n".join(l for l in lines if l is not None)
