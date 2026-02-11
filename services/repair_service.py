import pandas as pd
import streamlit as st
from core.database import supabase

def get_repair_data():
    """
    Lấy dữ liệu từ Supabase và tiền xử lý các cột NĂM, THÁNG, CHI_PHÍ.
    Đảm bảo không bao giờ trả về DataFrame thiếu cột để tránh lỗi Dashboard.
    """
    # Danh sách cột bắt buộc phải có để Dashboard không bị crash
    required_columns = ['confirmed_dt', 'NĂM', 'THÁNG', 'CHI_PHÍ', 'branch', 'machine_display', 'id']
    
    try:
        # 1. Thực hiện truy vấn dữ liệu
        res = supabase.table("repair_cases").select("*").order("confirmed_date", desc=True).execute()
        
        # 2. Khởi tạo DataFrame (Gán ngay để tránh UnboundLocalError)
        df = pd.DataFrame(res.data)

        # 3. Kiểm tra nếu không có dữ liệu (Rỗng)
        if df.empty:
            return pd.DataFrame(columns=required_columns)

        # 4. TIỀN XỬ LÝ DỮ LIỆU
        # Chuyển đổi ngày tháng (errors='coerce' sẽ biến lỗi thành NaT)
        df['confirmed_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        
        # Xử lý trường hợp ngày xác nhận trống thì lấy ngày tạo (nếu có) hoặc bỏ qua
        if 'created_at' in df.columns:
            df['confirmed_dt'] = df['confirmed_dt'].fillna(pd.to_datetime(df['created_at'], errors='coerce'))
        
        # Loại bỏ các dòng không thể xác định ngày tháng để tránh lỗi khi trích xuất Năm/Tháng
        df = df.dropna(subset=['confirmed_dt'])

        if not df.empty:
            # Tạo cột NĂM và THÁNG (Ép kiểu int để dùng cho Selectbox)
            df['NĂM'] = df['confirmed_dt'].dt.year.astype(int)
            df['THÁNG'] = df['confirmed_dt'].dt.month.astype(int)
            
            # Xử lý CHI_PHÍ: Chuyển đổi về số, thay thế NaN bằng 0
            df['CHI_PHÍ'] = pd.to_numeric(df.get('compensation', 0), errors='coerce').fillna(0)
            
            # Đảm bảo có cột hiển thị máy
            if 'machine_display' not in df.columns:
                df['machine_display'] = df.get('machine_id', 'Unknown Device')
        else:
            # Trả về khung cột nếu sau khi lọc bị trống
            return pd.DataFrame(columns=required_columns)

        return df

    except Exception as e:
        # Log lỗi nhưng vẫn trả về DataFrame trống để giao diện không bị sập hoàn toàn
        st.error(f"⚠️ Lỗi hệ thống dữ liệu: {str(e)}")
        return pd.DataFrame(columns=required_columns)

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
