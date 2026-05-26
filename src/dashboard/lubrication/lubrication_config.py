
from pathlib import Path
import json

def default_lubrication_config():
    return {
        "tenant_id":"cliente_demo","plant_id":"lab_virtual","asset_id":"sistema_lubrificacao_01",
        "asset_name":"Sistema de Lubrificação Centralizada","source_id":"grease_gateway_01",
        "pressure_unit":"bar","sensor_range_bar":250,
        "outlets":[
            {"outlet_id":"saida_graxa_01","name":"Saída de Graxa 01"},
            {"outlet_id":"saida_graxa_02","name":"Saída de Graxa 02"},
            {"outlet_id":"saida_graxa_03","name":"Saída de Graxa 03"},
            {"outlet_id":"saida_graxa_04","name":"Saída de Graxa 04"}],
        "rules":{"low_pressure_bar":10,"high_pressure_bar":160,"critical_pressure_bar":220,"max_rise_time_sec":10,"max_decay_time_sec":15,"pulse_min_delta_bar":8}}

def load_lubrication_config(path=None):
    candidates=[]
    if path: candidates.append(Path(path))
    candidates += [Path('config/lubrication_pilot_config.json'), Path('lubrication_pilot_config.json'), Path(__file__).resolve().parents[3]/'config'/'lubrication_pilot_config.json']
    for p in candidates:
        if p.exists():
            return json.loads(p.read_text(encoding='utf-8'))
    return default_lubrication_config()
