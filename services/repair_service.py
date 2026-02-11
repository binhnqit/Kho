import pandas as pd
import streamlit as st
from core.database import supabase

def get_repair_data():
    res = supabase.table("repair_cases").select("*, machines(machine_code)").execute()
    
    if not res.data:
        # Nếu không có dữ liệu, trả về DF trống với các cột mặc định để tránh lỗi KeyError
        return pd.DataFrame(columns=['NĂM', 'THÁNG', 'machine_display', 'CHI_PHÍ', 'CHI_NHÁNH'])

    df = pd.DataFrame(res.data)
    
    # 1. Chuyển đổi sang định dạng datetime
    if 'received_date' in df.columns:
        df['received_date'] = pd.to_datetime(df['received_date'])
        
        # 2. Trích xuất NĂM và THÁNG (Đây là phần giải quyết KeyError)
        df['NĂM'] = df['received_date'].dt.year
        df['THÁNG'] = df['received_date'].dt.month
    else:
        # Trường hợp DB lỗi không có cột received_date, tạo cột giả để app không sập
        df['NĂM'] = None
        df['THÁNG'] = None

    # 3. Xử lý hiển thị mã máy
    if 'machines' in df.columns:
        df['machine_display'] = df['machines'].apply(
            lambda x: x['machine_code'] if isinstance(x, dict) and x else "N/A"
        )
    
    # 4. Đổi tên cột cho thân thiện
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
