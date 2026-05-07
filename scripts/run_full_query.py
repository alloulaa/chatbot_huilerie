import os, sys
sys.path.insert(0, os.getcwd())
from app.database import get_db_connection

huilerie='ma3sra'
query = '''
SELECT
    m.nom_machine,
    m.reference AS machine_ref,
    COALESCE(u.nb_executions, 0) AS nb_executions,
    COALESCE(u.rendement_moyen, 0) AS rendement_moyen,
    COALESCE(u.total_produit, 0) AS total_produit
FROM machine m
JOIN huilerie h ON h.id_huilerie = m.huilerie_id
LEFT JOIN (
    SELECT
        et.machine_id,
        COUNT(DISTINCT ep.id_execution_production) AS nb_executions,
        AVG(ep.rendement) AS rendement_moyen,
        SUM(COALESCE(pf.quantite_produite, 0)) AS total_produit
    FROM etape_production et
    JOIN guide_production gp ON gp.id_guide_production = et.guide_production_id
    JOIN execution_production ep ON ep.guide_production_id = gp.id_guide_production
    LEFT JOIN produit_final pf ON pf.execution_production_id = ep.id_execution_production
    JOIN lot_olives lo ON lo.id_lot = ep.lot_olives_id
    JOIN huilerie h2 ON h2.id_huilerie = lo.huilerie_id
    WHERE et.machine_id IS NOT NULL AND LOWER(h2.nom) = LOWER(%s)
    GROUP BY et.machine_id ) u ON u.machine_id = m.id_machine
WHERE 1=1
ORDER BY m.nom_machine ASC
'''
params = (huilerie,)
conn = get_db_connection()
cursor = conn.cursor(dictionary=True)
cursor.execute(query, params)
rows = cursor.fetchall() or []
print('rows:', len(rows))
for r in rows[:50]:
    print(r)

cursor.close()
conn.close()
