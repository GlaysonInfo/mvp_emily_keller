
from datetime import datetime, timezone
from .lubrication_labels import status_priority, severity_from_priority

def now_utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def _float(v, default=None):
    try:
        if v is None or v=='': return default
        return float(v)
    except Exception:
        return default

def get_metric(metrics, prefix, outlet_id, suffix=''):
    keys=[f'{prefix}_{outlet_id}{suffix}', f'{prefix}_{outlet_id}_bar', f'{prefix}_{outlet_id}_sec', f'{prefix}_{outlet_id}']
    for k in keys:
        if k in metrics: return metrics[k]
    return None

def infer_outlets_from_payload(payload):
    outlets=set()
    for k in (payload.get('metrics') or {}):
        if k.startswith('pressure_') and k.endswith('_bar'):
            outlets.add(k.replace('pressure_','').replace('_bar',''))
    return sorted(outlets)

def evaluate_outlet(outlet_id, metrics, rules):
    pressure=_float(get_metric(metrics,'pressure',outlet_id,'_bar'),0)
    peak=_float(get_metric(metrics,'peak',outlet_id,'_bar'),pressure)
    min_pressure=_float(get_metric(metrics,'min',outlet_id,'_bar'),None)
    avg_pressure=_float(get_metric(metrics,'avg',outlet_id,'_bar'),None)
    rise_time=_float(get_metric(metrics,'rise_time',outlet_id,'_sec'),None)
    decay_time=_float(get_metric(metrics,'decay_time',outlet_id,'_sec'),None)
    low=float(rules.get('low_pressure_bar',10)); high=float(rules.get('high_pressure_bar',160)); critical=float(rules.get('critical_pressure_bar',220))
    max_rise=float(rules.get('max_rise_time_sec',10)); max_decay=float(rules.get('max_decay_time_sec',15)); pulse_delta=float(rules.get('pulse_min_delta_bar',8))
    if peak is None: pulse=False
    elif min_pressure is not None: pulse=(peak-min_pressure)>=pulse_delta
    else: pulse=peak>=low
    status='normal'; reasons=[]
    if not pulse:
        status='no_pulse'; reasons.append('Não foi detectado pulso de pressão no ciclo.')
    elif peak<=low:
        status='low_pressure'; reasons.append(f'Pico de pressão menor ou igual a {low} bar.')
    elif peak>=critical:
        status='high_pressure'; reasons.append(f'Pico de pressão acima do limite crítico de {critical} bar.')
    elif peak>=high:
        status='high_pressure'; reasons.append(f'Pico de pressão acima do limite de alerta de {high} bar.')
    if rise_time is not None and rise_time>max_rise:
        if status=='normal': status='slow_rise'
        reasons.append(f'Tempo de subida acima de {max_rise} s.')
    if decay_time is not None and decay_time>max_decay:
        if status=='high_pressure': status='high_pressure_slow_decay'
        elif status=='normal': status='slow_decay'
        reasons.append(f'Tempo de alívio acima de {max_decay} s.')
    priority=status_priority(status)
    anomaly=min(100,priority*18)
    if peak and high:
        anomaly=max(anomaly,min(100,max(0,(peak-high)/high*100)))
    if peak and low and peak<low:
        anomaly=max(anomaly,min(100,(low-peak)/low*100))
    return {"outlet_id":outlet_id,"pressure_bar":pressure,"peak_pressure_bar":peak,"min_pressure_bar":min_pressure,"avg_pressure_bar":avg_pressure,"rise_time_sec":rise_time,"decay_time_sec":decay_time,"pulse_detected":pulse,"status":status,"severity":severity_from_priority(priority),"priority":priority,"anomaly_score":round(float(anomaly),1),"reasons":reasons}

def build_alert_from_outlet(payload,outlet):
    oid=outlet['outlet_id']; status=outlet['status']
    if status=='low_pressure': desc=f'{oid} com baixa pressão no ciclo.'; action='Verificar falta de graxa, vazamento, linha aberta, conexão, pistão e bico de lubrificação.'
    elif status=='no_pulse': desc=f'{oid} sem pulso de pressão detectado.'; action='Verificar pistão, linha da saída, distribuidor e alimentação de graxa.'
    elif status=='high_pressure_slow_decay': desc=f'{oid} com alta pressão e alívio lento.'; action='Inspecionar obstrução parcial, graxa endurecida, restrição na linha ou bico bloqueado.'
    elif status=='high_pressure': desc=f'{oid} com pico de pressão elevado.'; action='Verificar obstrução, ponto de aplicação bloqueado, graxa endurecida ou restrição mecânica.'
    elif status=='slow_rise': desc=f'{oid} com subida lenta de pressão.'; action='Verificar alimentação, viscosidade da graxa, linha parcialmente aberta ou pistão com atuação irregular.'
    elif status=='slow_decay': desc=f'{oid} com alívio lento de pressão.'; action='Verificar retorno, restrição, obstrução parcial ou ponto de aplicação pesado.'
    else: desc=f'{oid} com anomalia de lubrificação.'; action='Inspecionar a saída de graxa e confirmar funcionamento do ciclo.'
    return {"metric":f"grease_pressure_{oid}","outlet_id":oid,"status_label":outlet['severity'],"status":"open","description":desc,"value":outlet.get('peak_pressure_bar'),"threshold":None,"recommended_action":action,"evidence":outlet.get('reasons',[]),"confidence":min(1.0,0.55+outlet.get('priority',0)*0.08)}

def build_ai_recommendation(outlets):
    bad=[o for o in outlets if o['status']!='normal']
    if not bad:
        return {"primary_hypothesis":"Sistema de lubrificação com comportamento normal no ciclo atual.","confidence":0.80,"evidence":["Todas as saídas monitoradas apresentaram pulso e pressão dentro das regras iniciais."],"recommended_actions":["Manter monitoramento e registrar próximos ciclos para formação de baseline."]}
    worst=sorted(bad,key=lambda x:x['priority'],reverse=True)[0]; oid=worst['outlet_id']; status=worst['status']
    if status=='low_pressure': hyp=f'Possível falta de lubrificação ou linha aberta na {oid}.'
    elif status=='no_pulse': hyp=f'Ausência de pulso de lubrificação na {oid}.'
    elif status in ['high_pressure','high_pressure_slow_decay']: hyp=f'Possível obstrução, graxa endurecida ou ponto pesado na {oid}.'
    elif status=='slow_decay': hyp=f'Possível restrição ou retorno lento na {oid}.'
    elif status=='slow_rise': hyp=f'Possível alimentação irregular ou pistão com atuação lenta na {oid}.'
    else: hyp=f'Anomalia de lubrificação na {oid}.'
    return {"primary_hypothesis":hyp,"confidence":min(0.95,0.65+worst['priority']*0.05),"evidence":worst.get('reasons',[]),"recommended_actions":["Comparar o manômetro físico com a leitura eletrônica.","Inspecionar a linha e o bico da saída indicada.","Verificar se houve pulso de lubrificação no ciclo.","Registrar ação tomada na Central de Alertas."],"affected_outlets":[o['outlet_id'] for o in bad]}

def evaluate_lubrication_cycle(payload, config):
    metrics=payload.get('metrics') or {}; rules=config.get('rules') or {}
    outlets=[o.get('outlet_id') for o in config.get('outlets',[]) if o.get('outlet_id')] or infer_outlets_from_payload(payload)
    outlet_results=[evaluate_outlet(oid,metrics,rules) for oid in outlets]
    max_priority=max([o['priority'] for o in outlet_results], default=0)
    alerts=[build_alert_from_outlet(payload,o) for o in outlet_results if o['status']!='normal']
    return {"tenant_id":payload.get('tenant_id',config.get('tenant_id')),"plant_id":payload.get('plant_id',config.get('plant_id')),"asset_id":payload.get('asset_id',config.get('asset_id')),"asset_name":config.get('asset_name','Sistema de Lubrificação'),"source_id":payload.get('source_id',config.get('source_id')),"cycle_id":payload.get('cycle_id') or f"cycle_{now_utc()}","cycle_timestamp":payload.get('timestamp_utc') or now_utc(),"status_label":severity_from_priority(max_priority),"outlet_count":len(outlet_results),"normal_count":sum(1 for o in outlet_results if o['status']=='normal'),"attention_count":sum(1 for o in outlet_results if o['severity']=='ATENÇÃO'),"alert_count":sum(1 for o in outlet_results if o['severity']=='ALERTA'),"critical_count":sum(1 for o in outlet_results if o['severity']=='CRÍTICO'),"max_pressure_bar":max([o['peak_pressure_bar'] or 0 for o in outlet_results], default=0),"max_anomaly_score":max([o['anomaly_score'] or 0 for o in outlet_results], default=0),"outlets":outlet_results,"active_alerts":alerts,"payload":payload,"recommendation":build_ai_recommendation(outlet_results)}
