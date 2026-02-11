import pandas as pd
import streamlit as st
from core.database import supabase

def get_repair_data():
    # Giả sử đây là đoạn code bạn gọi từ Supabase
    # res = supabase.table("repair_cases").select("*").execute()
    # df = pd.DataFrame(res.data)
    
    # --- ĐOẠN FIX QUAN TRỌNG ---
    # Nếu df rỗng, tạo DataFrame có sẵn các cột cần thiết để không bị KeyError
    if df.empty:
        return pd.DataFrame(columns=['confirmed_dt', 'NĂM', 'THÁNG', 'CHI_PHÍ', 'branch', 'machine_display'])

    # Chuyển đổi ngày tháng an toàn
    df['confirmed_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
    
    # Xử lý các dòng bị lỗi ngày (NaT) - gán tạm bằng ngày hiện tại hoặc xóa bỏ
    df = df.dropna(subset=['confirmed_dt'])

    # Tạo cột NĂM và THÁNG từ confirmed_dt
    df['NĂM'] = df['confirmed_dt'].dt.year.astype(int)
    df['THÁNG'] = df['confirmed_dt'].dt.month.astype(int)
    
    # Đảm bảo cột chi phí là số
    df['CHI_PHÍ'] = pd.to_numeric(df.get('compensation', 0), errors='coerce').fillna(0)
    
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
