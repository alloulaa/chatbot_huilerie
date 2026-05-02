#!/usr/bin/env python3
"""Check lots for today and different dates"""
from app.database import get_db_connection
from datetime import datetime, timedelta
from app.nlp.normalizer import resolve_period

# Get today's dates
start_date_today, end_date_today, period_text = resolve_period("aujourd_hui")
print(f"Today period: {start_date_today} to {end_date_today}")

conn = get_db_connection()
cursor = conn.cursor(dictionary=True)

# Check lots for zitouneya for TODAY
print("\n=== Lots for zitouneya TODAY ===")
query_today = """
    SELECT lo.reference, lo.date_reception, h.nom, h.entreprise_id
    FROM lot_olives lo
    JOIN huilerie h ON h.id_huilerie = lo.huilerie_id
    WHERE LOWER(h.nom) = LOWER(%s)
      AND h.entreprise_id = 1
      AND lo.date_reception BETWEEN %s AND %s
    ORDER BY lo.date_reception DESC
"""
cursor.execute(query_today, ("zitouneya", start_date_today, end_date_today))
rows_today = cursor.fetchall()
print(f"Found {len(rows_today)} lots")
for row in rows_today:
    print(f"  - {row['reference']} ({row['date_reception']})")

# Check ALL lots for zitouneya (no date filter)
print("\n=== ALL Lots for zitouneya (no date filter) ===")
query_all = """
    SELECT lo.reference, lo.date_reception, h.nom
    FROM lot_olives lo
    JOIN huilerie h ON h.id_huilerie = lo.huilerie_id
    WHERE LOWER(h.nom) = LOWER(%s)
      AND h.entreprise_id = 1
    ORDER BY lo.date_reception DESC
    LIMIT 10
"""
cursor.execute(query_all, ("zitouneya",))
rows_all = cursor.fetchall()
print(f"Found {len(rows_all)} lots")
for row in rows_all:
    print(f"  - {row['reference']} ({row['date_reception']})")

# Get current date info
print(f"\n=== Date Debug ===")
print(f"Today's date (Python): {datetime.now().date()}")
print(f"Query period: {start_date_today} to {end_date_today}")

cursor.close()
conn.close()
