
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import os, boto3
from boto3.dynamodb.conditions import Key

def dec(v: Any) -> Any:
    if isinstance(v,float): return Decimal(str(round(v,6)))
    if isinstance(v,dict): return {k:dec(x) for k,x in v.items()}
    if isinstance(v,list): return [dec(x) for x in v]
    return v

def undec(v: Any) -> Any:
    if isinstance(v,Decimal): return int(v) if v%1==0 else float(v)
    if isinstance(v,dict): return {k:undec(x) for k,x in v.items()}
    if isinstance(v,list): return [undec(x) for x in v]
    return v

class LubricationRepository:
    def __init__(self):
        region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        session=boto3.Session(profile_name=os.getenv('AWS_PROFILE') or None, region_name=region)
        db=session.resource('dynamodb')
        self.state_table=db.Table(os.getenv('GREASE_STATE_TABLE','grease_lubrication_state'))
        self.cycles_table=db.Table(os.getenv('GREASE_CYCLES_TABLE','grease_lubrication_cycles'))
        self.alerts_table=db.Table(os.getenv('CONDITION_ALERTS_TABLE','condition_alerts'))
    @staticmethod
    def tenant_asset(tenant_id, asset_id): return f'{tenant_id}#{asset_id}'
    def save_cycle_result(self,result):
        tenant_id=result['tenant_id']; asset_id=result['asset_id']; tenant_asset=self.tenant_asset(tenant_id,asset_id)
        state={"tenant_id":tenant_id,"asset_id":asset_id,"plant_id":result.get('plant_id'),"asset_name":result.get('asset_name'),"source_id":result.get('source_id'),"updated_at":result.get('cycle_timestamp'),"cycle_id":result.get('cycle_id'),"status_label":result.get('status_label'),"outlet_count":result.get('outlet_count'),"normal_count":result.get('normal_count'),"attention_count":result.get('attention_count'),"alert_count":result.get('alert_count'),"critical_count":result.get('critical_count'),"max_pressure_bar":result.get('max_pressure_bar'),"max_anomaly_score":result.get('max_anomaly_score'),"outlets":result.get('outlets',[]),"recommendation":result.get('recommendation',{})}
        cycle={**state,"tenant_asset":tenant_asset,"cycle_timestamp":result.get('cycle_timestamp'),"payload":result.get('payload',{}),"active_alerts":result.get('active_alerts',[])}
        self.state_table.put_item(Item=dec(state)); self.cycles_table.put_item(Item=dec(cycle))
        for alert in result.get('active_alerts',[]):
            item={"tenant_asset":tenant_asset,"alert_key":f"open#{alert.get('metric')}","alert_id":f"{asset_id}#{alert.get('metric')}","tenant_id":tenant_id,"plant_id":result.get('plant_id'),"asset_id":asset_id,"asset_name":result.get('asset_name'),"metric":alert.get('metric'),"outlet_id":alert.get('outlet_id'),"value":alert.get('value'),"threshold":alert.get('threshold'),"status_label":alert.get('status_label'),"status":"open","description":alert.get('description'),"recommended_action":alert.get('recommended_action'),"evidence":alert.get('evidence',[]),"confidence":alert.get('confidence'),"first_detected_at":result.get('cycle_timestamp'),"last_detected_at":result.get('cycle_timestamp'),"source":"grease_lubrication_module"}
            self.alerts_table.put_item(Item=dec(item))
    def get_state(self,tenant_id,asset_id):
        return undec(self.state_table.get_item(Key={'tenant_id':tenant_id,'asset_id':asset_id}).get('Item',{}))
    def list_cycles(self,tenant_id,asset_id,limit=50):
        resp=self.cycles_table.query(KeyConditionExpression=Key('tenant_asset').eq(self.tenant_asset(tenant_id,asset_id)),ScanIndexForward=False,Limit=limit)
        return [undec(i) for i in resp.get('Items',[])]
    def update_cycle_dose(self,tenant_id,asset_id,cycle_timestamp,*,linked_asset_id,outlet_id,grease_amount_g,grease_type,cycle_interval_h):
        result=self.cycles_table.update_item(
            Key={'tenant_asset':self.tenant_asset(tenant_id,asset_id),'cycle_timestamp':cycle_timestamp},
            UpdateExpression='SET linked_asset_id=:linked_asset_id, linked_outlet_id=:outlet_id, grease_amount_g=:amount, grease_type=:grease_type, cycle_interval_h=:interval, dose_recorded_at=:recorded_at',
            ExpressionAttributeValues=dec({
                ':linked_asset_id': linked_asset_id,
                ':outlet_id': outlet_id,
                ':amount': grease_amount_g,
                ':grease_type': grease_type,
                ':interval': cycle_interval_h,
                ':recorded_at': datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
            }),
            ReturnValues='ALL_NEW',
        )
        return undec(result.get('Attributes',{}))
    def list_alerts(self,tenant_id,asset_id):
        resp=self.alerts_table.query(KeyConditionExpression=Key('tenant_asset').eq(self.tenant_asset(tenant_id,asset_id)))
        return [undec(i) for i in resp.get('Items',[])]
