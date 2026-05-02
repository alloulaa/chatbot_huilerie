#!/usr/bin/env python3
from app.database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor(dictionary=True)

# Find all huileries
cursor.execute("SELECT id_huilerie, nom, entreprise_id FROM huilerie ORDER BY entreprise_id, nom")
rows = cursor.fetchall()

print("=== All Huileries ===")
for row in rows:
    print(f"ID: {row['id_huilerie']:3d} | Nom: {row['nom']:20s} | Entreprise: {row['entreprise_id']}")

# Find zitouneya specifically
print("\n=== Looking for zitouneya ===")
cursor.execute("SELECT id_huilerie, nom, entreprise_id FROM huilerie WHERE LOWER(nom) LIKE LOWER(%s)", ("%zitouneya%",))
rows = cursor.fetchall()
for row in rows:
    print(f"Found: {row['nom']} (Entreprise ID: {row['entreprise_id']})")

cursor.close()
conn.close()
