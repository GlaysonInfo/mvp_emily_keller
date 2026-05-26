from __future__ import annotations

import os

from scripts.test_condition_ingest import main


os.environ.setdefault("CONDITION_INGEST_ENDPOINT", "https://sentinelaindustrial.com.br/condition/ingest")

if __name__ == "__main__":
    main()
