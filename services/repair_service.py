import pandas as pd
import streamlit as st
from core.database import supabase

def get_repair_data():
    try:
        # 1. Tải dữ liệu repair_cases (Tiếp thu: Sắp xếp desc và lấy toàn bộ)
        res = supabase.table("repair_cases").select("*").order("created_at", desc=True).execute()
        if not res.data: 
            return pd.DataFrame()
        
        df = pd.DataFrame(res.data)
        
        # 2. Tải dữ liệu machines để map mã máy (Quan trọng để hiển thị 1641...)
        res_m = supabase.table("machines").select("id, machine_code").execute()
        map_dict = {m['id']: str(m['machine_code']) for m in res_m.data}

        # 3. CHUẨN HÓA NGÀY THÁNG (Tiếp thu: dropna và Thứ tiếng Việt)
        df['confirmed_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df['created_dt'] = pd.to_datetime(df['created_at'], errors='coerce')
        
        # Loại bỏ dòng không có ngày để tránh lỗi biểu đồ
        df = df.dropna(subset=['confirmed_dt'])

        # Tiếp thu: Mapping Thứ trong tuần
        day_map = {
            'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
            'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'
        }
        df['NĂM'] = df['confirmed_dt'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_dt'].dt.month.astype(int)
        df['THỨ'] = df['confirmed_dt'].dt.day_name().map(day_map)

        # 4. CHUẨN HÓA HIỂN THỊ VÀ CHI PHÍ
        df['machine_display'] = df['machine_id'].map(map_dict).fillna("MÁY LẠ/ID SAI")
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)

        # Lưu ý: Hiện tại đang là năm 2026, nếu data có năm 2026 là chính xác với thực tế hiện tại.
        
        return df.sort_values(by='created_dt', ascending=False)

    except Exception as e:
        st.error(f"❌ Lỗi hệ thống tải data: {e}")
        return pd.DataFrame()

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
