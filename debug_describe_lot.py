#!/usr/bin/env python3
from app.database import get_db_connection

conn = get_db_connection()
cur = conn.cursor(dictionary=True)
cur.execute('DESCRIBE lot_olives')
rows = cur.fetchall()
print('=== lot_olives columns ===')
for r in rows:
    print(r['Field'], r['Type'])
cur.close()
conn.close()
