
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT/'src'/'dashboard'))
from lubrication.lubrication_config import load_lubrication_config
from lubrication.lubrication_engine import evaluate_lubrication_cycle
from lubrication.lubrication_repository import LubricationRepository
sys.path.append(str(ROOT/'src'/'edge'/'grease_bridge'))
from grease_cycle_simulator import generate_grease_cycle_payload
config=load_lubrication_config(str(ROOT/'config'/'lubrication_pilot_config.json'))
payload=generate_grease_cycle_payload(config['tenant_id'],config['plant_id'],config['asset_id'],config['source_id'])
result=evaluate_lubrication_cycle(payload,config)
LubricationRepository().save_cycle_result(result)
print('Ciclo de lubrificação demonstrativo salvo.')
print(f"Status: {result['status_label']}")
print(f"Alertas: {len(result['active_alerts'])}")
