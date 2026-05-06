import json
import urllib.request

data = json.dumps({
    'message': 'Y a-t-il des analyses anormales cette semaine ?',
    'userId': 1,
    'sessionId': 'test-session'
}).encode('utf-8')

req = urllib.request.Request(
    'http://127.0.0.1:8001/chat/ask',
    data=data,
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        print('RESPONSE:')
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if 'data' in result and result['data']:
            print(f'\nData returned: {len(result["data"])} analyses')
            for item in result['data'][:3]:
                print(f"  - Lot {item.get('lot_ref')}: acidite={item.get('acidite_huile_pourcent')}")
except Exception as e:
    print(f'Error: {e}')
