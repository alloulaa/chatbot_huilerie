import os, sys
sys.path.insert(0, os.getcwd())
from app.database import get_db_connection

huilerie='ma3sra'
start_date='2026-05-07'
end_date='2026-05-07'

query = '''
SELECT
    et.machine_id,
    COUNT(DISTINCT ep.id_execution_production) AS nb_exec,
    AVG(ep.rendement) AS avg_rend,
    SUM(COALESCE(pf.quantite_produite,0)) AS total_prod
FROM etape_production et
JOIN guide_production gp ON gp.id_guide_production = et.guide_production_id
JOIN execution_production ep ON ep.guide_production_id = gp.id_guide_production
LEFT JOIN produit_final pf ON pf.execution_production_id = ep.id_execution_production
JOIN lot_olives lo ON lo.id_lot = ep.lot_olives_id
JOIN huilerie h2 ON h2.id_huilerie = lo.huilerie_id
WHERE et.machine_id IS NOT NULL AND LOWER(h2.nom) = LOWER(%s)
  AND ep.date_debut BETWEEN %s AND %s
GROUP BY et.machine_id
ORDER BY nb_exec DESC
'''

conn = get_db_connection()
cursor = conn.cursor(dictionary=True)
cursor.execute(query, (huilerie, start_date, end_date))
rows = cursor.fetchall() or []
print('rows with date filter:', len(rows))
for r in rows:
    print(r)

cursor.close()
conn.close()
