
OUTLET_STATUS_LABELS = {
    "normal": "Normal",
    "low_pressure": "Baixa pressão",
    "high_pressure": "Alta pressão",
    "no_pulse": "Sem pulso",
    "slow_rise": "Subida lenta",
    "slow_decay": "Alívio lento",
    "high_pressure_slow_decay": "Alta pressão + alívio lento",
    "sensor_fault": "Falha de sensor",
}
STATUS_PRIORITY = {"normal":0,"low_pressure":2,"slow_rise":2,"slow_decay":2,"high_pressure":3,"high_pressure_slow_decay":4,"no_pulse":5,"sensor_fault":5}
SEVERITY_LABELS = {0:"NORMAL",1:"ATENÇÃO",2:"ATENÇÃO",3:"ALERTA",4:"ALERTA",5:"CRÍTICO"}
def outlet_label(outlet_id: str) -> str:
    return str(outlet_id or '').replace('_',' ').title().replace('Saida','Saída')
def status_label(status: str) -> str:
    return OUTLET_STATUS_LABELS.get(status, status)
def status_priority(status: str) -> int:
    return STATUS_PRIORITY.get(status, 0)
def severity_from_priority(priority: int) -> str:
    return SEVERITY_LABELS.get(priority, 'NORMAL')
