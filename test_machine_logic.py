#!/usr/bin/env python3
"""
Test script for machine listing logic
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.query_service import ChatbotService

def test_machine_logic():
    service = ChatbotService()

    print("=== Testing Machine Logic ===\n")

    # Test 1: Get all machines (admin view)
    print("1. Getting all machines (admin view):")
    result = service.get_all_machines(enterprise_id=1)
    machines = result.get("value", [])
    print(f"   Found {len(machines)} machines")
    for m in machines[:3]:  # Show first 3
        print(f"   - {m['nomMachine']} ({m['huilerie']}) - {m['etatMachine']}")
    if len(machines) > 3:
        print(f"   ... and {len(machines) - 3} more")
    print()

    # Test 2: Get machines for specific huilerie
    print("2. Getting machines for 'zitouneya':")
    result = service.get_all_machines(huilerie="zitouneya", enterprise_id=1)
    machines = result.get("value", [])
    print(f"   Found {len(machines)} machines")
    for m in machines:
        print(f"   - {m['nomMachine']} - {m['etatMachine']}")
    print()

    # Test 3: Get machines with issues
    print("3. Getting machines with issues:")
    result = service.get_machines(enterprise_id=1)
    machines = result.get("value", [])
    print(f"   Found {len(machines)} machines with issues")
    for m in machines:
        print(f"   - {m['nomMachine']} - {m['etatMachine']}")
    print()

    # Test 4: Get machine usage stats
    print("4. Getting machine usage statistics:")
    result = service.get_machines_utilisees(enterprise_id=1)
    machines = result.get("value", [])
    print(f"   Found {len(machines)} machines with usage data")
    for m in machines[:3]:  # Show top 3
        nb_exec = m.get('nbExecutions', 0)
        rend = m.get('rendementMoyen', 0.0)
        total = m.get('totalProduit', 0.0)
        print(f"   - {m['nomMachine']}: {nb_exec} exec, {rend:.1f}% yield, {total:.0f}L produced")
    print()

if __name__ == "__main__":
    test_machine_logic()
