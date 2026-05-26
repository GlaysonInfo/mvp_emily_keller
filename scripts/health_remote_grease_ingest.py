from __future__ import annotations
import json, os, urllib.request

endpoint = os.getenv("GREASE_HEALTH_ENDPOINT", "https://sentinelaindustrial.com.br/grease/health")
with urllib.request.urlopen(endpoint, timeout=10) as resp:
    raw = resp.read().decode("utf-8", errors="replace")
    try:
        print(json.dumps(json.loads(raw), ensure_ascii=False, indent=2))
    except Exception:
        print(raw)
