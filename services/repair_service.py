import pandas as pd
from core.database import supabase

def get_repair_data():
    try:
        res_repair = supabase.table("repair_cases").select("*").execute()
        df = pd.DataFrame(res_repair.data)
        if df.empty:
            return pd.DataFrame()

        res_m = supabase.table("machines").select("id, machine_code").execute()
        map_dict = {m['id']: str(m['machine_code']) for m in res_m.data}

        df['machine_display'] = df['machine_id'].map(map_dict).fillna("N/A")
        df['confirmed_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df['NĂM'] = df['confirmed_dt'].dt.year
        df['THÁNG'] = df['confirmed_dt'].dt.month
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)

        return df
    except Exception as e:
        return pd.DataFrame()

def insert_new_repair(data_dict):
    return supabase.table("repair_cases").insert(data_dict).execute()
