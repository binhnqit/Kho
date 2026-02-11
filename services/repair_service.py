import pandas as pd
import streamlit as st
from core.database import supabase

def get_repair_data():
    # ... logic lấy dữ liệu từ Supabase ...
    res = supabase.table("repair_cases").select("*").execute()
    df = pd.DataFrame(res.data)
    
    # DANH SÁCH CỘT BẮT BUỘC PHẢI CÓ
    required_columns = ['branch', 'machine_display', 'confirmed_dt', 'CHI_PHÍ', 'NĂM', 'THÁNG']
    
    if df.empty:
        # Tạo dataframe rỗng nhưng có đầy đủ tên cột để các hàm sau không bị lỗi KeyError
        return pd.DataFrame(columns=required_columns)
    
    # Đảm bảo cột branch tồn tại (đề phòng trường hợp trong DB đặt tên khác)
    if 'branch' not in df.columns:
        # Nếu DB đặt tên là 'chi_nhanh' thì rename, nếu không có thì tạo cột giả
        df['branch'] = "Chưa xác định"
        
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
