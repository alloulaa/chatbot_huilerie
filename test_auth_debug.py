#!/usr/bin/env python3
"""
Debug script to check what the JWT/auth backend returns
Run this and provide the JWT token from your authenticated session
"""
import json
from app.services.permission_service import (
    get_user_permissions, 
    get_user_enterprise_id,
    is_admin,
    get_user_huilerie
)

print("=" * 70)
print("JWT Authentication Debugger")
print("=" * 70)
print("""
To use this script:
1. Login to the application in your browser
2. Open Developer Tools (F12) > Application > Cookies (or Local Storage)
3. Find your JWT token
4. Replace 'YOUR_JWT_TOKEN' below with that token
5. Run this script: python test_auth_debug.py
""")

JWT_TOKEN = None  # PASTE YOUR JWT HERE

if JWT_TOKEN and JWT_TOKEN != "YOUR_JWT_TOKEN":
    print(f"\nTesting with JWT (first 50 chars): {JWT_TOKEN[:50]}...\n")
    
    print("1. Getting user permissions...")
    auth_data = get_user_permissions(JWT_TOKEN)
    
    if auth_data:
        print("\n✓ Authentication successful!")
        print("\nFull auth_data:")
        print(json.dumps(auth_data, indent=2, default=str))
        
        print("\n2. Extracted user information:")
        user = auth_data.get("utilisateur") or {}
        print(f"   - User ID: {user.get('id')}")
        print(f"   - Name: {user.get('nom')}")
        print(f"   - Profile: {user.get('profil')}")
        
        enterprise_id = get_user_enterprise_id(auth_data)
        print(f"   - Enterprise ID: {enterprise_id} {'✓' if enterprise_id else '✗ MISSING'}")
        print(f"   - Huilerie ID: {user.get('huilerieId')}")
        
        user_is_admin = is_admin(auth_data)
        print(f"   - Is Admin: {user_is_admin}")
        
        user_huilerie = get_user_huilerie(auth_data, JWT_TOKEN)
        print(f"   - User Huilerie: {user_huilerie}")
        
        print("\n3. Permissions:")
        for perm in auth_data.get('permissions', []):
            can_read = perm.get('canRead') or perm.get('can_read')
            print(f"   - {perm.get('module')}: {'read' if can_read else 'denied'}")
        
        if not enterprise_id and user_huilerie:
            print("\n⚠️  WARNING: No entrepriseId in JWT but user has huilerie!")
            print("   → The new code will deduce enterprise_id from huilerie")
            from app.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT entreprise_id FROM huilerie WHERE LOWER(nom) = LOWER(%s)", (user_huilerie,))
            row = cursor.fetchone()
            if row:
                print(f"   → Deduced enterprise_id: {row['entreprise_id']}")
            cursor.close()
            conn.close()
    else:
        print("\n✗ Authentication failed!")
        print("   - JWT is invalid or expired")
        print("   - Backend is unreachable")
else:
    print("\n" + "=" * 70)
    print("ERROR: No JWT provided!")
    print("=" * 70)
    print("\nPlease provide your JWT token to continue.")
