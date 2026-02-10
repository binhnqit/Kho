import pandas as pd
from core.database import supabase

def get_repair_data():
    """Lấy toàn bộ dữ liệu từ database và chuẩn hóa"""
    try:
        # 1. Lấy dữ liệu repair_cases (Dùng limit để vượt ngưỡng 1000 nếu cần)
        # Nếu data của bạn cực lớn, cần dùng vòng lặp, hiện tại ta tăng limit lên 5000
        res_repair = supabase.table("repair_cases").select("*").limit(5000).execute()
        df = pd.DataFrame(res_repair.data)

        if df.empty:
            return pd.DataFrame()

        # 2. Lấy dữ liệu bảng machines để mapping
        res_m = supabase.table("machines").select("id, machine_code").execute()
        map_dict = {m['id']: str(m['machine_code']) for m in res_m.data}

        # 3. CHUẨN HÓA DỮ LIỆU
        # Map UUID sang Mã máy
        df['machine_display'] = df['machine_id'].map(map_dict).fillna("MÁY LẠ (ID sai)")
        
        # Xử lý ngày tháng: confirmed_date
        # errors='coerce' sẽ biến các ngày sai định dạng thành NaT (Not a Time)
        df['confirmed_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        
        # Loại bỏ dữ liệu rác nếu năm quá lớn (ví dụ năm > 2025) hoặc bị trống
        # Bạn có thể điều chỉnh mốc năm này
        current_year = 2025 
        df = df[df['confirmed_dt'].dt.year <= current_year]
        
        # Trích xuất Năm và Tháng sau khi đã lọc rác
        df['NĂM'] = df['confirmed_dt'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_dt'].dt.month.astype(int)
        
        # Ép kiểu số cho chi phí
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)

        return df
    except Exception as e:
        print(f"Lỗi tại Service: {e}")
        return pd.DataFrame()

def insert_new_repair(data_dict):
    """Hàm chèn dữ liệu mới"""
    return supabase.table("repair_cases").insert(data_dict).execute()
