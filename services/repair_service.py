# services/repair_service.py
import pandas as pd
from core.database import supabase

def get_repair_data():
    """
    Hàm lấy dữ liệu tổng hợp: 
    1. Lấy repair_cases 
    2. Lấy machines để map ID sang Mã Máy
    3. Chuẩn hóa các cột số và ngày tháng
    """
    try:
        # 1. Lấy dữ liệu từ bảng sửa chữa
        res_repair = supabase.table("repair_cases").select("*").execute()
        df = pd.DataFrame(res_repair.data)

        if df.empty:
            return pd.DataFrame()

        # 2. Lấy dữ liệu bảng máy để mapping mã máy thân thiện (1641,...)
        res_m = supabase.table("machines").select("id, machine_code").execute()
        map_dict = {m['id']: str(m['machine_code']) for m in res_m.data}

        # 3. CHUẨN HÓA DỮ LIỆU (Fix lỗi cột và dòng)
        # Map UUID sang Mã máy
        df['machine_display'] = df['machine_id'].map(map_dict).fillna("N/A")
        
        # Ép kiểu ngày tháng
        df['confirmed_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df['NĂM'] = df['confirmed_dt'].dt.year
        df['THÁNG'] = df['confirmed_dt'].dt.month
        
        # Ép kiểu số cho chi phí (Fix lỗi compensation)
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)

        return df
    except Exception as e:
        print(f"Lỗi Service: {e}")
        return pd.DataFrame()

def insert_new_repair(data_dict):
    """Hàm dùng để lưu ca sửa chữa mới (cho Tab Admin)"""
    return supabase.table("repair_cases").insert(data_dict).execute()
