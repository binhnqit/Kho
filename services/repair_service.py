import pandas as pd
import streamlit as st
from core.database import supabase

def get_repair_data():
    res = supabase.table("repair_cases").select("*, machines(machine_code)").execute()
    
    if not res.data:
        return pd.DataFrame()

    df = pd.DataFrame(res.data)
    
    # --- BỔ SUNG ĐOẠN NÀY ---
    # 1. Chuyển đổi cột ngày nhận máy sang định dạng datetime
    if 'received_date' in df.columns:
        df['received_date'] = pd.to_datetime(df['received_date'])
        # 2. Tạo cột 'NĂM' để dashboard.py không bị lỗi KeyError
        df['NĂM'] = df['received_date'].dt.year
    # ------------------------

    if 'machines' in df.columns:
        df['machine_display'] = df['machines'].apply(lambda x: x['machine_code'] if isinstance(x, dict) else "N/A")
    
    df = df.rename(columns={
        'compensation': 'CHI_PHÍ',
        'branch': 'CHI_NHÁNH'
    })
    
    return df

def insert_new_repair(data_dict):
    """
    Data_dict truyền vào cần khớp với các cột:
    machine_id, branch, customer_name, received_date, 
    issue_reason, confirmed_date, note, is_unrepairable, compensation
    """
    try:
        # Loại bỏ 'created_by' nếu có trong data_dict vì DB không có cột này
        if 'created_by' in data_dict:
            data_dict.pop('created_by')
            
        # Thực hiện insert vào Supabase
        response = supabase.table("repair_cases").insert(data_dict).execute()
        return response
    except Exception as e:
        st.error(f"❌ Lỗi Insert: {str(e)}")
        return None
