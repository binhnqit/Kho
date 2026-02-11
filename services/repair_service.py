import pandas as pd
import streamlit as st
from core.database import supabase

def get_repair_data():
    try:
        # 1. Lấy dữ liệu sửa chữa
        res_repair = supabase.table("repair_cases").select("*").execute()
        df_repair = pd.DataFrame(res_repair.data)

        # 2. Lấy danh mục máy để lấy machine_code
        res_machines = supabase.table("machines").select("id, machine_code").execute()
        df_machines = pd.DataFrame(res_machines.data)

        if df_repair.empty:
            return pd.DataFrame(columns=['machine_display', 'NĂM', 'THÁNG', 'CHI_PHÍ', 'branch'])

        # 3. MAPPING: Đổi ID dài ngoằng thành Code ngắn gọn
        # Gộp bảng repair với bảng machines dựa trên cột id máy
        df = df_repair.merge(
            df_machines, 
            left_on='machine_id', 
            right_on='id', 
            how='left', 
            suffixes=('', '_m')
        )

        # 4. TẠO CỘT HIỂN THỊ CHUẨN
        # Nếu có machine_code thì hiện, không thì hiện 'N/A' thay vì cái ID dài
        df['machine_display'] = df['machine_code'].fillna('N/A')

        # --- Các bước xử lý NĂM/THÁNG/CHI PHÍ giữ nguyên như cũ ---
        df['confirmed_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df = df.dropna(subset=['confirmed_dt'])
        df['NĂM'] = df['confirmed_dt'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_dt'].dt.month.astype(int)
        df['CHI_PHÍ'] = pd.to_numeric(df.get('compensation', 0), errors='coerce').fillna(0)

        return df
    except Exception as e:
        st.error(f"Lỗi Mapping: {e}")
        return pd.DataFrame()
def insert_new_repair(data_dict):
    """
    Thêm bản ghi mới vào bảng repair_cases.
    """
    try:
        # Clean data trước khi gửi lên database
        if 'created_by' in data_dict:
            data_dict.pop('created_by')
            
        # Thực hiện insert
        response = supabase.table("repair_cases").insert(data_dict).execute()
        
        # Xóa cache để Dashboard cập nhật số liệu mới ngay lập tức
        st.cache_data.clear()
        
        return response
    except Exception as e:
        st.error(f"❌ Không thể lưu dữ liệu: {str(e)}")
        return None
