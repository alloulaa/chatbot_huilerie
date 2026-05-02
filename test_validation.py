#!/usr/bin/env python3
"""
Test the complete huilerie validation logic
"""
from app.database import get_db_connection
from app.services.permission_service import is_huilerie_allowed

print("=== Testing Huilerie Validation ===\n")

# Test 1: zitouneya (enterprise 1) with user from enterprise 1 - should PASS
print("Test 1: zitouneya (enterprise 1) - user from enterprise 1")
result = is_huilerie_allowed("zitouneya", enterprise_id=1)
print(f"  Result: {result} (expected: True)\n")

# Test 2: Moulin Artisanal (enterprise 2) with user from enterprise 1 - should FAIL
print("Test 2: Moulin Artisanal (enterprise 2) - user from enterprise 1")
result = is_huilerie_allowed("Moulin Artisanal", enterprise_id=1)
print(f"  Result: {result} (expected: False)\n")

# Test 3: Moulin Sfax (enterprise 1) with user from enterprise 1 - should PASS
print("Test 3: Moulin Sfax (enterprise 1) - user from enterprise 1")
result = is_huilerie_allowed("Moulin Sfax", enterprise_id=1)
print(f"  Result: {result} (expected: True)\n")

# Test 4: Non-existent huilerie - should FAIL
print("Test 4: Non-existent huilerie")
result = is_huilerie_allowed("Fake Huilerie", enterprise_id=1)
print(f"  Result: {result} (expected: False)\n")

# Test 5: None huilerie - should PASS (no restriction)
print("Test 5: None huilerie (no restriction)")
result = is_huilerie_allowed(None, enterprise_id=1)
print(f"  Result: {result} (expected: True)\n")

# Test 6: Test user_enterprise_id deduction
print("Test 6: Deducing enterprise_id from user_huilerie")
conn = get_db_connection()
cursor = conn.cursor(dictionary=True)
query = "SELECT entreprise_id FROM huilerie WHERE LOWER(nom) = LOWER(%s)"
cursor.execute(query, ("zitouneya",))
row = cursor.fetchone()
if row:
    deduced_enterprise_id = row.get("entreprise_id")
    print(f"  Deduced enterprise_id for 'zitouneya': {deduced_enterprise_id} (expected: 1)")
    print(f"  This enterprise_id would then be used for validation")
cursor.close()
conn.close()
