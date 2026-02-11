import pandas as pd
import streamlit as st
from core.database import supabase

# --- CẤU HÌNH HẰNG SỐ ---
STATUS_OPTIONS = [
    "1. Chờ nhận", 
    "2. Đã nhận kho tổng", 
    "3. Đang sửa nội bộ", 
    "4. Gửi nhà cung cấp", 
    "5. Đã sửa xong", 
    "6. Đã trả chi nhánh"
]

def get_repair_data():
    """
    Lấy dữ liệu từ bảng repair_cases, mapping với bảng machines để lấy machine_code 
    và tiền xử lý các cột thời gian, chi phí.
    """
    try:
        # 1. Lấy dữ liệu sửa chữa
        res_repair = supabase.table("repair_cases").select("*").order("created_at", desc=True).execute()
        df_repair = pd.DataFrame(res_repair.data)

        # 2. Lấy danh mục máy để mapping machine_code
        res_machines = supabase.table("machines").select("id, machine_code").execute()
        df_machines = pd.DataFrame(res_machines.data)

        if df_repair.empty:
            # Trả về khung DataFrame rỗng với đầy đủ các cột cần thiết để không lỗi Dashboard
            return pd.DataFrame(columns=[
                'machine_display', 'NĂM', 'THÁNG', 'CHI_PHÍ', 'branch', 
                'status', 'origin_branch', 'receiver_name', 'returner_name'
            ])

        # 3. MAPPING: Đổi UUID máy thành Machine Code dễ đọc
        df = df_repair.merge(
            df_machines, 
            left_on='machine_id', 
            right_on='id', 
            how='left', 
            suffixes=('', '_m')
        )

        # 4. TẠO CỘT HIỂN THỊ CHUẨN (Apple Style - Sạch sẽ)
        df['machine_display'] = df['machine_code'].fillna('N/A')

        # 5. XỬ LÝ THỜI GIAN & CHI PHÍ
        # Ưu tiên lấy ngày xác nhận, nếu không có lấy ngày tạo
        df['confirmed_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df['confirmed_dt'] = df['confirmed_dt'].fillna(pd.to_datetime(df['created_at'], errors='coerce'))
        
        # Loại bỏ các dòng không có ngày tháng hợp lệ để tránh lỗi trích xuất
        df = df.dropna(subset=['confirmed_dt'])

        # Trích xuất Năm/Tháng để lọc báo cáo
        df['NĂM'] = df['confirmed_dt'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_dt'].dt.month.astype(int)
        
        # Chuyển đổi chi phí bồi thường/sửa chữa về dạng số
        df['CHI_PHÍ'] = pd.to_numeric(df.get('compensation', 0), errors='coerce').fillna(0)

        return df
    except Exception as e:
        st.error(f"❌ Lỗi truy xuất dữ liệu: {e}")
        return pd.DataFrame()

def insert_new_repair(data_dict):
    """
    Thêm một ca sửa chữa mới vào hệ thống.
    """
    try:
        # Loại bỏ các trường kỹ thuật không thuộc Schema bảng
        keys_to_remove = ['created_by', 'machine_display']
        for key in keys_to_remove:
            if key in data_dict:
                data_dict.pop(key)
        
        # Gán trạng thái mặc định khi khởi tạo
        if 'status' not in data_dict:
            data_dict['status'] = "1. Chờ nhận"
            
        response = supabase.table("repair_cases").insert(data_dict).execute()
        
        # Xóa cache để các Tab khác cập nhật ngay lập tức
        st.cache_data.clear()
        return response
    except Exception as e:
        st.error(f"❌ Không thể lưu dữ liệu: {str(e)}")
        return None

def update_repair_tracking(case_id, new_status, staff_name, note=""):
    """
    Cập nhật trạng thái vận hành và đối soát nhân viên thực hiện (Receiver/Returner).
    """
    update_data = {
        "status": new_status,
        "note": note,
        "updated_at": "now()"
    }
    
    # --- LOGIC ĐỐI SOÁT NGHIỆP VỤ ---
    if "Đã nhận" in new_status:
        update_data["receiver_name"] = staff_name
        update_data["received_date"] = "now()"
        
    elif "Đã trả" in new_status:
        update_data["returner_name"] = staff_name
        update_data["returned_date"] = "now()"

    try:
        response = supabase.table("repair_cases").update(update_data).eq("id", case_id).execute()
        
        # Làm mới dữ liệu toàn cục
        st.cache_data.clear()
        return response
    except Exception as e:
        st.error(f"❌ Lỗi cập nhật đối soát: {str(e)}")
        return None
