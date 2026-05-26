
import pandas as pd
import streamlit as st
from .lubrication_config import load_lubrication_config
from .lubrication_engine import evaluate_lubrication_cycle
from .lubrication_labels import status_label, outlet_label
from .lubrication_repository import LubricationRepository

def outlets_df(data):
    rows=[]
    for o in data.get('outlets',[]):
        rows.append({'Saída':outlet_label(o.get('outlet_id')),'Pressão atual (bar)':o.get('pressure_bar'),'Pico do ciclo (bar)':o.get('peak_pressure_bar'),'Subida (s)':o.get('rise_time_sec'),'Alívio (s)':o.get('decay_time_sec'),'Pulso':'Sim' if o.get('pulse_detected') else 'Não','Status':status_label(o.get('status')),'Severidade':o.get('severity'),'Score':o.get('anomaly_score')})
    return pd.DataFrame(rows)

def alerts_df(alerts):
    return pd.DataFrame([{'Saída':outlet_label(a.get('outlet_id','')),'Severidade':a.get('status_label'),'Descrição':a.get('description'),'Valor':a.get('value'),'Ação recomendada':a.get('recommended_action'),'Status':a.get('status')} for a in alerts])

def cycles_df(cycles):
    return pd.DataFrame([{'Data/Hora':c.get('cycle_timestamp'),'Ciclo':c.get('cycle_id'),'Status':c.get('status_label'),'Saídas':c.get('outlet_count'),'Normais':c.get('normal_count'),'Atenção':c.get('attention_count'),'Alertas':c.get('alert_count'),'Críticos':c.get('critical_count'),'Maior pressão (bar)':c.get('max_pressure_bar'),'Maior score':c.get('max_anomaly_score')} for c in cycles])

def sample_payload_from_config(config):
    return {'tenant_id':config.get('tenant_id'),'plant_id':config.get('plant_id'),'asset_id':config.get('asset_id'),'source_id':config.get('source_id'),'timestamp_utc':'2026-05-25T23:30:00Z','cycle_id':'cycle_demo_dashboard','metrics':{'pressure_saida_graxa_01_bar':84.2,'pressure_saida_graxa_02_bar':91.7,'pressure_saida_graxa_03_bar':7.8,'pressure_saida_graxa_04_bar':146.5,'peak_saida_graxa_01_bar':102.3,'peak_saida_graxa_02_bar':108.1,'peak_saida_graxa_03_bar':9.2,'peak_saida_graxa_04_bar':181.2,'min_saida_graxa_01_bar':2.0,'min_saida_graxa_02_bar':2.0,'min_saida_graxa_03_bar':0.0,'min_saida_graxa_04_bar':4.0,'rise_time_saida_graxa_01_sec':3.2,'rise_time_saida_graxa_02_sec':3.5,'rise_time_saida_graxa_03_sec':8.9,'rise_time_saida_graxa_04_sec':2.1,'decay_time_saida_graxa_01_sec':4.8,'decay_time_saida_graxa_02_sec':5.1,'decay_time_saida_graxa_03_sec':2.4,'decay_time_saida_graxa_04_sec':18.6}}

def render_lubrication_page(config_path='config/lubrication_pilot_config.json'):
    st.header('Sistema de Lubrificação')
    st.caption('Monitoramento inteligente de pressão por saída de graxa.')
    config=load_lubrication_config(config_path); repo=LubricationRepository(); tenant_id=config.get('tenant_id'); asset_id=config.get('asset_id')
    a,b,c,d=st.columns(4); a.metric('Ativo',config.get('asset_name',asset_id)); b.metric('Saídas monitoradas',len(config.get('outlets',[]))); c.metric('Sensor sugerido',f"0–{config.get('sensor_range_bar',250)} bar"); d.metric('Fonte',config.get('source_id'))
    state=repo.get_state(tenant_id,asset_id); cycles=repo.list_cycles(tenant_id,asset_id,30); alerts=repo.list_alerts(tenant_id,asset_id)
    if not state:
        st.warning('Ainda não há ciclo salvo para este sistema de lubrificação.')
        if st.button('Gerar ciclo demonstrativo',type='primary',use_container_width=True):
            result=evaluate_lubrication_cycle(sample_payload_from_config(config),config); repo.save_cycle_result(result); st.success('Ciclo demonstrativo salvo.'); st.rerun()
        return
    k1,k2,k3,k4,k5=st.columns(5); k1.metric('Status geral',state.get('status_label','-')); k2.metric('Normais',state.get('normal_count',0)); k3.metric('Atenção',state.get('attention_count',0)); k4.metric('Alertas',state.get('alert_count',0)); k5.metric('Críticos',state.get('critical_count',0))
    tab1,tab2,tab3,tab4,tab5=st.tabs(['Visão Geral','Pressão por Saída','Últimos Ciclos','Alertas Ativos','Recomendação da IA'])
    with tab1:
        st.subheader('Ciclo atual'); st.dataframe(outlets_df(state),use_container_width=True,hide_index=True)
        if st.button('Gerar novo ciclo demonstrativo',use_container_width=True):
            result=evaluate_lubrication_cycle(sample_payload_from_config(config),config); repo.save_cycle_result(result); st.success('Novo ciclo demonstrativo salvo.'); st.rerun()
    with tab2:
        df=outlets_df(state); st.dataframe(df,use_container_width=True,hide_index=True); st.download_button('Exportar pressão por saída CSV',df.to_csv(index=False,sep=';',encoding='utf-8-sig').encode('utf-8-sig'),'pressao_por_saida.csv','text/csv',use_container_width=True)
    with tab3:
        df=cycles_df(cycles); st.dataframe(df,use_container_width=True,hide_index=True) if not df.empty else st.info('Nenhum ciclo histórico encontrado.')
    with tab4:
        df=alerts_df(alerts); st.dataframe(df,use_container_width=True,hide_index=True) if not df.empty else st.success('Nenhum alerta ativo registrado para o sistema de lubrificação.')
    with tab5:
        rec=state.get('recommendation',{}); st.metric('Hipótese principal',rec.get('primary_hypothesis','-')); st.metric('Confiança',f"{float(rec.get('confidence',0))*100:.0f}%")
        st.markdown('#### Evidências')
        for ev in rec.get('evidence',[]): st.markdown(f'- {ev}')
        st.markdown('#### Ações recomendadas')
        for action in rec.get('recommended_actions',[]): st.markdown(f'- {action}')
        if rec.get('affected_outlets'): st.warning('Saídas afetadas: '+', '.join(rec['affected_outlets']))
