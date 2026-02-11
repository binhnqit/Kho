import pandas as pd
import streamlit as st
from core.database import supabase

def get_repair_data():
    # Sử dụng .select("*, machines(machine_code)") để lấy thông tin từ cả 2 bảng
    res = supabase.table("repair_cases").select("""
        *,
        machines (
            machine_code
        )
    """).execute()
    
    if not res.data:
        return pd.DataFrame()

    df = pd.DataFrame(res.data)
    
    # Làm phẳng dữ liệu (Flatten) để cột machine_code nằm ngoài cùng cho dễ dùng
    if 'machines' in df.columns:
        df['machine_display'] = df['machines'].apply(lambda x: x['machine_code'] if isinstance(x, dict) else "N/A")
    
    # Đổi tên cột hiển thị cho thân thiện (Tùy chọn)
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
