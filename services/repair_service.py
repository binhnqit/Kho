import pandas as pd
import streamlit as st
from core.database import supabase

def get_repair_data():
    try:
        res = supabase.table("repair_cases").select("*, machines(machine_code)").execute()
        
        # Nếu không có dữ liệu hoặc lỗi, trả về DataFrame trống có sẵn các cột cần thiết
        if not res.data:
            return pd.DataFrame(columns=['NĂM', 'THÁNG', 'CHI_NHÁNH', 'CHI_PHÍ', 'machine_display'])

        df = pd.DataFrame(res.data)
        
        # 1. Xử lý thời gian
        if 'received_date' in df.columns:
            df['received_date'] = pd.to_datetime(df['received_date'])
            df['NĂM'] = df['received_date'].dt.year
            df['THÁNG'] = df['received_date'].dt.month
        
        # 2. Xử lý mã máy
        if 'machines' in df.columns:
            df['machine_display'] = df['machines'].apply(
                lambda x: x['machine_code'] if isinstance(x, dict) and x else "N/A"
            )

        # 3. Đổi tên cột (Lưu ý: Sau bước này, 'branch' trở thành 'CHI_NHÁNH')
        df = df.rename(columns={
            'compensation': 'CHI_PHÍ',
            'branch': 'CHI_NHÁNH'
        })
        
        # Đảm bảo các cột cần thiết luôn tồn tại để tránh KeyError
        required_cols = ['NĂM', 'THÁNG', 'CHI_NHÁNH', 'CHI_PHÍ', 'machine_display']
        for col in required_cols:
            if col not in df.columns:
                df[col] = None

        return df
        
    except Exception as e:
        st.error(f"Lỗi lấy dữ liệu: {e}")
        return pd.DataFrame(columns=['NĂM', 'THÁNG', 'CHI_NHÁNH', 'CHI_PHÍ', 'machine_display'])

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
