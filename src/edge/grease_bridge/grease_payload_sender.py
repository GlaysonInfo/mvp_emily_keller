
import json, os, urllib.request
from grease_cycle_simulator import generate_grease_cycle_payload

def send_payload(endpoint,payload,timeout_sec=10):
    req=urllib.request.Request(endpoint,data=json.dumps(payload).encode('utf-8'),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=timeout_sec) as resp:
        raw=resp.read().decode('utf-8',errors='replace')
        try: return json.loads(raw)
        except Exception: return {'raw':raw,'status':resp.status}
if __name__=='__main__':
    endpoint=os.getenv('GREASE_BRIDGE_ENDPOINT','http://localhost:8000/grease/ingest')
    print(json.dumps(send_payload(endpoint,generate_grease_cycle_payload()),ensure_ascii=False,indent=2))
