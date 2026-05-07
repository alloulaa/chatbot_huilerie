import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.database import get_db_connection

huilerie_name = 'ma3sra'

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
WHERE LOWER(h2.nom) = LOWER(%s)
GROUP BY et.machine_id
ORDER BY nb_exec DESC
'''

conn = None
cursor = None
try:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, (huilerie_name,))
    rows = cursor.fetchall() or []
    print('Found', len(rows), 'rows')
    for r in rows:
        print(r)
except Exception as e:
    print('Error', e)
finally:
    if cursor:
        cursor.close()
    if conn and conn.is_connected():
        conn.close()
